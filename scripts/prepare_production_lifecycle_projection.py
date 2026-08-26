#!/usr/bin/env python3
"""Prepare an exact canonical source descriptor for a lifecycle projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections.abc import Callable
from pathlib import Path

SOURCE_SCHEMA = "openadapt.production-lifecycle-source/v1"
SOURCE_REPOSITORY = "OpenAdaptAI/.github"
SOURCE_REF = "refs/heads/main"
SOURCE_EVENT = "production_lifecycle_ledger_changed"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_SOURCE_BYTES = 2 * 1024 * 1024
LEDGER_DOMAIN = b"OpenAdapt production lifecycle ledger head v1\0"
IDEMPOTENCY_DOMAIN = b"OpenAdapt production lifecycle projection idempotency v1\0"
EXPECTED_PATHS = {
    "admissions": "production-lifecycle-admissions.json",
    "admissions_schema": "schemas/production-lifecycle-admissions.schema.json",
    "evidence_registry": "evidence-registry.json",
    "evidence_registry_schema": "schemas/evidence-registry.schema.json",
    "evidence_registry_validator": "scripts/validate_evidence_registry.py",
    "evidence_manifest_schema": (
        "schemas/production-lifecycle-evidence-manifest.schema.json"
    ),
    "evidence_summary_schema": (
        "schemas/production-lifecycle-evidence-summary.schema.json"
    ),
    "lifecycle": "repository-lifecycle.yml",
    "policy": "production-lifecycle-policy.json",
    "policy_schema": "schemas/production-lifecycle-policy.schema.json",
    "validator": "scripts/validate_production_lifecycle.py",
}


class ProjectionInputError(ValueError):
    """The lifecycle projection input is not exact or internally consistent."""


def digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _digest_fields(domain: bytes, fields: tuple[str, ...]) -> str:
    payload = domain + b"".join(value.encode("ascii") + b"\0" for value in fields)
    return digest(payload)


def ledger_head_sha256(admissions_sha256: str, evidence_registry_sha256: str) -> str:
    return _digest_fields(LEDGER_DOMAIN, (admissions_sha256, evidence_registry_sha256))


def projection_idempotency_key(
    *,
    source_commit: str,
    candidate_admissions_sha256: str,
    candidate_ledger_head_sha256: str,
) -> str:
    return _digest_fields(
        IDEMPOTENCY_DOMAIN,
        (
            SOURCE_EVENT,
            SOURCE_REPOSITORY,
            SOURCE_REF,
            source_commit,
            candidate_admissions_sha256,
            candidate_ledger_head_sha256,
        ),
    )


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "openadapt-lifecycle-projection/1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES:
        raise ProjectionInputError("a canonical source file exceeds the size limit")
    return body


def build_source(
    source_commit: str,
    *,
    fetch_bytes: Callable[[str], bytes] = fetch,
) -> tuple[dict[str, object], dict[str, bytes]]:
    if HEX40.fullmatch(source_commit) is None:
        raise ProjectionInputError("the source commit is not an exact lowercase SHA")
    files: dict[str, dict[str, str]] = {}
    contents: dict[str, bytes] = {}
    for key, path in sorted(EXPECTED_PATHS.items()):
        url = (
            "https://raw.githubusercontent.com/"
            f"{SOURCE_REPOSITORY}/{source_commit}/{path}"
        )
        body = fetch_bytes(url)
        if len(body) > MAX_SOURCE_BYTES:
            raise ProjectionInputError("a canonical source file exceeds the size limit")
        contents[key] = body
        files[key] = {"path": path, "url": url, "sha256": digest(body)}
    return (
        {
            "schema_version": SOURCE_SCHEMA,
            "repository": SOURCE_REPOSITORY,
            "source_commit": source_commit,
            "files": files,
        },
        contents,
    )


def prepare(
    *,
    source_commit: str,
    source_repository: str,
    source_ref: str,
    source_event: str,
    candidate_admissions_sha256: str,
    candidate_ledger_head_sha256: str,
    idempotency_key: str,
    fetch_bytes: Callable[[str], bytes] = fetch,
) -> dict[str, object]:
    if source_repository != SOURCE_REPOSITORY:
        raise ProjectionInputError("the source repository is not canonical")
    if source_ref != SOURCE_REF:
        raise ProjectionInputError("the source ref is not exact main")
    if source_event != SOURCE_EVENT:
        raise ProjectionInputError("the source event is not canonical")
    for label, value in (
        ("candidate admissions", candidate_admissions_sha256),
        ("candidate ledger head", candidate_ledger_head_sha256),
        ("idempotency key", idempotency_key),
    ):
        if SHA256.fullmatch(value) is None:
            raise ProjectionInputError(f"the {label} digest is malformed")

    source, contents = build_source(source_commit, fetch_bytes=fetch_bytes)
    actual_admissions = digest(contents["admissions"])
    if candidate_admissions_sha256 != actual_admissions:
        raise ProjectionInputError("the admissions digest does not match the source")
    actual_head = ledger_head_sha256(
        actual_admissions, digest(contents["evidence_registry"])
    )
    if candidate_ledger_head_sha256 != actual_head:
        raise ProjectionInputError("the lifecycle ledger head does not match the source")
    expected_idempotency = projection_idempotency_key(
        source_commit=source_commit,
        candidate_admissions_sha256=actual_admissions,
        candidate_ledger_head_sha256=actual_head,
    )
    if idempotency_key != expected_idempotency:
        raise ProjectionInputError("the projection idempotency key does not match")
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-event", required=True)
    parser.add_argument("--candidate-admissions-sha256", required=True)
    parser.add_argument("--candidate-ledger-head-sha256", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = prepare(
        source_commit=args.source_commit,
        source_repository=args.source_repository,
        source_ref=args.source_ref,
        source_event=args.source_event,
        candidate_admissions_sha256=args.candidate_admissions_sha256,
        candidate_ledger_head_sha256=args.candidate_ledger_head_sha256,
        idempotency_key=args.idempotency_key,
    )
    args.output.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
