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
import shutil
import stat
import subprocess
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import database_backup_contract as contract

CLI_VERSION = "2.75.0"
RELEASE_ASSET_LIMIT = 2 * 1024**3


def quiet(function, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return function(argparse.Namespace(**kwargs))


def run(command, *, stdout=None, env=None):
    """Never put a subprocess command or its secret-bearing stderr in an error."""
    result = subprocess.run(
        command, stdout=stdout or subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, timeout=1800, check=False,
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
    contract.database_identity(config["db_url"], config["project_ref"], "production database")
    parsed = urlsplit(config["db_url"])
    if not parsed.password:
        raise contract.ContractError("the source config has no database password")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) - {"sslmode"} or query.get("sslmode", ["require"]) not in (
        ["require"], ["verify-ca"], ["verify-full"]
    ):
        raise contract.ContractError("the source URL must use TLS and no additional connection options")
    return config


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
        env = os.environ.copy()
        env["PGSSLMODE"] = "require"
        # Supabase db dump runs only pg_dump/pg_dumpall, which read the source.
        # Keep all stdout/stderr private: errors can contain connection details.
        commands = [
            ("roles.sql", ["--role-only"]), ("schema.sql", []),
            ("data.sql", ["--data-only", "--use-copy", "-x", "storage.buckets_vectors",
                          "-x", "storage.vector_indexes"]),
        ]
        for name, flags in commands:
            run(["supabase", "db", "dump", "--db-url", config["db_url"],
                 "--file", str(dumps / name), *flags], env=env)
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
