#!/usr/bin/env python3
"""Capture with a task-owned, short-lived Supabase read-only login.

The existing role OID is an explicit private configuration input. This command
never adopts an unknown role, grants a privilege, or deletes a provider role.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import local_database_backup as backup
from database_backup_contract import ContractError

ROLE = "cli_login_supabase_read_only_user"
ROLE_QUERY = (
    "SELECT oid,rolname,rolsuper,rolcreaterole,rolcreatedb,rolcanlogin,rolvaliduntil "
    f"FROM pg_catalog.pg_roles WHERE rolname='{ROLE}'"
)


def config_file(path: Path) -> dict:
    backup.private_file(path)
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or set(value) != {
        "project_ref", "management_token", "owned_role_oid", "pooler_host"
    }:
        raise ContractError("the temporary capture configuration has unexpected fields")
    if (not isinstance(value["project_ref"], str)
            or not re.fullmatch(r"[a-z0-9]{20}", value["project_ref"])
            or not isinstance(value["management_token"], str)
            or not value["management_token"] or "\n" in value["management_token"]
            or type(value["owned_role_oid"]) is not int or value["owned_role_oid"] <= 0
            or not isinstance(value["pooler_host"], str)
            or not re.fullmatch(r"(?:[a-z0-9-]+\.){1,2}pooler\.supabase\.com", value["pooler_host"])):
        raise ContractError("the temporary capture configuration is invalid")
    return value


class Management:
    def __init__(self, config: dict):
        self.base = "https://api.supabase.com/v1/projects/" + config["project_ref"]
        self.token = config["management_token"]

    def request(self, suffix: str, payload: dict) -> object:
        try:
            response = requests.post(self.base + suffix, json=payload,
                                     headers={"Authorization": "Bearer " + self.token}, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            raise ContractError("the backup provider request failed") from None

    def query(self, sql: str, *, mutate: bool = False) -> list:
        result = self.request("/database/query" if mutate else "/database/query/read-only", {"query": sql})
        if not isinstance(result, list):
            raise ContractError("the backup provider returned invalid catalog metadata")
        return result


def owned_role(api: Management, oid: int, *, closed: bool = False) -> dict:
    rows = api.query(ROLE_QUERY)
    if (len(rows) != 1 or rows[0].get("oid") != oid or rows[0].get("rolname") != ROLE
            or any(rows[0].get(name) is not False for name in ("rolsuper", "rolcreaterole", "rolcreatedb"))):
        raise ContractError("the configured temporary role identity or privileges changed")
    if closed and rows[0].get("rolcanlogin") is not False:
        raise ContractError("the temporary role is already enabled; refusing to rotate another operation")
    return rows[0]


def mutate_owned(api: Management, oid: int, statement: str) -> None:
    # Check the OID and change the fixed role in the same SQL transaction.
    # Callers supply only the two fixed lifecycle statements below.
    if statement not in {f'ALTER ROLE "{ROLE}" LOGIN',
                         f'ALTER ROLE "{ROLE}" NOLOGIN VALID UNTIL \'1970-01-01 00:00:00+00\''}:
        raise ContractError("the temporary role mutation is not allowed")
    api.query("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='" + ROLE
              + "' AND oid=" + str(oid) + ") THEN RAISE EXCEPTION 'temporary role changed'; END IF; "
              + statement + "; END $$", mutate=True)


def revoke_login(api: Management, oid: int, started: datetime, application: str) -> dict:
    owned_role(api, oid)
    mutate_owned(api, oid, f'ALTER ROLE "{ROLE}" NOLOGIN VALID UNTIL \'1970-01-01 00:00:00+00\'')
    rows = api.query("SELECT pid,application_name,backend_start FROM pg_catalog.pg_stat_activity "
                     f"WHERE usename='{ROLE}'")
    for row in rows:
        backend_start = datetime.fromisoformat(row["backend_start"].replace(" ", "T"))
        if (type(row.get("pid")) is not int or row["pid"] <= 0 or backend_start < started
                or row.get("application_name") not in {application, "Supavisor"}):
            raise ContractError("an unexpected temporary-role session remains; no broad termination")
        api.query("SELECT pg_catalog.pg_terminate_backend(pid) FROM pg_catalog.pg_stat_activity WHERE pid="
                  + str(row["pid"]) + f" AND usename='{ROLE}' AND backend_start='"
                  + backend_start.isoformat() + "' AND (SELECT oid FROM pg_roles WHERE rolname='"
                  + ROLE + "')=" + str(oid), mutate=True)
    if api.query(f"SELECT pid FROM pg_stat_activity WHERE usename='{ROLE}'"):
        raise ContractError("temporary source sessions remain")
    role = owned_role(api, oid, closed=True)
    if datetime.fromisoformat(role["rolvaliduntil"].replace(" ", "T")) >= datetime.now(timezone.utc):
        raise ContractError("the temporary credential expiry did not verify")
    return {"login_disabled": True, "credential_expired": True, "owned_sessions_removed": True,
            "provider_role_metadata_retained": True}


def capture(config_path: Path, expected_backup_commit: str, backup_root: Path,
            identity: Path, recipients: Path, postgres_bin: Path) -> Path:
    """Return a verified archive only after this operation's login is revoked."""
    os.umask(0o077)
    config = config_file(Path(config_path))
    root = Path(backup_root)
    backup.private_root(root)
    backup.check_identity(Path(identity), Path(recipients))
    if backup.run(["supabase", "--version"]).decode().strip() != backup.CLI_VERSION:
        raise ContractError("the pinned Supabase CLI version is required")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_backup_commit):
        raise ContractError("the exact reviewed source commit is required")
    api = Management(config)
    oid = config["owned_role_oid"]
    owned_role(api, oid, closed=True)
    if api.query(f"SELECT pid FROM pg_stat_activity WHERE usename='{ROLE}'"):
        raise ContractError("an existing temporary-role session prevents capture")
    started = datetime.now(timezone.utc)
    application = "oa-backup-" + str(os.getpid()) + "-" + str(int(started.timestamp()))
    archive = root / started.strftime("%Y%m%dT%H%M%SZ")
    status = {"schema": "openadapt.temporary-backup-lifecycle/v1", "started_at": started.isoformat(),
              "production_backup": False, "login_disabled": False, "owned_sessions_removed": False}
    attempted = False
    try:
        # Even an uncertain API response enters cleanup; ownership was established
        # before this request and cleanup never targets any other role or OID.
        attempted = True
        login = api.request("/cli/login-role", {"read_only": True})
        if (not isinstance(login, dict) or login.get("role") != ROLE
                or type(login.get("ttl_seconds")) is not int or not 0 < login["ttl_seconds"] <= 600
                or not isinstance(login.get("password"), str) or not login["password"]):
            raise ContractError("the temporary login response exceeds the approved scope")
        owned_role(api, oid)
        mutate_owned(api, oid, f'ALTER ROLE "{ROLE}" LOGIN')
        with tempfile.TemporaryDirectory(prefix=".temporary-capture-", dir=root) as temporary:
            dumps = Path(temporary)
            source = {"project_ref": config["project_ref"], "db_url": "postgresql://" + ROLE + "."
                      + config["project_ref"] + ":" + quote(login["password"], safe="") + "@"
                      + config["pooler_host"] + ":5432/postgres?sslmode=require"}
            backup.source_config(source)
            _, env = backup.dump_connection(source, dumps / "source.pgpass")
            env["PGAPPNAME"] = application
            sql = ("SET ROLE supabase_read_only_user; BEGIN READ ONLY; SELECT current_user,session_user,"
                   "current_setting('transaction_read_only'),(SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user),"
                   "has_schema_privilege(current_user,'auth','USAGE'),has_schema_privilege(current_user,'storage','USAGE'),"
                   "has_table_privilege(current_user,'auth.users','SELECT'); ROLLBACK;")
            valid = False
            for attempt in range(5):
                try:
                    result = backup.run([str(Path(postgres_bin) / "psql"), "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-c", sql], env=env)
                    valid = result.decode().strip().split("|") == ["supabase_read_only_user", ROLE, "on", "t", "t", "t", "t"]
                    break
                except ContractError:
                    if attempt == 4:
                        raise
                    time.sleep(2)
            if not valid:
                raise ContractError("the effective read-only source role or managed-schema access did not verify")
            backup.capture_dumps(dumps, env, Path(postgres_bin))
            backup.pack(dumps, archive, project_ref=config["project_ref"], recipients=Path(recipients),
                        identity=Path(identity), source_commit=expected_backup_commit, scope="production",
                        created_at=started.isoformat().replace("+00:00", "Z"))
            status["production_backup"] = True
    finally:
        try:
            if attempted:
                status.update(revoke_login(api, oid, started, application))
        finally:
            status["completed_at"] = datetime.now(timezone.utc).isoformat()
            # No secret, connection string, role identifier, or provider body is
            # retained in this receipt. Preserve failures without overwriting.
            receipt = root / ("lifecycle-" + started.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
            with receipt.open("x") as stream:
                json.dump(status, stream, indent=2, sort_keys=True)
                stream.write("\n")
    return archive
