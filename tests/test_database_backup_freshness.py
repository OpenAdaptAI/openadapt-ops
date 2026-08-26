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
    stable_json,
    verify_latest,
)

NOW = datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc)
STAMP = "20260818T150000Z"
PREFIX = f"daily/{STAMP}"


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
                "StorageClass": "STANDARD",
            },
            {
                "Key": f"{PREFIX}/db-backup-{STAMP}.tar.gz.age",
                "LastModified": "2026-08-18T15:01:00Z",
                "Size": 100,
                "StorageClass": "GLACIER_IR",
            },
        ],
    }


def attributes() -> dict[str, object]:
    return {
        "ObjectSize": 100,
        "Checksum": {
            "ChecksumSHA256": base64.b64encode(bytes.fromhex("a" * 64)).decode(),
        },
        "StorageClass": "GLACIER_IR",
    }


def selection() -> dict[str, object]:
    return select_latest(inventory(), now=NOW, maximum_age_seconds=86400)


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
            "StorageClass": "STANDARD",
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
            "StorageClass": "STANDARD",
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
                ChecksumSHA256=f"{value['Checksum']['ChecksumSHA256']}-2"
            ),
            "checksum",
        ),
        (lambda value: value.update(ObjectSize=99), "size"),
        (lambda value: value.update(StorageClass="STANDARD"), "GLACIER_IR"),
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


@pytest.mark.parametrize(
    ("index", "storage_class"),
    [(0, "GLACIER_IR"), (1, "STANDARD")],
)
def test_wrong_inventory_storage_class_never_selects_a_recovery_point(
    index: int, storage_class: str
) -> None:
    value = inventory()
    value["Contents"][index]["StorageClass"] = storage_class
    with pytest.raises(FreshnessError, match="wrong storage class"):
        select_latest(value, now=NOW, maximum_age_seconds=86400)


def test_tampered_selection_storage_class_never_verifies() -> None:
    value = selection()
    value["ciphertext_storage_class"] = "STANDARD"
    with pytest.raises(FreshnessError, match="selected ciphertext storage class"):
        verify_latest(value, manifest(), attributes())
