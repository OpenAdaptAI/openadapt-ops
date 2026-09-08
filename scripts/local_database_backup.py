#!/usr/bin/env python3
"""Create and verify a local encrypted recovery point without a CI runner.

The source password comes only from an explicitly supplied private config file.
This command does not install a scheduler, change a database, or upload data.
The existing S3 workflow does not count a local archive as an off-device backup.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import io
import json
import os
import re
import select
import shutil
import stat
import subprocess
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import database_backup_contract as contract

CLI_VERSION = "2.75.0"
RELEASE_ASSET_LIMIT = 2 * 1024**3


def quiet(function, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return function(argparse.Namespace(**kwargs))


def run(command, *, stdout=None, env=None, input=None):
    """Never put a subprocess command or its secret-bearing stderr in an error."""
    result = subprocess.run(
        command, stdout=stdout or subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, input=input, timeout=1800, check=False,
    )
    if result.returncode:
        raise contract.ContractError(
            f"{Path(command[0]).name} failed (exit {result.returncode}); no recovery point is claimed"
        )
    return result.stdout


def private_file(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise contract.ContractError("the credential or key must be a private regular file (0600)")
    if info.st_uid != os.getuid():
        raise contract.ContractError("the credential or key must belong to the current user")


def private_root(path: Path) -> None:
    if not path.is_absolute():
        raise contract.ContractError("the backup root must be an absolute path")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
        raise contract.ContractError("the backup root must be a private directory (0700)")
    if info.st_uid != os.getuid():
        raise contract.ContractError("the backup root must belong to the current user")
    if shutil.disk_usage(path).free < 1024**3:
        raise contract.ContractError("the backup device has less than 1 GiB free")


def check_identity(identity: Path, recipients: Path) -> None:
    private_file(identity)
    public = run(["age-keygen", "-y", str(identity)]).decode().strip()
    if public not in contract.recipients(recipients):
        raise contract.ContractError("the local decryption key does not match a backup recipient")


def source_config(config: dict) -> dict:
    if set(config) != {"project_ref", "db_url"}:
        raise contract.ContractError("the source config requires exactly project_ref and db_url")
    parsed = urlsplit(config["db_url"])
    identity_url = config["db_url"]
    if unquote(parsed.username or "") == "cli_login_supabase_read_only_user." + config["project_ref"]:
        # The provider's temporary role uses the same exact project suffix on
        # a session pooler. Validate its host/project with the canonical role.
        identity_url = parsed._replace(netloc="postgres." + config["project_ref"] + ":unused@" +
                                       parsed.netloc.rsplit("@", 1)[1]).geturl()
    contract.database_identity(identity_url, config["project_ref"], "production database")
    if not parsed.password:
        raise contract.ContractError("the source config has no database password")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) - {"sslmode"} or query.get("sslmode", ["require"]) not in (
        ["require"], ["verify-ca"], ["verify-full"]
    ):
        raise contract.ContractError("the source URL must use TLS and no additional connection options")
    return config


def dump_connection(config: dict, passfile: Path) -> tuple[str, dict]:
    """Use libpq's private password file, never a password in child argv."""
    parsed = urlsplit(config["db_url"])
    fields = (parsed.hostname, str(parsed.port or 5432), unquote(parsed.path.lstrip("/")),
              unquote(parsed.username), unquote(parsed.password))
    if any("\n" in value or "\r" in value for value in fields):
        raise contract.ContractError("the connection fields must not contain line breaks")
    line = ":".join(value.replace("\\", "\\\\").replace(":", "\\:") for value in fields)
    with passfile.open("x") as stream:
        stream.write(line + "\n")
    passfile.chmod(0o600)
    username = parsed.netloc.rsplit("@", 1)[0].split(":", 1)[0]
    address = parsed.netloc.rsplit("@", 1)[1]
    passwordless = parsed._replace(netloc=username + "@" + address).geturl()
    env = {name: value for name, value in os.environ.items()
           if not name.startswith("PG") and name != "SUPABASE_DB_PASSWORD"}
    assumed_role = "supabase_read_only_user" if unquote(parsed.username).split(".")[0] == "cli_login_supabase_read_only_user" else "postgres"
    env.update(PGPASSFILE=str(passfile), PGSSLMODE=parse_qs(parsed.query).get("sslmode", ["require"])[0],
               PGHOST=parsed.hostname, PGPORT=str(parsed.port or 5432), PGUSER=unquote(parsed.username),
               PGDATABASE=unquote(parsed.path.lstrip("/")), PGCONNECT_TIMEOUT="15",
               PGOPTIONS=f"-c role={assumed_role} -c default_transaction_read_only=on -c statement_timeout=1200000",
               OPENADAPT_DATABASE_ROLE=assumed_role)
    return passwordless, env


def native_dump_script(flags: list[str], *, snapshot: bool = False) -> bytes:
    """Use the pinned upstream SQL procedure, with our actual libpq boundary.

    The CLI's Docker path drops TLS parameters. Generate its script with a
    fixed synthetic connection, then remove exactly those five exports. Never
    expand a real password into shell text. pg_dump reads our private passfile.
    """
    expected = {
        'export PGHOST="127.0.0.1"', 'export PGPORT="55480"',
        'export PGUSER="postgres"', 'export PGPASSWORD="unused"',
        'export PGDATABASE="postgres"',
    }
    env = {name: value for name, value in os.environ.items()
           if not name.startswith("PG") and name != "SUPABASE_DB_PASSWORD"}
    script = run(["supabase", "db", "dump", "--db-url",
                  "postgresql://postgres:unused@127.0.0.1:55480/postgres", "--dry-run", *flags],
                 env=env).decode()
    lines = script.splitlines(keepends=True)
    exports = [line.strip() for line in lines if re.match(r"^export PG", line)]
    if len(exports) != 5 or set(exports) != expected:
        raise contract.ContractError("the pinned dump script has an unexpected connection boundary")
    script = "".join(line for line in lines if line.strip() not in expected)
    if script.count('--role "postgres"') != 1:
        raise contract.ContractError("the pinned dump script has an unexpected assumed role")
    script = script.replace('--role "postgres"', '--role "$OPENADAPT_DATABASE_ROLE"')
    if snapshot:
        if script.count("\npg_dump \\\n") != 1:
            raise contract.ContractError("the pinned script has an unexpected pg_dump command")
        script = script.replace("\npg_dump \\\n", '\npg_dump --snapshot "$OPENADAPT_BACKUP_SNAPSHOT" \\\n')
    return script.encode()


def native_dump(output: Path, flags: list[str], env: dict, postgres_bin: Path, *, snapshot: str | None = None) -> None:
    version = run([str(postgres_bin / "pg_dump"), "--version"]).decode()
    if not re.search(r"\(PostgreSQL\) 17\.", version):
        raise contract.ContractError("native PostgreSQL17 tools are required")
    actual = dict(env)
    actual.setdefault("OPENADAPT_DATABASE_ROLE", "postgres")
    if actual["OPENADAPT_DATABASE_ROLE"] not in {"postgres", "supabase_read_only_user"}:
        raise contract.ContractError("the dump role is not an approved source role")
    actual["PATH"] = str(postgres_bin) + os.pathsep + os.environ.get("PATH", "")
    if snapshot is not None:
        if not re.fullmatch(r"[0-9A-F]{8}-[0-9A-F]{8}-[0-9]+", snapshot):
            raise contract.ContractError("the exported snapshot identifier is invalid")
        actual["OPENADAPT_BACKUP_SNAPSHOT"] = snapshot
    with output.open("xb") as stream:
        run(["bash", "-s"], stdout=stream, env=actual, input=native_dump_script(flags, snapshot=snapshot is not None))


@contextlib.contextmanager
def source_snapshot(env: dict, postgres_bin: Path):
    """Hold one read-only MVCC snapshot for both native dumps."""
    with tempfile.TemporaryFile() as diagnostics:
        process = subprocess.Popen(
            [str(postgres_bin / "psql"), "-X", "-qAt", "-v", "ON_ERROR_STOP=1"],
            env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=diagnostics,
        )
        try:
            process.stdin.write(b"BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\nSELECT pg_catalog.pg_export_snapshot();\n")
            process.stdin.flush()
            if not select.select([process.stdout], [], [], 30)[0]:
                raise contract.ContractError("the source snapshot did not start within 30 seconds")
            value = process.stdout.readline().decode().strip()
            if not re.fullmatch(r"[0-9A-F]{8}-[0-9A-F]{8}-[0-9]+", value):
                raise contract.ContractError("the source did not return a valid exported snapshot")
            yield value
            if process.poll() is not None:
                raise contract.ContractError("the source snapshot ended before the backup completed")
            process.stdin.write(b"ROLLBACK;\n\\q\n")
            process.stdin.flush()
            process.wait(timeout=15)
            if process.returncode:
                raise contract.ContractError("the source snapshot did not close successfully")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            process.stdin.close()
            process.stdout.close()


def capture_dumps(dumps: Path, env: dict, postgres_bin: Path) -> None:
    native_dump(dumps / "roles.sql", ["--role-only"], env, postgres_bin)
    with source_snapshot(env, postgres_bin) as snapshot:
        native_dump(dumps / "schema.sql", [], env, postgres_bin, snapshot=snapshot)
        native_dump(dumps / "data.sql", ["--data-only", "--use-copy", "-x", "storage.buckets_vectors",
                    "-x", "storage.vector_indexes"], env, postgres_bin, snapshot=snapshot)
    # Roles are cluster metadata and pg_dumpall cannot import an MVCC snapshot.
    # Refuse concurrent role changes instead of publishing a mismatched set.
    native_dump(dumps / "roles-after.sql", ["--role-only"], env, postgres_bin)
    if contract.comparison_sha256(dumps / "roles.sql") != contract.comparison_sha256(dumps / "roles-after.sql"):
        raise contract.ContractError("database roles changed during the backup")


def configure(args) -> None:
    output = Path(args.output)
    private_root(output.parent)
    value = source_config({
        "project_ref": args.project_ref,
        "db_url": getpass.getpass("Supabase PostgreSQL URL (hidden): ").strip(),
    })
    with output.open("x") as stream:
        json.dump(value, stream)
        stream.write("\n")
    output.chmod(0o600)


def pack(dumps: Path, destination: Path, *, project_ref: str, recipients: Path,
         identity: Path, source_commit: str, scope: str, created_at: str) -> dict:
    """Publish a directory only after real age encryption/decryption and rehash."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise contract.ContractError("the source commit must be an exact Git SHA")
    if scope not in {"production", "synthetic"}:
        raise contract.ContractError("the archive scope must be production or synthetic")
    private_root(destination.parent)
    check_identity(identity, recipients)
    if destination.exists():
        raise contract.ContractError("the recovery point already exists; refusing to overwrite it")
    with tempfile.TemporaryDirectory(prefix=".backup-", dir=destination.parent) as temp:
        work = Path(temp)
        copied = work / "dump"
        copied.mkdir(mode=0o700)
        # Copy exact regular SQL components. Ignore unrelated files and reject
        # symlinks before reading a caller-supplied dump directory.
        for name in contract.REQUIRED_DUMPS:
            source = dumps / name
            if not stat.S_ISREG(source.lstat().st_mode):
                raise contract.ContractError("a dump component is not a regular file")
            shutil.copyfile(source, copied / name)
        backup_contract = copied / "backup-contract.json"
        quiet(contract.create_contract, project_ref=project_ref, recipients=str(recipients),
              dump_dir=str(copied), created_at=created_at, supabase_cli_version=CLI_VERSION,
              maximum_rpo_seconds=86400, retention_days=90, output=str(backup_contract))
        plain = work / "database.tar.gz"
        with tarfile.open(plain, "w:gz") as archive:
            for name in contract.ARCHIVE_MEMBERS:
                archive.add(copied / name, arcname=name, recursive=False)
        final = work / "complete"
        final.mkdir(mode=0o700)
        cipher = final / "database.tar.gz.age"
        run(["age", "-R", str(recipients), "-o", str(cipher), str(plain)])
        if cipher.stat().st_size >= RELEASE_ASSET_LIMIT:
            raise contract.ContractError("the ciphertext exceeds the private release asset limit")
        manifest_path = final / "artifact-manifest.json"
        quiet(contract.create_manifest, contract=str(backup_contract), plaintext_archive=str(plain),
              ciphertext_archive=str(cipher), repository_commit=source_commit,
              workflow_run_id=None, output=str(manifest_path))
        manifest = json.loads(manifest_path.read_text())
        # A local execution must never invent a GitHub Actions run ID.
        manifest["artifact"]["local_execution"] = {
            "id": str(uuid.uuid4()), "scope": scope, "created_at": created_at,
        }
        manifest["artifact_sha256"] = contract.sha256_text(contract.stable_json(manifest["artifact"]))
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        quiet(contract.verify_artifact, manifest=str(manifest_path), ciphertext_archive=str(cipher))
        recovered = work / "roundtrip.tar.gz"
        run(["age", "-d", "-i", str(identity), "-o", str(recovered), str(cipher)])
        quiet(contract.extract_artifact, plaintext_archive=str(recovered),
              manifest=str(manifest_path), output_dir=str(work / "roundtrip"))
        receipt = {
            "schema": "openadapt.local-database-backup/v1", "scope": scope,
            "created_at": created_at, "artifact_sha256": manifest["artifact_sha256"],
            "ciphertext_bytes": cipher.stat().st_size,
            "encryption_roundtrip_verified": True, "database_restored": False,
            "storage_restored": False, "off_device_verified": False,
        }
        (final / "local-verification.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        for path in final.iterdir():
            path.chmod(0o600)
        # Hard-link refusal gives no-replace semantics even if another local
        # invocation creates the target between the preflight and this point.
        destination.mkdir(mode=0o700)
        try:
            for name in ("database.tar.gz.age", "artifact-manifest.json", "local-verification.json"):
                path = final / name
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
                os.link(path, destination / path.name)
        except BaseException:
            shutil.rmtree(destination)
            raise
        return receipt


def unpack(archive: Path, identity: Path, output: Path) -> None:
    private_file(identity)
    if output.exists():
        raise contract.ContractError("the extraction target already exists")
    private_root(output.parent)
    manifest = archive / "artifact-manifest.json"
    cipher = archive / "database.tar.gz.age"
    quiet(contract.verify_artifact, manifest=str(manifest), ciphertext_archive=str(cipher))
    with tempfile.TemporaryDirectory(prefix=".restore-", dir=output.parent) as temp:
        plain = Path(temp) / "database.tar.gz"
        run(["age", "-d", "-i", str(identity), "-o", str(plain), str(cipher)])
        quiet(contract.extract_artifact, plaintext_archive=str(plain), manifest=str(manifest),
              output_dir=str(Path(temp) / "dump"))
        output.mkdir(mode=0o700)
        try:
            for source in (Path(temp) / "dump").iterdir():
                os.link(source, output / source.name)
        except BaseException:
            shutil.rmtree(output)
            raise


def capture(args) -> dict:
    config_path = Path(args.source_config)
    private_file(config_path)
    config = source_config(json.loads(config_path.read_text()))
    if run(["supabase", "--version"]).decode().strip() != CLI_VERSION:
        raise contract.ContractError(f"Supabase CLI {CLI_VERSION} is required")
    root = Path(args.backup_root)
    private_root(root)
    identity, recipients = Path(args.identity), Path(args.recipients)
    check_identity(identity, recipients)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(prefix=".capture-", dir=root) as temp:
        dumps = Path(temp)
        _, env = dump_connection(config, dumps / "source.pgpass")
        # Execute the maintained pg_dump/pg_dumpall procedure with explicit
        # native TLS/passfile settings. Keep client diagnostics private.
        capture_dumps(dumps, env, Path(args.postgres_bin))
        return pack(dumps, root / stamp, project_ref=config["project_ref"], recipients=recipients,
                    identity=identity, source_commit=args.source_commit, scope="production",
                    created_at=now.isoformat().replace("+00:00", "Z"))


def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    configure_parser = commands.add_parser("configure")
    configure_parser.add_argument("--project-ref", required=True)
    configure_parser.add_argument("--output", required=True)
    capture_parser = commands.add_parser("capture")
    capture_parser.add_argument("--source-config", required=True)
    capture_parser.add_argument("--backup-root", required=True)
    capture_parser.add_argument("--identity", required=True)
    capture_parser.add_argument("--recipients", required=True)
    capture_parser.add_argument("--source-commit", required=True)
    capture_parser.add_argument("--postgres-bin", required=True)
    unpack_parser = commands.add_parser("unpack")
    unpack_parser.add_argument("--archive", required=True)
    unpack_parser.add_argument("--identity", required=True)
    unpack_parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "capture":
            print(json.dumps(capture(args), sort_keys=True))
        elif args.command == "configure":
            configure(args)
            print(json.dumps({"configured": True, "database_accessed": False}))
        else:
            unpack(Path(args.archive), Path(args.identity), Path(args.output))
            print(json.dumps({"extracted": True, "database_restored": False}))
    except (contract.ContractError, OSError, ValueError, subprocess.TimeoutExpired):
        # Config/URL/parser failures can embed credentials. Keep this entry
        # point silent about arbitrary exception text, including subprocess args.
        print("error: local backup operation failed; no new recovery claim", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
