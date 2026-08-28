#!/usr/bin/env python3
"""Prove that the newest private database backup is complete and fresh."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ARTIFACT_SCHEMA = "openadapt.database-backup-artifact/v2"
RESTORE_EVIDENCE_SCHEMA = "openadapt.database-restore-evidence/v2"
STAMP = re.compile(r"^(\d{8}T\d{6}Z)$")
MANIFEST_KEY = re.compile(r"^daily/(\d{8}T\d{6}Z)/artifact-manifest\.json$")
CIPHERTEXT_KEY = re.compile(
    r"^daily/(\d{8}T\d{6}Z)/db-backup-(\d{8}T\d{6}Z)\.tar\.gz\.age$"
)
RESTORE_KEY = re.compile(
    r"^drills/database-only/(\d{8}T\d{6}Z)/"
    r"restore-evidence-(\d{8}T\d{6}Z)\.json$"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


class FreshnessError(ValueError):
    """The S3 inventory does not prove a current recovery point."""


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise FreshnessError(f"{name} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise FreshnessError(f"{name} is not an ISO-8601 time") from error
    if parsed.tzinfo is None:
        raise FreshnessError(f"{name} has no timezone")
    return parsed.astimezone(timezone.utc)


def recovery_time(stamp: str) -> datetime:
    if STAMP.fullmatch(stamp) is None:
        raise FreshnessError("the backup stamp is invalid")
    try:
        return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise FreshnessError("the backup stamp is invalid") from error


def select_latest(
    inventory: dict[str, object], *, now: datetime, maximum_age_seconds: int
) -> dict[str, object]:
    if not isinstance(inventory, dict):
        raise FreshnessError("the S3 inventory is not an object")
    if maximum_age_seconds <= 0:
        raise FreshnessError("the maximum backup age must be positive")
    if inventory.get("IsTruncated") is not False:
        raise FreshnessError("the S3 inventory is incomplete")
    contents = inventory.get("Contents")
    if not isinstance(contents, list) or not contents:
        raise FreshnessError("the backup bucket has no daily recovery point")

    objects: dict[str, dict[str, object]] = {}
    stamps: set[str] = set()
    for item in contents:
        if not isinstance(item, dict) or not isinstance(item.get("Key"), str):
            raise FreshnessError("the S3 inventory contains an invalid object")
        key = item["Key"]
        manifest_match = MANIFEST_KEY.fullmatch(key)
        ciphertext_match = CIPHERTEXT_KEY.fullmatch(key)
        if manifest_match:
            stamp = manifest_match.group(1)
        elif ciphertext_match and ciphertext_match.group(1) == ciphertext_match.group(
            2
        ):
            stamp = ciphertext_match.group(1)
        else:
            raise FreshnessError(
                f"the daily prefix contains an unexpected object: {key}"
            )
        if key in objects:
            raise FreshnessError(f"the S3 inventory contains a duplicate object: {key}")
        if not isinstance(item.get("Size"), int) or item["Size"] <= 0:
            raise FreshnessError(f"the S3 object is empty: {key}")
        parse_time(item.get("LastModified"), f"LastModified for {key}")
        objects[key] = item
        stamps.add(stamp)

    latest_stamp = max(stamps)
    recovery_point = recovery_time(latest_stamp)
    age = (now.astimezone(timezone.utc) - recovery_point).total_seconds()
    if age < -300:
        raise FreshnessError("the newest backup recovery point is in the future")
    if age > maximum_age_seconds:
        raise FreshnessError(
            f"the newest backup recovery point is stale by {int(age - maximum_age_seconds)} seconds"
        )

    manifest_key = f"daily/{latest_stamp}/artifact-manifest.json"
    ciphertext_key = f"daily/{latest_stamp}/db-backup-{latest_stamp}.tar.gz.age"
    if manifest_key not in objects or ciphertext_key not in objects:
        raise FreshnessError(
            "the newest backup prefix does not contain one complete object pair"
        )
    if sum(key.startswith(f"daily/{latest_stamp}/") for key in objects) != 2:
        raise FreshnessError(
            "the newest backup prefix does not contain exactly two objects"
        )

    for key in (manifest_key, ciphertext_key):
        last_modified = parse_time(
            objects[key]["LastModified"], f"LastModified for {key}"
        )
        if last_modified < recovery_point - timedelta(seconds=30):
            raise FreshnessError(f"the S3 object predates its recovery point: {key}")
        if last_modified > recovery_point + timedelta(hours=2):
            raise FreshnessError(
                f"the S3 object arrived too late for its recovery point: {key}"
            )

    return {
        "schema": "openadapt.database-backup-selection/v1",
        "recovery_point_at": recovery_point.isoformat().replace("+00:00", "Z"),
        "age_seconds": max(0, int(age)),
        "manifest_key": manifest_key,
        "manifest_bytes": objects[manifest_key]["Size"],
        "ciphertext_key": ciphertext_key,
        "ciphertext_bytes": objects[ciphertext_key]["Size"],
    }


def verify_latest(
    selection: dict[str, object],
    manifest: dict[str, object],
    attributes: dict[str, object],
) -> dict[str, object]:
    if not all(isinstance(value, dict) for value in (selection, manifest, attributes)):
        raise FreshnessError("the backup verification input is not an object")
    if selection.get("schema") != "openadapt.database-backup-selection/v1":
        raise FreshnessError("the backup selection schema is invalid")
    manifest_key = selection.get("manifest_key")
    ciphertext_key = selection.get("ciphertext_key")
    if (
        not isinstance(manifest_key, str)
        or MANIFEST_KEY.fullmatch(manifest_key) is None
    ):
        raise FreshnessError("the selected manifest key is invalid")
    ciphertext_match = (
        CIPHERTEXT_KEY.fullmatch(ciphertext_key)
        if isinstance(ciphertext_key, str)
        else None
    )
    if ciphertext_match is None or ciphertext_match.group(1) != ciphertext_match.group(
        2
    ):
        raise FreshnessError("the selected ciphertext key is invalid")
    if manifest_key.split("/")[1] != ciphertext_match.group(1):
        raise FreshnessError(
            "the selected backup objects use different recovery points"
        )

    if manifest.get("schema") != ARTIFACT_SCHEMA:
        raise FreshnessError("the artifact manifest schema is invalid")
    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        raise FreshnessError("the artifact manifest is incomplete")
    if manifest.get("artifact_sha256") != sha256_text(stable_json(artifact)):
        raise FreshnessError("the artifact manifest digest is invalid")
    ciphertext = artifact.get("ciphertext_archive")
    if not isinstance(ciphertext, dict):
        raise FreshnessError("the ciphertext contract is missing")
    ciphertext_bytes = ciphertext.get("bytes")
    ciphertext_sha = ciphertext.get("sha256")
    if not isinstance(ciphertext_bytes, int) or ciphertext_bytes <= 0:
        raise FreshnessError("the ciphertext size is invalid")
    if not isinstance(ciphertext_sha, str) or SHA256.fullmatch(ciphertext_sha) is None:
        raise FreshnessError("the ciphertext digest is invalid")
    if selection.get("ciphertext_bytes") != ciphertext_bytes:
        raise FreshnessError("the S3 inventory size does not match the manifest")
    if selection.get("manifest_bytes") != len(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    ):
        raise FreshnessError(
            "the S3 manifest size does not match the downloaded manifest"
        )
    if (
        not isinstance(artifact.get("repository_commit"), str)
        or COMMIT.fullmatch(artifact["repository_commit"]) is None
    ):
        raise FreshnessError("the artifact repository commit is invalid")
    run_id = artifact.get("workflow_run_id")
    if not isinstance(run_id, str) or not run_id.isdigit():
        raise FreshnessError("the artifact workflow run ID is invalid")

    if attributes.get("ObjectSize") != ciphertext_bytes:
        raise FreshnessError("the remote ciphertext size does not match the manifest")
    expected_checksum = base64.b64encode(bytes.fromhex(ciphertext_sha)).decode()
    checksum = attributes.get("Checksum")
    if (
        not isinstance(checksum, dict)
        or checksum.get("ChecksumSHA256") != expected_checksum
    ):
        raise FreshnessError(
            "the remote ciphertext full-object checksum does not match"
        )

    return {
        "fresh": True,
        "recovery_point_at": selection["recovery_point_at"],
        "age_seconds": selection["age_seconds"],
        "artifact_sha256": manifest["artifact_sha256"],
        "repository_commit": artifact["repository_commit"],
        "workflow_run_id": run_id,
    }


def select_latest_restore(
    inventory: dict[str, object], *, now: datetime, maximum_age_seconds: int
) -> dict[str, object]:
    """Select the newest uploaded database-only restore receipt."""
    if not isinstance(inventory, dict):
        raise FreshnessError("the restore-drill inventory is not an object")
    if maximum_age_seconds <= 0:
        raise FreshnessError("the maximum restore-drill age must be positive")
    if inventory.get("IsTruncated") is not False:
        raise FreshnessError("the restore-drill inventory is incomplete")
    contents = inventory.get("Contents")
    if not isinstance(contents, list) or not contents:
        raise FreshnessError("the backup bucket has no database-only restore drill")

    receipts: list[tuple[datetime, str, int]] = []
    keys: set[str] = set()
    for item in contents:
        if not isinstance(item, dict) or not isinstance(item.get("Key"), str):
            raise FreshnessError("the restore-drill inventory contains an invalid object")
        key = item["Key"]
        match = RESTORE_KEY.fullmatch(key)
        if match is None or match.group(1) != match.group(2):
            raise FreshnessError(
                f"the database-only drill prefix contains an unexpected object: {key}"
            )
        if key in keys:
            raise FreshnessError(
                f"the restore-drill inventory contains a duplicate object: {key}"
            )
        size = item.get("Size")
        if not isinstance(size, int) or size <= 0:
            raise FreshnessError(f"the restore-drill receipt is empty: {key}")
        uploaded_at = parse_time(item.get("LastModified"), f"LastModified for {key}")
        receipts.append((uploaded_at, key, size))
        keys.add(key)

    uploaded_at, key, size = max(receipts, key=lambda item: (item[0], item[1]))
    age = (now.astimezone(timezone.utc) - uploaded_at).total_seconds()
    if age < -300:
        raise FreshnessError("the newest restore-drill receipt is in the future")
    if age > maximum_age_seconds:
        raise FreshnessError("the newest database-only restore drill is stale")
    return {
        "schema": "openadapt.database-restore-selection/v1",
        "receipt_key": key,
        "receipt_bytes": size,
        "uploaded_at": uploaded_at.isoformat().replace("+00:00", "Z"),
    }


def verify_restore(
    selection: dict[str, object],
    receipt: dict[str, object],
    *,
    now: datetime,
    maximum_age_seconds: int,
) -> dict[str, object]:
    """Verify that a recent receipt proves an isolated database restore."""
    if not isinstance(selection, dict) or not isinstance(receipt, dict):
        raise FreshnessError("the restore-drill verification input is not an object")
    if maximum_age_seconds <= 0:
        raise FreshnessError("the maximum restore-drill age must be positive")
    if selection.get("schema") != "openadapt.database-restore-selection/v1":
        raise FreshnessError("the restore-drill selection schema is invalid")
    key = selection.get("receipt_key")
    match = RESTORE_KEY.fullmatch(key) if isinstance(key, str) else None
    if match is None or match.group(1) != match.group(2):
        raise FreshnessError("the selected restore-drill key is invalid")
    if selection.get("receipt_bytes") != len(
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    ):
        raise FreshnessError("the restore-drill receipt size does not match S3")
    if receipt.get("schema") != RESTORE_EVIDENCE_SCHEMA:
        raise FreshnessError("the restore-drill receipt schema is invalid")
    if receipt.get("database_restored") is not True:
        raise FreshnessError("the receipt does not prove a database restore")
    if receipt.get("storage_restored") is not False:
        raise FreshnessError("the database-only receipt has an invalid Storage result")

    digest_fields = (
        "backup_contract_sha256",
        "artifact_sha256",
        "source_project_ref_sha256",
        "scratch_project_ref_sha256",
        "schema_sha256",
        "data_sha256",
        "schema_comparison_sha256",
        "data_comparison_sha256",
    )
    for name in digest_fields:
        value = receipt.get(name)
        if not isinstance(value, str) or SHA256.fullmatch(value) is None:
            raise FreshnessError(f"the restore-drill {name} is invalid")
    if receipt["source_project_ref_sha256"] == receipt["scratch_project_ref_sha256"]:
        raise FreshnessError("the restore drill used the production database as its target")

    recovery_point = parse_time(receipt.get("recovery_point_at"), "recovery_point_at")
    started_at = parse_time(receipt.get("started_at"), "started_at")
    completed_at = parse_time(receipt.get("completed_at"), "completed_at")
    if completed_at < started_at:
        raise FreshnessError("the restore drill completed before it started")
    if started_at < recovery_point:
        raise FreshnessError("the restore drill started before its recovery point")
    if recovery_point.strftime("%Y%m%dT%H%M%SZ") != match.group(1):
        raise FreshnessError("the restore-drill key does not match its recovery point")

    rpo_seconds = int((started_at - recovery_point).total_seconds())
    rto_seconds = int((completed_at - started_at).total_seconds())
    if receipt.get("rpo_seconds_at_start") != rpo_seconds:
        raise FreshnessError("the restore-drill RPO is invalid")
    if receipt.get("rto_seconds") != rto_seconds:
        raise FreshnessError("the restore-drill RTO is invalid")

    age = (now.astimezone(timezone.utc) - completed_at).total_seconds()
    if age < -300:
        raise FreshnessError("the restore-drill completion time is in the future")
    if age > maximum_age_seconds:
        raise FreshnessError("the newest database-only restore drill is stale")
    uploaded_at = parse_time(selection.get("uploaded_at"), "uploaded_at")
    if uploaded_at < completed_at:
        raise FreshnessError("the restore-drill receipt predates its completion")

    return {
        "restore_current": True,
        "recovery_point_at": receipt["recovery_point_at"],
        "completed_at": receipt["completed_at"],
        "age_seconds": max(0, int(age)),
        "rpo_seconds_at_start": rpo_seconds,
        "rto_seconds": rto_seconds,
    }


def write_json(path: str, value: object) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    select = commands.add_parser("select")
    select.add_argument("--inventory", required=True)
    select.add_argument("--output", required=True)
    select.add_argument("--github-output")
    select.add_argument("--now")
    select.add_argument("--maximum-age-seconds", type=int, default=86400)

    verify = commands.add_parser("verify")
    verify.add_argument("--selection", required=True)
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--attributes", required=True)

    restore_select = commands.add_parser("select-restore")
    restore_select.add_argument("--inventory", required=True)
    restore_select.add_argument("--output", required=True)
    restore_select.add_argument("--github-output")
    restore_select.add_argument("--now")
    restore_select.add_argument("--maximum-age-seconds", type=int, default=2592000)

    restore_verify = commands.add_parser("verify-restore")
    restore_verify.add_argument("--selection", required=True)
    restore_verify.add_argument("--receipt", required=True)
    restore_verify.add_argument("--now")
    restore_verify.add_argument("--maximum-age-seconds", type=int, default=2592000)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "select":
            now = (
                parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
            )
            result = select_latest(
                json.loads(Path(args.inventory).read_text(encoding="utf-8")),
                now=now,
                maximum_age_seconds=args.maximum_age_seconds,
            )
            write_json(args.output, result)
            if args.github_output:
                with Path(args.github_output).open("a", encoding="utf-8") as stream:
                    stream.write(f"manifest_key={result['manifest_key']}\n")
                    stream.write(f"ciphertext_key={result['ciphertext_key']}\n")
        elif args.command == "verify":
            result = verify_latest(
                json.loads(Path(args.selection).read_text(encoding="utf-8")),
                json.loads(Path(args.manifest).read_text(encoding="utf-8")),
                json.loads(Path(args.attributes).read_text(encoding="utf-8")),
            )
        elif args.command == "select-restore":
            now = (
                parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
            )
            result = select_latest_restore(
                json.loads(Path(args.inventory).read_text(encoding="utf-8")),
                now=now,
                maximum_age_seconds=args.maximum_age_seconds,
            )
            write_json(args.output, result)
            if args.github_output:
                with Path(args.github_output).open("a", encoding="utf-8") as stream:
                    stream.write(f"receipt_key={result['receipt_key']}\n")
        else:
            now = (
                parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
            )
            result = verify_restore(
                json.loads(Path(args.selection).read_text(encoding="utf-8")),
                json.loads(Path(args.receipt).read_text(encoding="utf-8")),
                now=now,
                maximum_age_seconds=args.maximum_age_seconds,
            )
    except (FreshnessError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
