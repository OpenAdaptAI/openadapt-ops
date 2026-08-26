#!/usr/bin/env python3
"""Validate an exact documentation synchronization dispatch."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import yaml

REF = "refs/heads/main"
EVENT = "push"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
KEY = re.compile(r"^docs-sync:[0-9a-f]{64}$")
DOMAIN = b"OpenAdapt docs sync dispatch v1\0"


class DocsSyncError(ValueError):
    """The documentation dispatch does not match its exact contract."""


def allowed_repositories(path: Path) -> set[str]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("repos"), list):
        raise DocsSyncError("the repository inventory is invalid")
    allowed: set[str] = set()
    for entry in value["repos"]:
        if not isinstance(entry, dict):
            raise DocsSyncError("the repository inventory contains an invalid entry")
        repository = entry.get("github")
        if entry.get("changelog") is True and isinstance(repository, str):
            allowed.add(repository)
    if not allowed:
        raise DocsSyncError("the repository inventory has no public sync source")
    return allowed


def expected_idempotency_key(
    source_repository: str,
    source_ref: str,
    source_commit: str,
    source_event: str,
) -> str:
    fields = (source_repository, source_ref, source_commit, source_event)
    payload = DOMAIN + b"".join(value.encode("utf-8") + b"\0" for value in fields)
    return "docs-sync:" + hashlib.sha256(payload).hexdigest()


def validate(
    *,
    repositories: Path,
    source_repository: str,
    source_ref: str,
    source_commit: str,
    source_event: str,
    idempotency_key: str,
) -> None:
    if source_repository not in allowed_repositories(repositories):
        raise DocsSyncError("the source repository is not in the public sync inventory")
    if source_ref != REF:
        raise DocsSyncError("the source ref is not exact main")
    if source_event != EVENT:
        raise DocsSyncError("the source event is not a main push")
    if HEX40.fullmatch(source_commit) is None:
        raise DocsSyncError("the source commit is not an exact lowercase SHA")
    if KEY.fullmatch(idempotency_key) is None:
        raise DocsSyncError("the docs-sync idempotency key is malformed")
    expected = expected_idempotency_key(
        source_repository, source_ref, source_commit, source_event
    )
    if idempotency_key != expected:
        raise DocsSyncError("the docs-sync idempotency key does not match the source")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repositories", type=Path, required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-event", required=True)
    parser.add_argument("--idempotency-key", required=True)
    args = parser.parse_args()
    validate(
        repositories=args.repositories,
        source_repository=args.source_repository,
        source_ref=args.source_ref,
        source_commit=args.source_commit,
        source_event=args.source_event,
        idempotency_key=args.idempotency_key,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
