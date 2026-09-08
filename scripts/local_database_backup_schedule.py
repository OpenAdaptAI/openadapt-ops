#!/usr/bin/env python3
"""Run one pinned local backup, or generate its private 04:00 launchd plist.

Setup requires matching production restore and off-device receipts. It never
loads launchd, installs a runner, pulls source code, or changes credentials.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib
import json
import os
import plistlib
import re
import stat
import subprocess
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "scripts/local_database_backup_schedule.py", "scripts/temporary_database_backup.py",
    "scripts/local_database_backup.py", "scripts/private_database_backup_release.py",
    "scripts/database_backup_contract.py",
)
CONFIG_KEYS = {"expected_backup_commit", "capture_config", "backup_root", "identity",
               "recipients", "postgres_bin", "internal_commit"}
PATH_KEYS = ("capture_config", "backup_root", "identity", "recipients", "postgres_bin")
SHA = re.compile(r"[0-9a-f]{40}")


class ScheduleError(ValueError):
    """The local schedule cannot prove its source or recovery prerequisites."""


def private_path(path: Path, *, directory: bool = False) -> None:
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise ScheduleError("the schedule requires private files owned by the current user")


def unique_fields(pairs: list) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ScheduleError("the schedule configuration contains duplicate fields")
        result[name] = value
    return result


def private_json(path: Path) -> dict:
    private_path(path)
    with path.open("rb") as stream:
        data = stream.read(64 * 1024 + 1)
    if len(data) > 64 * 1024:
        raise ScheduleError("the schedule configuration or receipt is unexpectedly large")
    value = json.loads(data, object_pairs_hook=unique_fields)
    if not isinstance(value, dict):
        raise ScheduleError("the schedule configuration or receipt is invalid")
    return value


def read_config(path: Path) -> dict:
    if not path.is_absolute():
        raise ScheduleError("the schedule configuration path must be absolute")
    value = private_json(path)
    if set(value) != CONFIG_KEYS:
        raise ScheduleError("the schedule configuration fields do not match the contract")
    for name in ("expected_backup_commit", "internal_commit"):
        if not isinstance(value[name], str) or SHA.fullmatch(value[name]) is None:
            raise ScheduleError("the schedule requires exact source commits")
    for name in PATH_KEYS:
        if not isinstance(value[name], str) or not Path(value[name]).is_absolute():
            raise ScheduleError("the schedule requires absolute local paths")
        value[name] = Path(value[name])
    private_path(value["backup_root"], directory=True)
    for name in ("capture_config", "identity"):
        private_path(value[name])
    if not value["recipients"].is_file() or not value["postgres_bin"].is_dir():
        raise ScheduleError("the local encryption or PostgreSQL tools are unavailable")
    return value


def git_read(arguments: list[str]) -> bytes:
    try:
        # A partial clone must not fetch missing code during a scheduled run.
        env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
        result = subprocess.run(["git", "-C", str(CODE_ROOT), *arguments], check=False,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, env=env)
    except (OSError, subprocess.TimeoutExpired):
        raise ScheduleError("the pinned source could not be verified") from None
    if result.returncode:
        raise ScheduleError("the pinned source could not be verified")
    return result.stdout


def verify_source(expected_commit: str) -> None:
    if not isinstance(expected_commit, str) or SHA.fullmatch(expected_commit) is None:
        raise ScheduleError("the schedule requires an exact source commit")
    if git_read(["rev-parse", "--verify", "HEAD"]).decode().strip() != expected_commit:
        raise ScheduleError("the checkout does not match the reviewed source commit")
    for name in SOURCE_FILES:
        path = CODE_ROOT / name
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ScheduleError("a pinned source file is not a regular file")
        expected = git_read(["show", f"{expected_commit}:{name}"])
        if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(expected).digest():
            raise ScheduleError("a source file differs from the reviewed commit")


def load_operations():
    """Import backup code only after the caller verifies its exact file bytes."""
    sys.path.insert(0, str(CODE_ROOT / "scripts"))
    capture = importlib.import_module("temporary_database_backup")
    transport = importlib.import_module("private_database_backup_release")
    for name in ("temporary_database_backup", "private_database_backup_release",
                 "local_database_backup", "database_backup_contract"):
        module = sys.modules.get(name)
        if module is not None and Path(module.__file__).resolve() != CODE_ROOT / "scripts" / f"{name}.py":
            raise ScheduleError("a backup dependency came from outside the reviewed checkout")
    return capture, transport


@contextlib.contextmanager
def run_lock(root: Path):
    path = root / ".database-backup-schedule.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise ScheduleError("the backup run lock is not a private owned file")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ScheduleError("a local database backup is already active") from None
        yield
    finally:
        os.close(descriptor)


def run_once(config_path: Path) -> dict:
    config = read_config(config_path)
    with run_lock(config["backup_root"]):
        verify_source(config["expected_backup_commit"])
        # Library diagnostics can contain connection details. launchd receives
        # only the wrapper's fixed success/failure message, never those details.
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            capture, transport = load_operations()
            archive = capture.capture(config["capture_config"], config["expected_backup_commit"],
                                      config["backup_root"], config["identity"], config["recipients"],
                                      config["postgres_bin"])
            if (not isinstance(archive, Path) or archive.parent.resolve() != config["backup_root"].resolve()
                    or archive.is_symlink()):
                raise ScheduleError("the capture returned an unexpected archive location")
            result = transport.publish(archive, config["internal_commit"])
        if not isinstance(result, dict) or result.get("off_device_verified") is not True:
            raise ScheduleError("the off-device backup did not verify")
        return result


def verify_recovery(archive: Path, config: dict, transport) -> None:
    if (not archive.is_absolute() or archive.parent.resolve() != config["backup_root"].resolve()
            or archive.is_symlink()):
        raise ScheduleError("the proven archive must belong to the configured backup root")
    manifest, expected = transport.verify_local(archive)
    restored = private_json(archive / "restore-receipt.json")
    if (restored.get("schema") != "openadapt.database-restore-evidence/v2"
            or restored.get("database_restored") is not True or restored.get("storage_restored") is not False
            or restored.get("artifact_sha256") != manifest["artifact_sha256"]
            or restored.get("backup_contract_sha256") != manifest["artifact"]["backup_contract_sha256"]):
        raise ScheduleError("the production database restore receipt does not match the archive")
    source = restored.get("source_project_ref_sha256")
    scratch = restored.get("scratch_project_ref_sha256")
    if (not isinstance(source, str) or not isinstance(scratch, str) or source == scratch
            or not re.fullmatch(r"[0-9a-f]{64}", source) or not re.fullmatch(r"[0-9a-f]{64}", scratch)):
        raise ScheduleError("the restore receipt does not bind an isolated target")
    copied = private_json(archive / transport.RECEIPT_NAME)
    if (copied.get("schema") != "openadapt.database-backup-github-release/v1"
            or copied.get("scope") != "production" or copied.get("repository") != transport.REPOSITORY
            or copied.get("repository_visibility_verified") != "private"
            or copied.get("off_device_verified") is not True or copied.get("download_readback_verified") is not True
            or copied.get("artifact_sha256") != manifest["artifact_sha256"]):
        raise ScheduleError("the private off-device receipt does not match the restored archive")
    assets = copied.get("assets")
    if not isinstance(assets, dict) or set(assets) != set(expected):
        raise ScheduleError("the off-device receipt asset inventory does not match")
    for name, entry in expected.items():
        asset = assets[name]
        if (not isinstance(asset, dict) or type(asset.get("id")) is not int or asset["id"] <= 0
                or asset.get("bytes") != entry["bytes"] or asset.get("sha256") != entry["sha256"]):
            raise ScheduleError("the off-device asset receipt does not match the local bytes")


def private_log(path: Path) -> None:
    if path.exists() or path.is_symlink():
        private_path(path)
    else:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)


def setup(config_path: Path, verified_archive: Path, output: Path) -> Path:
    config = read_config(config_path)
    verify_source(config["expected_backup_commit"])
    _, transport = load_operations()
    verify_recovery(verified_archive, config, transport)
    if not output.is_absolute() or {"LaunchAgents", "LaunchDaemons"}.intersection(output.resolve().parts):
        raise ScheduleError("setup writes a private review file, never a launchd installation path")
    private_path(output.parent, directory=True)
    stdout = config["backup_root"] / "schedule.stdout.log"
    stderr = config["backup_root"] / "schedule.stderr.log"
    private_log(stdout)
    private_log(stderr)
    value = {
        "Label": "ai.openadapt.database-backup",
        "ProgramArguments": [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()),
                             "run", "--config", str(config_path)],
        "WorkingDirectory": str(CODE_ROOT), "StartCalendarInterval": {"Hour": 4, "Minute": 0},
        "RunAtLoad": False, "KeepAlive": False, "ProcessType": "Background", "Umask": 0o077,
        "EnvironmentVariables": {"PATH": f"{config['postgres_bin']}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
        "StandardOutPath": str(stdout), "StandardErrorPath": str(stderr),
    }
    descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        plistlib.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("--config", type=Path, required=True)
    plan = commands.add_parser("setup")
    plan.add_argument("--config", type=Path, required=True)
    plan.add_argument("--verified-archive", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.command == "run":
            run_once(args.config)
        else:
            setup(args.config, args.verified_archive, args.output)
    except (Exception, KeyboardInterrupt):
        parser.exit(1, "The local database backup operation did not complete.\n")
    print("The local database backup completed." if args.command == "run" else "The private schedule plist is ready for review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
