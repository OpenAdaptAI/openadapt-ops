#!/usr/bin/env python3
"""Render the public lifecycle from an exact, validated organization policy.

The source descriptor pins the canonical organization-profile commit and the
hash of every input.  The renderer fetches those exact bytes, runs the pinned
canonical validator, and only then writes the remote-safe public projection.
It never invents or downgrades lifecycle state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "production-lifecycle-source.json"
OUTPUT_PATH = ROOT / "docs" / "production-lifecycle.json"
SOURCE_SCHEMA = "openadapt.production-lifecycle-source/v1"
OUTPUT_SCHEMA = "openadapt.public-production-lifecycle/v1"
POLICY_SCHEMA = "openadapt.production-lifecycle-policy/v1"
ADMISSIONS_SCHEMA = "openadapt.production-lifecycle-admissions/v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_SOURCE_BYTES = 2 * 1024 * 1024
EXPECTED_FILE_KEYS = {
    "admissions",
    "admissions_schema",
    "evidence_registry",
    "evidence_registry_schema",
    "evidence_registry_validator",
    "evidence_manifest_schema",
    "evidence_summary_schema",
    "lifecycle",
    "policy",
    "policy_schema",
    "validator",
}
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


class RenderError(ValueError):
    """The public policy cannot be derived from verified canonical inputs."""


def _closed(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise RenderError(f"{label} must contain exactly {sorted(keys)}; got {actual}")
    return value


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _load_json_bytes(value: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RenderError(f"{label} is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise RenderError(f"{label} must be a JSON object")
    return parsed


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "openadapt-docs-production-lifecycle-renderer/1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_SOURCE_BYTES:
            raise RenderError("canonical lifecycle input exceeds the size limit")
        body = response.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES:
        raise RenderError("canonical lifecycle input exceeds the size limit")
    return body


def load_source(path: Path = SOURCE_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(
            f"production lifecycle source is missing or invalid: {exc}"
        ) from exc
    source = _closed(
        value,
        {"schema_version", "repository", "source_commit", "files"},
        "production lifecycle source",
    )
    if source["schema_version"] != SOURCE_SCHEMA:
        raise RenderError("production lifecycle source schema is not supported")
    if source["repository"] != "OpenAdaptAI/.github":
        raise RenderError("production lifecycle source repository is not canonical")
    commit = source["source_commit"]
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise RenderError("production lifecycle source commit is not exact")
    files = source["files"]
    if not isinstance(files, dict) or set(files) != EXPECTED_FILE_KEYS:
        raise RenderError("production lifecycle source file inventory is not exact")
    for key in sorted(EXPECTED_FILE_KEYS):
        item = _closed(files[key], {"path", "url", "sha256"}, f"source file {key}")
        if item["path"] != EXPECTED_PATHS[key]:
            raise RenderError(f"source file {key} path is not canonical")
        if (
            not isinstance(item["sha256"], str)
            or SHA256.fullmatch(item["sha256"]) is None
        ):
            raise RenderError(f"source file {key} digest is invalid")
        parsed = urlsplit(item["url"])
        expected_path = f"/OpenAdaptAI/.github/{commit}/{item['path']}"
        if (
            parsed.scheme != "https"
            or parsed.netloc != "raw.githubusercontent.com"
            or parsed.path != expected_path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise RenderError(f"source file {key} URL is not bound to the exact commit")
    return source


def fetch_inputs(
    source: Mapping[str, Any],
    *,
    fetch: Callable[[str], bytes] = _fetch,
) -> dict[str, bytes]:
    inputs: dict[str, bytes] = {}
    for key in sorted(EXPECTED_FILE_KEYS):
        item = source["files"][key]
        try:
            body = fetch(item["url"])
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise RenderError(
                f"canonical source file {key} could not be fetched: {exc}"
            ) from exc
        if _digest_bytes(body) != item["sha256"]:
            raise RenderError(f"canonical source file {key} digest changed")
        inputs[key] = body
    return inputs


def validate_inputs(inputs: Mapping[str, bytes]) -> None:
    """Run the exact canonical validator pinned by the source descriptor."""

    with tempfile.TemporaryDirectory(
        prefix="openadapt-production-policy-"
    ) as directory:
        root = Path(directory)
        for key, relative in EXPECTED_PATHS.items():
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(inputs[key])
        environment = dict(os.environ)
        environment["PYTHONPYCACHEPREFIX"] = str(root / ".pycache")
        completed = subprocess.run(
            [
                sys.executable,
                str(root / EXPECTED_PATHS["validator"]),
                "--root",
                str(root),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
        )
        if completed.returncode != 0:
            detail = (
                completed.stderr or completed.stdout or "validation failed"
            ).strip()
            raise RenderError(
                f"canonical Production lifecycle refused: {detail.splitlines()[-1]}"
            )


def render(source: Mapping[str, Any], inputs: Mapping[str, bytes]) -> dict[str, Any]:
    policy = _load_json_bytes(inputs["policy"], "canonical policy")
    admissions = _load_json_bytes(inputs["admissions"], "canonical admissions")
    if policy.get("schema_version") != POLICY_SCHEMA:
        raise RenderError("canonical policy schema is not supported")
    if admissions.get("schema_version") != ADMISSIONS_SCHEMA:
        raise RenderError("canonical admissions schema is not supported")
    policy_digest = source["files"]["policy"]["sha256"]
    if admissions.get("policy_sha256") != policy_digest:
        raise RenderError("canonical admissions do not bind the exact policy")
    targets = policy.get("targets")
    current_admissions = admissions.get("admissions")
    if not isinstance(targets, list) or not isinstance(current_admissions, list):
        raise RenderError("canonical policy target or admission inventory is invalid")
    by_target: dict[str, list[dict[str, Any]]] = {}
    for admission in current_admissions:
        if not isinstance(admission, dict) or not isinstance(
            admission.get("target"), str
        ):
            raise RenderError("canonical admission target is invalid")
        by_target.setdefault(admission["target"], []).append(admission)
    rendered_targets: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise RenderError("canonical policy target is invalid")
        target_id = target["id"]
        target_admissions = by_target.pop(target_id, [])
        target_admissions.sort(key=lambda item: item["release_identity"]["sequence"])
        latest_admission = target_admissions[-1] if target_admissions else None
        rendered_targets.append(
            {
                "id": target_id,
                "display_name": target["display_name"],
                "lifecycle_scope": target["lifecycle_scope"],
                "lifecycle_subject": target["lifecycle_subject"],
                "source_repository": target["source_repository"],
                "release_kind": target["release_kind"],
                "required_claim_scope": target["required_claim_scope"],
                "required_artifact_kinds": target["required_artifact_kinds"],
                "package_index_project": target["package_index_project"],
                "artifact_authority_by_kind": target["artifact_authority_by_kind"],
                "latest_admission": latest_admission,
                "admission_history": target_admissions,
            }
        )
    if by_target:
        raise RenderError(
            f"canonical admissions contain unknown targets: {sorted(by_target)}"
        )
    return {
        "$schema": "schemas/production-lifecycle-public.schema.json",
        "schema_version": OUTPUT_SCHEMA,
        "source": source,
        "policy_revision": policy["revision"],
        "maximum_admission_days": policy["maximum_admission_days"],
        "derivation": {
            "mode": "latest_signed_admission_at_read_time",
            "static_production_state": False,
            "expired_or_revoked_latest_behavior": "no_production",
            "fallback_to_older_release": False,
        },
        "targets": rendered_targets,
    }


def encode(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Refuse generated-output drift"
    )
    args = parser.parse_args()
    try:
        source = load_source()
        inputs = fetch_inputs(source)
        validate_inputs(inputs)
        output = encode(render(source, inputs))
        if args.check:
            if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != output:
                raise RenderError(
                    "docs/production-lifecycle.json differs from the exact canonical source"
                )
        else:
            temporary = OUTPUT_PATH.with_suffix(".json.tmp")
            temporary.write_bytes(output)
            temporary.replace(OUTPUT_PATH)
    except (OSError, RenderError, subprocess.SubprocessError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    action = "Validated" if args.check else "Rendered"
    print(f"{action} the public Production lifecycle from exact canonical inputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
