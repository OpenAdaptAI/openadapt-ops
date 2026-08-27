from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prepare_production_lifecycle_projection",
    ROOT / "scripts" / "prepare_production_lifecycle_projection.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


NOW = datetime(2026, 8, 27, 17, 0, tzinfo=timezone.utc)


def reference(
    *, kind: str, schema: str, media: str, digest: str, subject: str | None
) -> dict[str, object]:
    digest_hex = digest.removeprefix("sha256:")
    return {
        "schema_version": MODULE.REFERENCE_SCHEMA,
        "repository": MODULE.TARGET_REPOSITORY,
        "repository_id": MODULE.TARGET_REPOSITORY_ID,
        "repository_owner_id": MODULE.TARGET_OWNER_ID,
        "registry_source_commit": "9" * 40,
        "registry_revision": 14,
        "registry_head_sha256": "sha256:" + "d" * 64,
        "registry_entry_sha256": "sha256:" + "8" * 64,
        "kind": kind,
        "object_schema_version": schema,
        "object_path": (
            f"production-evidence/objects/sha256/{digest_hex[:2]}/"
            f"{digest_hex}.{kind}.json"
        ),
        "object_sha256": digest,
        "size_bytes": 128,
        "object_media_type": media,
        "semantic_identity_sha256": "sha256:" + "7" * 64,
        "subject_sha256": subject,
    }


def feed_bytes() -> bytes:
    checkpoint = "sha256:" + "c" * 64
    bundle = "sha256:" + "e" * 64
    signer_object = "sha256:" + "6" * 64
    signer_hex = signer_object.removeprefix("sha256:")
    value = {
        "schema_version": MODULE.FEED_SCHEMA,
        "repository": MODULE.TARGET_REPOSITORY,
        "repository_id": MODULE.TARGET_REPOSITORY_ID,
        "repository_owner_id": MODULE.TARGET_OWNER_ID,
        "ref": MODULE.TARGET_REF,
        "feed_revision": 9,
        "generated_at": "2026-08-27T16:00:00Z",
        "expires_at": "2026-08-28T16:00:00Z",
        "registry_source_commit": "9" * 40,
        "registry_revision": 14,
        "registry_head_sha256": "sha256:" + "d" * 64,
        "signer_registry": {
            "schema_version": MODULE.SIGNER_POINTER_SCHEMA,
            "object_path": (
                f"production-evidence/signer-registries/sha256/{signer_hex[:2]}/"
                f"{signer_hex}.qualification-signer-registry.json"
            ),
            "object_sha256": signer_object,
            "registry_identity_sha256": "sha256:" + "5" * 64,
            "registry_revision": 14,
        },
        "checkpoints": [
            {
                "checkpoint_reference": reference(
                    kind=MODULE.CHECKPOINT_KIND,
                    schema=MODULE.CHECKPOINT_SCHEMA,
                    media=MODULE.CHECKPOINT_MEDIA,
                    digest=checkpoint,
                    subject=None,
                ),
                "checkpoint_bundle_reference": reference(
                    kind=MODULE.CHECKPOINT_BUNDLE_KIND,
                    schema=MODULE.SIGSTORE_SCHEMA_MEDIA,
                    media=MODULE.SIGSTORE_SCHEMA_MEDIA,
                    digest=bundle,
                    subject=checkpoint,
                ),
            }
        ],
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def inputs() -> tuple[dict[str, object], bytes]:
    body = feed_bytes()
    value: dict[str, object] = {
        "source_commit": "a" * 40,
        "expected_old_commit": "f" * 40,
        "new_commit": "b" * 40,
        "feed_sha256": MODULE.sha256(body),
        "checkpoint_sha256": "sha256:" + "c" * 64,
        "registry_head_sha256": "sha256:" + "d" * 64,
        "expires_at": "2026-08-28T16:00:00Z",
    }
    unsigned = {
        "schema_version": MODULE.UPDATE_SCHEMA,
        "event_type": MODULE.EVENT_TYPE,
        "source_repository": MODULE.SOURCE_REPOSITORY,
        "source_repository_id": MODULE.SOURCE_REPOSITORY_ID,
        "source_ref": MODULE.SOURCE_REF,
        "source_commit": value["source_commit"],
        "target_repository": MODULE.TARGET_REPOSITORY,
        "target_repository_id": MODULE.TARGET_REPOSITORY_ID,
        "target_ref": MODULE.TARGET_REF,
        "expected_old_commit": value["expected_old_commit"],
        "new_commit": value["new_commit"],
        "feed_path": MODULE.FEED_PATH,
        "feed_sha256": value["feed_sha256"],
        "checkpoint_sha256": value["checkpoint_sha256"],
        "registry_head_sha256": value["registry_head_sha256"],
        "expires_at": value["expires_at"],
    }
    value["supplied_idempotency_key"] = MODULE.idempotency_key(unsigned)
    return value, body


def test_exact_feed_builds_one_closed_canonical_update() -> None:
    candidate, body = inputs()
    result = MODULE.prepare(**candidate, fetch_bytes=lambda _: body, now=NOW)
    assert set(result) == MODULE.UPDATE_FIELDS
    assert result["source_repository_id"] == "1172011294"
    assert result["target_repository_id"] == "858454062"
    assert result["target_ref"] == "refs/heads/production-lifecycle-feed"
    assert MODULE.canonical_json(result) == MODULE.canonical_json(
        json.loads(MODULE.canonical_json(result))
    )


def test_first_feed_creation_uses_json_null_old_commit() -> None:
    candidate, body = inputs()
    candidate["expected_old_commit"] = ""
    candidate_without_key = {
        "schema_version": MODULE.UPDATE_SCHEMA,
        "event_type": MODULE.EVENT_TYPE,
        "source_repository": MODULE.SOURCE_REPOSITORY,
        "source_repository_id": MODULE.SOURCE_REPOSITORY_ID,
        "source_ref": MODULE.SOURCE_REF,
        "source_commit": candidate["source_commit"],
        "target_repository": MODULE.TARGET_REPOSITORY,
        "target_repository_id": MODULE.TARGET_REPOSITORY_ID,
        "target_ref": MODULE.TARGET_REF,
        "expected_old_commit": None,
        "new_commit": candidate["new_commit"],
        "feed_path": MODULE.FEED_PATH,
        "feed_sha256": candidate["feed_sha256"],
        "checkpoint_sha256": candidate["checkpoint_sha256"],
        "registry_head_sha256": candidate["registry_head_sha256"],
        "expires_at": candidate["expires_at"],
    }
    candidate["supplied_idempotency_key"] = MODULE.idempotency_key(
        candidate_without_key
    )
    assert (
        MODULE.prepare(**candidate, fetch_bytes=lambda _: body, now=NOW)["expected_old_commit"]
        is None
    )


@pytest.mark.parametrize(
    "field",
    [
        "source_commit",
        "new_commit",
        "feed_sha256",
        "checkpoint_sha256",
        "registry_head_sha256",
        "expires_at",
        "supplied_idempotency_key",
    ],
)
def test_feed_update_fails_closed_for_mismatched_identity(field: str) -> None:
    candidate, body = inputs()
    candidate[field] = "wrong"
    with pytest.raises(MODULE.ProjectionInputError):
        MODULE.prepare(**candidate, fetch_bytes=lambda _: body, now=NOW)


def test_feed_update_rejects_checkpoint_not_named_by_feed() -> None:
    candidate, body = inputs()
    candidate["checkpoint_sha256"] = "sha256:" + "9" * 64
    with pytest.raises(MODULE.ProjectionInputError, match="not in the feed"):
        MODULE.prepare(**candidate, fetch_bytes=lambda _: body, now=NOW)


def test_feed_rejects_one_field_reference_and_expired_feed() -> None:
    candidate, body = inputs()
    value = json.loads(body)
    value["checkpoints"][0]["checkpoint_reference"] = {
        "object_sha256": "sha256:" + "c" * 64
    }
    malformed = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    candidate["feed_sha256"] = MODULE.sha256(malformed)
    with pytest.raises(MODULE.ProjectionInputError, match="not closed"):
        MODULE.prepare(**candidate, fetch_bytes=lambda _: malformed, now=NOW)
    with pytest.raises(MODULE.ProjectionInputError, match="future-valid"):
        MODULE.prepare(
            **inputs()[0], fetch_bytes=lambda _: body,
            now=datetime(2026, 8, 29, tzinfo=timezone.utc),
        )
