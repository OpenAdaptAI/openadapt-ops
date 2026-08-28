from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_database_backup_freshness import (
    FreshnessError,
    select_latest,
    select_latest_restore,
    stable_json,
    verify_latest,
    verify_restore,
)

NOW = datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc)
STAMP = "20260818T150000Z"
PREFIX = f"daily/{STAMP}"
RESTORE_KEY = (
    f"drills/database-only/{STAMP}/restore-evidence-{STAMP}.json"
)


def manifest() -> dict[str, object]:
    artifact = {
        "backup_contract_sha256": "c" * 64,
        "plaintext_archive": {"bytes": 200, "sha256": "d" * 64},
        "ciphertext_archive": {"bytes": 100, "sha256": "a" * 64},
        "repository_commit": "b" * 40,
        "workflow_run_id": "32113840939",
    }
    return {
        "schema": "openadapt.database-backup-artifact/v2",
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(stable_json(artifact).encode()).hexdigest(),
    }


def inventory(value: dict[str, object] | None = None) -> dict[str, object]:
    value = value or manifest()
    manifest_bytes = len((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
    return {
        "IsTruncated": False,
        "Contents": [
            {
                "Key": f"{PREFIX}/artifact-manifest.json",
                "LastModified": "2026-08-18T15:01:00Z",
                "Size": manifest_bytes,
            },
            {
                "Key": f"{PREFIX}/db-backup-{STAMP}.tar.gz.age",
                "LastModified": "2026-08-18T15:01:00Z",
                "Size": 100,
            },
        ],
    }


def attributes() -> dict[str, object]:
    return {
        "ObjectSize": 100,
        "Checksum": {
            "ChecksumSHA256": base64.b64encode(bytes.fromhex("a" * 64)).decode(),
        },
        "StorageClass": "STANDARD",
    }


def selection() -> dict[str, object]:
    return select_latest(inventory(), now=NOW, maximum_age_seconds=86400)


def restore_receipt() -> dict[str, object]:
    return {
        "schema": "openadapt.database-restore-evidence/v2",
        "backup_contract_sha256": "1" * 64,
        "artifact_sha256": "2" * 64,
        "source_project_ref_sha256": "3" * 64,
        "scratch_project_ref_sha256": "4" * 64,
        "recovery_point_at": "2026-08-18T15:00:00Z",
        "started_at": "2026-08-18T15:30:00Z",
        "completed_at": "2026-08-18T15:35:00Z",
        "rpo_seconds_at_start": 1800,
        "rto_seconds": 300,
        "schema_sha256": "5" * 64,
        "data_sha256": "6" * 64,
        "schema_comparison_sha256": "7" * 64,
        "data_comparison_sha256": "8" * 64,
        "database_restored": True,
        "storage_restored": False,
    }


def restore_inventory(value: dict[str, object] | None = None) -> dict[str, object]:
    value = value or restore_receipt()
    receipt_bytes = len((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
    return {
        "IsTruncated": False,
        "Contents": [
            {
                "Key": RESTORE_KEY,
                "LastModified": "2026-08-18T15:36:00Z",
                "Size": receipt_bytes,
            }
        ],
    }


def restore_selection(
    value: dict[str, object] | None = None,
) -> dict[str, object]:
    return select_latest_restore(
        restore_inventory(value), now=NOW, maximum_age_seconds=2592000
    )


def test_complete_fresh_pair_passes() -> None:
    result = verify_latest(selection(), manifest(), attributes())
    assert result["fresh"] is True
    assert result["age_seconds"] == 3600


def test_missing_newest_ciphertext_does_not_fall_back_to_an_old_pair() -> None:
    value = inventory()
    value["Contents"].append(
        {
            "Key": "daily/20260818T155500Z/artifact-manifest.json",
            "LastModified": "2026-08-18T15:55:10Z",
            "Size": 10,
        }
    )
    with pytest.raises(FreshnessError, match="complete object pair"):
        select_latest(value, now=NOW, maximum_age_seconds=86400)


def test_stale_recovery_point_is_rejected() -> None:
    with pytest.raises(FreshnessError, match="stale"):
        select_latest(inventory(), now=NOW, maximum_age_seconds=1800)


def test_truncated_inventory_is_rejected() -> None:
    value = inventory()
    value["IsTruncated"] = True
    with pytest.raises(FreshnessError, match="incomplete"):
        select_latest(value, now=NOW, maximum_age_seconds=86400)


def test_invalid_calendar_stamp_is_rejected_cleanly() -> None:
    value = inventory()
    value["Contents"][0]["Key"] = "daily/20261318T150000Z/artifact-manifest.json"
    value["Contents"][1]["Key"] = (
        "daily/20261318T150000Z/db-backup-20261318T150000Z.tar.gz.age"
    )
    with pytest.raises(FreshnessError, match="backup stamp"):
        select_latest(value, now=NOW, maximum_age_seconds=86400)


def test_unexpected_object_in_daily_prefix_is_rejected() -> None:
    value = inventory()
    value["Contents"].append(
        {
            "Key": f"{PREFIX}/plaintext.sql",
            "LastModified": "2026-08-18T15:01:00Z",
            "Size": 1,
        }
    )
    with pytest.raises(FreshnessError, match="unexpected object"):
        select_latest(value, now=NOW, maximum_age_seconds=86400)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: value["Checksum"].update(ChecksumSHA256="wrong"), "checksum"),
        (
            lambda value: value["Checksum"].update(
                ChecksumSHA256=f'{value["Checksum"]["ChecksumSHA256"]}-2'
            ),
            "checksum",
        ),
        (lambda value: value.update(ObjectSize=99), "size"),
    ],
)
def test_remote_ciphertext_mismatch_is_rejected(change, message: str) -> None:
    value = attributes()
    change(value)
    with pytest.raises(FreshnessError, match=message):
        verify_latest(selection(), manifest(), value)


def test_manifest_digest_mismatch_is_rejected() -> None:
    value = manifest()
    value["artifact"]["repository_commit"] = "e" * 40
    with pytest.raises(FreshnessError, match="manifest digest"):
        verify_latest(selection(), value, attributes())


def test_current_database_only_restore_drill_passes() -> None:
    result = verify_restore(
        restore_selection(),
        restore_receipt(),
        now=NOW,
        maximum_age_seconds=2592000,
    )
    assert result == {
        "restore_current": True,
        "recovery_point_at": "2026-08-18T15:00:00Z",
        "completed_at": "2026-08-18T15:35:00Z",
        "age_seconds": 1500,
        "rpo_seconds_at_start": 1800,
        "rto_seconds": 300,
    }


def test_restore_drill_inventory_fails_closed() -> None:
    with pytest.raises(FreshnessError, match="no database-only restore drill"):
        select_latest_restore(
            {"IsTruncated": False, "Contents": []},
            now=NOW,
            maximum_age_seconds=2592000,
        )

    value = restore_inventory()
    value["Contents"][0]["Key"] = f"drills/database-only/{STAMP}/notes.txt"
    with pytest.raises(FreshnessError, match="unexpected object"):
        select_latest_restore(value, now=NOW, maximum_age_seconds=2592000)


def test_stale_restore_drill_is_rejected_by_upload_and_receipt_time() -> None:
    value = restore_inventory()
    value["Contents"][0]["LastModified"] = "2026-07-01T15:36:00Z"
    with pytest.raises(FreshnessError, match="restore drill is stale"):
        select_latest_restore(value, now=NOW, maximum_age_seconds=2592000)

    receipt = restore_receipt()
    receipt["completed_at"] = "2026-07-01T15:35:00Z"
    receipt["started_at"] = "2026-07-01T15:30:00Z"
    receipt["recovery_point_at"] = "2026-07-01T15:00:00Z"
    old_key = "drills/database-only/20260701T150000Z/restore-evidence-20260701T150000Z.json"
    old_selection = restore_selection()
    old_selection["receipt_key"] = old_key
    old_selection["receipt_bytes"] = len(
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    )
    with pytest.raises(FreshnessError, match="restore drill is stale"):
        verify_restore(
            old_selection, receipt, now=NOW, maximum_age_seconds=2592000
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: value.update(database_restored=False), "database restore"),
        (lambda value: value.update(storage_restored=True), "Storage result"),
        (lambda value: value.update(artifact_sha256="wrong"), "artifact_sha256"),
        (
            lambda value: value.update(
                scratch_project_ref_sha256=value["source_project_ref_sha256"]
            ),
            "production database",
        ),
        (lambda value: value.update(rpo_seconds_at_start=1799), "RPO"),
        (lambda value: value.update(rto_seconds=299), "RTO"),
    ],
)
def test_invalid_restore_receipt_is_rejected(change, message: str) -> None:
    receipt = restore_receipt()
    change(receipt)
    with pytest.raises(FreshnessError, match=message):
        verify_restore(
            restore_selection(receipt),
            receipt,
            now=NOW,
            maximum_age_seconds=2592000,
        )
