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
POLICY_SCHEMA_V3 = "openadapt.production-lifecycle-policy/v3"
SUPPORTED_POLICY_SCHEMAS = {POLICY_SCHEMA, POLICY_SCHEMA_V3}
ADMISSIONS_SCHEMA = "openadapt.production-lifecycle-admissions/v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_SOURCE_BYTES = 2 * 1024 * 1024
PROFILE_CLONE_URL = "https://github.com/OpenAdaptAI/.github.git"
# Retained v1 public bound. v3 policy is until-revoked and has no day cap.
RETAINED_PUBLIC_MAXIMUM_ADMISSION_DAYS = 30
PUBLIC_TARGET_CONTRACT = {
    "agent": {
        "lifecycle_scope": "repository",
        "lifecycle_subject": "openadapt-agent",
        "release_kind": "public_package",
        "required_claim_scope": "qualified_agent_bridge_release",
        "required_artifact_kinds": ["sdist", "wheel"],
        "artifact_authority_by_kind": {"sdist": "pypi", "wheel": "pypi"},
    },
    "capture": {
        "lifecycle_scope": "repository",
        "lifecycle_subject": "openadapt-capture",
        "release_kind": "public_package",
        "required_claim_scope": "qualified_native_recorder_release",
        "required_artifact_kinds": ["sdist", "wheel"],
        "artifact_authority_by_kind": {"sdist": "pypi", "wheel": "pypi"},
    },
    "cloud": {
        "lifecycle_scope": "repository",
        "lifecycle_subject": "openadapt-cloud",
        "release_kind": "private_deployment",
        "required_claim_scope": "qualified_workflow_control_plane_deployment",
        "required_artifact_kinds": [],
        "artifact_authority_by_kind": {},
    },
    "desktop": {
        "lifecycle_scope": "repository",
        "lifecycle_subject": "openadapt-desktop",
        "release_kind": "public_package",
        "required_claim_scope": "qualified_native_workflow_desktop_release",
        "required_artifact_kinds": [
            "linux-installer",
            "macos-installer",
            "sdist",
            "wheel",
            "windows-installer",
        ],
        "artifact_authority_by_kind": {
            "linux-installer": "github_release",
            "macos-installer": "github_release",
            "sdist": "pypi",
            "wheel": "pypi",
            "windows-installer": "github_release",
        },
    },
    "docs": {
        "lifecycle_scope": "public_surface",
        "lifecycle_subject": "docs.openadapt.ai",
        "release_kind": "public_deployment",
        "required_claim_scope": "production_documentation_deployment",
        "required_artifact_kinds": ["deployment-manifest", "site-archive"],
        "artifact_authority_by_kind": {
            "deployment-manifest": "managed_evidence",
            "site-archive": "managed_evidence",
        },
    },
    "flow": {
        "lifecycle_scope": "repository",
        "lifecycle_subject": "openadapt-flow",
        "release_kind": "public_package",
        "required_claim_scope": "qualified_workflow_runtime_release",
        "required_artifact_kinds": ["sdist", "wheel"],
        "artifact_authority_by_kind": {"sdist": "pypi", "wheel": "pypi"},
    },
    "openadapt": {
        "lifecycle_scope": "repository",
        "lifecycle_subject": "OpenAdapt",
        "release_kind": "public_package",
        "required_claim_scope": "qualified_workflow_launcher_release",
        "required_artifact_kinds": ["sdist", "wheel"],
        "artifact_authority_by_kind": {"sdist": "pypi", "wheel": "pypi"},
    },
}
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


def _local_profile_repo() -> Path | None:
    for candidate in (
        Path.home() / "oa" / "src" / ".github",
        Path("/Users/abrichr/oa/src/.github"),
    ):
        if (candidate / ".git").exists() or candidate.is_dir():
            git_dir = candidate / ".git"
            if git_dir.exists():
                return candidate
    return None


def materialize_commit(commit: str, dest: Path) -> None:
    """Materialize the exact profile commit so the validator can read evidence."""

    dest.mkdir(parents=True, exist_ok=True)
    local = _local_profile_repo()
    if local is not None:
        probe = subprocess.run(
            ["git", "-C", str(local), "cat-file", "-e", f"{commit}^{{commit}}"],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if probe.returncode == 0:
            archive = subprocess.run(
                ["git", "-C", str(local), "archive", "--format=tar", commit],
                check=True,
                capture_output=True,
                timeout=60,
            )
            subprocess.run(
                ["tar", "-xf", "-", "-C", str(dest)],
                check=True,
                input=archive.stdout,
                timeout=60,
            )
            return
    subprocess.run(
        ["git", "init", str(dest)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    subprocess.run(
        ["git", "-C", str(dest), "remote", "add", "origin", PROFILE_CLONE_URL],
        check=True,
        capture_output=True,
        timeout=30,
    )
    fetched = subprocess.run(
        ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", commit],
        check=False,
        capture_output=True,
        timeout=120,
    )
    if fetched.returncode != 0:
        detail = (fetched.stderr or fetched.stdout or b"").decode("utf-8", "replace")
        raise RenderError(f"canonical source commit could not be fetched: {detail.strip()}")
    subprocess.run(
        ["git", "-C", str(dest), "checkout", "--force", "FETCH_HEAD"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    head = subprocess.check_output(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        text=True,
        timeout=30,
    ).strip()
    if head != commit:
        raise RenderError("materialized source commit differs from the pin")


def read_pinned_files(source: Mapping[str, Any], tree: Path) -> dict[str, bytes]:
    inputs: dict[str, bytes] = {}
    for key in sorted(EXPECTED_FILE_KEYS):
        item = source["files"][key]
        path = tree / item["path"]
        try:
            body = path.read_bytes()
        except OSError as exc:
            raise RenderError(
                f"canonical source file {key} is missing from the source tree: {exc}"
            ) from exc
        if _digest_bytes(body) != item["sha256"]:
            raise RenderError(f"canonical source file {key} digest changed")
        inputs[key] = body
    return inputs


def validate_tree(tree: Path) -> None:
    """Run the exact canonical validator from the materialized source tree."""

    environment = dict(os.environ)
    environment["PYTHONPYCACHEPREFIX"] = str(tree / ".pycache")
    completed = subprocess.run(
        [
            sys.executable,
            str(tree / EXPECTED_PATHS["validator"]),
            "--root",
            str(tree),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=environment,
        cwd=str(tree),
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "validation failed").strip()
        raise RenderError(
            f"canonical Production lifecycle refused: {detail.splitlines()[-1]}"
        )


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
                "-S",
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


def _group_admissions(
    current_admissions: list[Any],
    *,
    tree: Path | None,
) -> dict[str, list[dict[str, Any]]]:
    by_target: dict[str, list[dict[str, Any]]] = {}
    for admission in current_admissions:
        if not isinstance(admission, dict):
            raise RenderError("canonical admission target is invalid")
        if isinstance(admission.get("target"), str):
            record = admission
            target_id = admission["target"]
        elif (
            admission.get("kind") == "qualification-release"
            and isinstance(admission.get("object_path"), str)
        ):
            if tree is None:
                raise RenderError(
                    "v2 qualification-release rows require the source tree"
                )
            path = tree / admission["object_path"]
            try:
                record = _load_json_bytes(
                    path.read_bytes(), "qualification-release object"
                )
            except OSError as exc:
                raise RenderError(
                    f"qualification-release object is missing: {exc}"
                ) from exc
            target_id = record.get("target")
            if not isinstance(target_id, str):
                raise RenderError("qualification-release object has no target")
        else:
            raise RenderError("canonical admission target is invalid")
        by_target.setdefault(target_id, []).append(record)
    return by_target


def _public_target_fields(target: Mapping[str, Any]) -> dict[str, Any]:
    target_id = target["id"]
    contract = PUBLIC_TARGET_CONTRACT.get(target_id)
    if contract is None:
        raise RenderError(f"canonical policy target is not public: {target_id!r}")
    if "lifecycle_scope" in target:
        return {
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
        }
    return {
        "id": target_id,
        "display_name": target["display_name"],
        "lifecycle_scope": contract["lifecycle_scope"],
        "lifecycle_subject": contract["lifecycle_subject"],
        "source_repository": target["source_repository"],
        "release_kind": contract["release_kind"],
        "required_claim_scope": contract["required_claim_scope"],
        "required_artifact_kinds": contract["required_artifact_kinds"],
        "package_index_project": target["package_index_project"],
        "artifact_authority_by_kind": contract["artifact_authority_by_kind"],
    }


def render(
    source: Mapping[str, Any],
    inputs: Mapping[str, bytes],
    *,
    tree: Path | None = None,
) -> dict[str, Any]:
    policy = _load_json_bytes(inputs["policy"], "canonical policy")
    admissions = _load_json_bytes(inputs["admissions"], "canonical admissions")
    if policy.get("schema_version") not in SUPPORTED_POLICY_SCHEMAS:
        raise RenderError("canonical policy schema is not supported")
    if admissions.get("schema_version") != ADMISSIONS_SCHEMA:
        raise RenderError("canonical admissions schema is not supported")
    policy_digest = source["files"]["policy"]["sha256"]
    if (
        policy.get("schema_version") == POLICY_SCHEMA
        and admissions.get("policy_sha256") != policy_digest
    ):
        raise RenderError("canonical admissions do not bind the exact policy")
    targets = policy.get("targets")
    current_admissions = admissions.get("admissions")
    if not isinstance(targets, list) or not isinstance(current_admissions, list):
        raise RenderError("canonical policy target or admission inventory is invalid")
    by_target = _group_admissions(current_admissions, tree=tree)
    rendered_targets: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise RenderError("canonical policy target is invalid")
        target_id = target["id"]
        target_admissions = by_target.pop(target_id, [])
        target_admissions.sort(key=lambda item: item["release_identity"]["sequence"])
        latest_admission = target_admissions[-1] if target_admissions else None
        rendered = _public_target_fields(target)
        rendered["latest_admission"] = latest_admission
        rendered["admission_history"] = target_admissions
        rendered_targets.append(rendered)
    if by_target:
        raise RenderError(
            f"canonical admissions contain unknown targets: {sorted(by_target)}"
        )
    maximum_admission_days = policy.get("maximum_admission_days")
    if maximum_admission_days is None:
        maximum_admission_days = RETAINED_PUBLIC_MAXIMUM_ADMISSION_DAYS
    return {
        "$schema": "schemas/production-lifecycle-public.schema.json",
        "schema_version": OUTPUT_SCHEMA,
        "source": source,
        "policy_revision": policy["revision"],
        "maximum_admission_days": maximum_admission_days,
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
        with tempfile.TemporaryDirectory(
            prefix="openadapt-production-policy-"
        ) as directory:
            tree = Path(directory) / "profile"
            materialize_commit(source["source_commit"], tree)
            inputs = read_pinned_files(source, tree)
            validate_tree(tree)
            output = encode(render(source, inputs, tree=tree))
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
