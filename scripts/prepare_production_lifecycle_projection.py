#!/usr/bin/env python3
"""Validate and build one canonical Production lifecycle feed update."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

UPDATE_SCHEMA = "openadapt.production-lifecycle-feed-update/v1"
FEED_SCHEMA = "openadapt.production-lifecycle-feed/v1"
EVENT_TYPE = "production_lifecycle_feed_updated"
SOURCE_REPOSITORY = "OpenAdaptAI/openadapt-ops"
SOURCE_REPOSITORY_ID = "1172011294"
SOURCE_REF = "refs/heads/main"
TARGET_REPOSITORY = "OpenAdaptAI/.github"
TARGET_REPOSITORY_ID = "858454062"
TARGET_OWNER_ID = "132681217"
TARGET_REF = "refs/heads/production-lifecycle-feed"
FEED_PATH = "production-lifecycle-feed.json"
IDEMPOTENCY_DOMAIN = b"OpenAdapt production lifecycle feed update idempotency v1\0"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
IDEMPOTENCY = re.compile(r"^lifecycle-feed-update:[0-9a-f]{64}$")
MAX_FEED_BYTES = 2 * 1024 * 1024
UPDATE_FIELDS = {
    "schema_version",
    "event_type",
    "source_repository",
    "source_repository_id",
    "source_ref",
    "source_commit",
    "target_repository",
    "target_repository_id",
    "target_ref",
    "expected_old_commit",
    "new_commit",
    "feed_path",
    "feed_sha256",
    "checkpoint_sha256",
    "registry_head_sha256",
    "expires_at",
    "idempotency_key",
}
FEED_FIELDS = {
    "schema_version",
    "repository",
    "repository_id",
    "repository_owner_id",
    "ref",
    "feed_revision",
    "generated_at",
    "expires_at",
    "registry_source_commit",
    "registry_revision",
    "registry_head_sha256",
    "signer_registry",
    "checkpoints",
}


class ProjectionInputError(ValueError):
    """The feed update is malformed or does not match the exact feed bytes."""


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def idempotency_key(value_without_key: Mapping[str, Any]) -> str:
    return (
        "lifecycle-feed-update:"
        + hashlib.sha256(
            IDEMPOTENCY_DOMAIN + canonical_json(value_without_key)
        ).hexdigest()
    )


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "openadapt-lifecycle-feed-source/1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(MAX_FEED_BYTES + 1)
    if len(body) > MAX_FEED_BYTES:
        raise ProjectionInputError("the lifecycle feed exceeds the size limit")
    return body


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProjectionInputError(f"the lifecycle feed repeats field {key!r}")
        result[key] = value
    return result


def _parse_feed(body: bytes) -> Mapping[str, Any]:
    try:
        value = json.loads(body, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectionInputError(
            "the lifecycle feed is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(value, Mapping) or set(value) != FEED_FIELDS:
        raise ProjectionInputError(
            "the lifecycle feed does not have the closed field set"
        )
    return value


def _validate_feed(
    feed: Mapping[str, Any],
    *,
    new_commit: str,
    feed_sha256: str,
    checkpoint_sha256: str,
    registry_head_sha256: str,
    expires_at: str,
    body: bytes,
) -> None:
    if feed.get("schema_version") != FEED_SCHEMA:
        raise ProjectionInputError("the lifecycle feed schema is not exact")
    if (
        feed.get("repository") != TARGET_REPOSITORY
        or feed.get("repository_id") != TARGET_REPOSITORY_ID
        or feed.get("repository_owner_id") != TARGET_OWNER_ID
        or feed.get("ref") != TARGET_REF
    ):
        raise ProjectionInputError(
            "the lifecycle feed repository identity is not exact"
        )
    if feed.get("registry_source_commit") != new_commit:
        raise ProjectionInputError(
            "the feed registry source commit is not the new commit"
        )
    if sha256(body) != feed_sha256:
        raise ProjectionInputError("the feed digest does not match the exact bytes")
    if feed.get("registry_head_sha256") != registry_head_sha256:
        raise ProjectionInputError("the feed registry head does not match")
    if feed.get("expires_at") != expires_at:
        raise ProjectionInputError("the feed expiry does not match")
    checkpoints = feed.get("checkpoints")
    if not isinstance(checkpoints, list) or len(checkpoints) not in {1, 2}:
        raise ProjectionInputError("the feed must contain one or two checkpoints")
    checkpoint_digests: list[str] = []
    for pair in checkpoints:
        if not isinstance(pair, Mapping) or set(pair) != {
            "checkpoint_reference",
            "checkpoint_bundle_reference",
        }:
            raise ProjectionInputError("a feed checkpoint pair is not closed")
        reference = pair["checkpoint_reference"]
        if not isinstance(reference, Mapping):
            raise ProjectionInputError("a checkpoint reference is not an object")
        digest = reference.get("object_sha256")
        if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            raise ProjectionInputError("a checkpoint reference digest is malformed")
        checkpoint_digests.append(digest)
    if checkpoint_sha256 not in checkpoint_digests:
        raise ProjectionInputError("the named checkpoint is not in the feed")


def prepare(
    *,
    source_commit: str,
    expected_old_commit: str | None,
    new_commit: str,
    feed_sha256: str,
    checkpoint_sha256: str,
    registry_head_sha256: str,
    expires_at: str,
    supplied_idempotency_key: str,
    fetch_bytes: Callable[[str], bytes] = fetch,
) -> dict[str, Any]:
    if HEX40.fullmatch(source_commit) is None or HEX40.fullmatch(new_commit) is None:
        raise ProjectionInputError("source_commit and new_commit must be exact SHAs")
    if expected_old_commit == "":
        expected_old_commit = None
    if expected_old_commit is not None and HEX40.fullmatch(expected_old_commit) is None:
        raise ProjectionInputError("expected_old_commit must be null or an exact SHA")
    for label, value in (
        ("feed", feed_sha256),
        ("checkpoint", checkpoint_sha256),
        ("registry head", registry_head_sha256),
    ):
        if SHA256.fullmatch(value) is None:
            raise ProjectionInputError(f"the {label} digest is malformed")
    if not isinstance(expires_at, str) or not expires_at:
        raise ProjectionInputError("expires_at is required")
    if IDEMPOTENCY.fullmatch(supplied_idempotency_key) is None:
        raise ProjectionInputError("the idempotency key is malformed")
    url = (
        "https://raw.githubusercontent.com/"
        f"{TARGET_REPOSITORY}/{new_commit}/{FEED_PATH}"
    )
    body = fetch_bytes(url)
    if len(body) > MAX_FEED_BYTES:
        raise ProjectionInputError("the lifecycle feed exceeds the size limit")
    _validate_feed(
        _parse_feed(body),
        new_commit=new_commit,
        feed_sha256=feed_sha256,
        checkpoint_sha256=checkpoint_sha256,
        registry_head_sha256=registry_head_sha256,
        expires_at=expires_at,
        body=body,
    )
    update: dict[str, Any] = {
        "schema_version": UPDATE_SCHEMA,
        "event_type": EVENT_TYPE,
        "source_repository": SOURCE_REPOSITORY,
        "source_repository_id": SOURCE_REPOSITORY_ID,
        "source_ref": SOURCE_REF,
        "source_commit": source_commit,
        "target_repository": TARGET_REPOSITORY,
        "target_repository_id": TARGET_REPOSITORY_ID,
        "target_ref": TARGET_REF,
        "expected_old_commit": expected_old_commit,
        "new_commit": new_commit,
        "feed_path": FEED_PATH,
        "feed_sha256": feed_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "registry_head_sha256": registry_head_sha256,
        "expires_at": expires_at,
    }
    expected_key = idempotency_key(update)
    if supplied_idempotency_key != expected_key:
        raise ProjectionInputError("the idempotency key does not bind the update")
    update["idempotency_key"] = supplied_idempotency_key
    if set(update) != UPDATE_FIELDS:
        raise AssertionError("the update builder emitted the wrong field set")
    return update


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--expected-old-commit", default="")
    parser.add_argument("--new-commit", required=True)
    parser.add_argument("--feed-sha256", required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--registry-head-sha256", required=True)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = prepare(
        source_commit=args.source_commit,
        expected_old_commit=args.expected_old_commit,
        new_commit=args.new_commit,
        feed_sha256=args.feed_sha256,
        checkpoint_sha256=args.checkpoint_sha256,
        registry_head_sha256=args.registry_head_sha256,
        expires_at=args.expires_at,
        supplied_idempotency_key=args.idempotency_key,
    )
    args.output.write_bytes(canonical_json(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
