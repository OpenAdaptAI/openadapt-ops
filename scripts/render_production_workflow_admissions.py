#!/usr/bin/env python3
"""Render the public workflow-admission ledger from an exact source pin.

Pins OpenAdaptAI/.github `production-workflow-admissions.json`. Fetches those
bytes, refuses digest drift, and copies remote-safe fields from each referenced
qualification-admission object. It never invents admission rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "production-workflow-admissions-source.json"
OUTPUT_PATH = ROOT / "docs" / "production-workflow-admissions.json"
SOURCE_SCHEMA = "openadapt.production-workflow-admissions-source/v1"
OUTPUT_SCHEMA = "openadapt.public-production-workflow-admissions/v1"
LEDGER_SCHEMA = "openadapt.production-workflow-admissions/v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
PROFILE_CLONE_URL = "https://github.com/OpenAdaptAI/.github.git"
EXPECTED_FILE_KEYS = {"admissions"}
EXPECTED_PATHS = {"admissions": "production-workflow-admissions.json"}
REQUIRED_EVIDENCE_CLASS = "remote-safe-synthetic"
REQUIRED_BUNDLE_VERSION = "0.0.0-synthetic"
PUBLIC_OBJECT_FIELDS = ("bundle_version", "evidence_class", "expires_at", "verdict")


class RenderError(ValueError):
    """The public workflow ledger cannot be derived from verified inputs."""


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


def load_source(path: Path = SOURCE_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(
            f"production workflow admissions source is missing or invalid: {exc}"
        ) from exc
    source = _closed(
        value,
        {"schema_version", "repository", "source_commit", "files"},
        "production workflow admissions source",
    )
    if source["schema_version"] != SOURCE_SCHEMA:
        raise RenderError("production workflow admissions source schema is not supported")
    if source["repository"] != "OpenAdaptAI/.github":
        raise RenderError("production workflow admissions source repository is not canonical")
    commit = source["source_commit"]
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise RenderError("production workflow admissions source commit is not exact")
    files = source["files"]
    if not isinstance(files, dict) or set(files) != EXPECTED_FILE_KEYS:
        raise RenderError(
            "production workflow admissions source file inventory is not exact"
        )
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


def _local_profile_repo() -> Path | None:
    for candidate in (
        Path.home() / "oa" / "src" / ".github",
        Path("/Users/abrichr/oa/src/.github"),
    ):
        git_dir = candidate / ".git"
        if git_dir.exists():
            return candidate
    return None


def materialize_commit(commit: str, dest: Path) -> None:
    """Materialize the exact profile commit so object paths can be hashed."""

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
        raise RenderError(
            f"canonical source commit could not be fetched: {detail.strip()}"
        )
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


def render(
    source: Mapping[str, Any],
    inputs: Mapping[str, bytes],
    *,
    tree: Path,
) -> dict[str, Any]:
    ledger = _load_json_bytes(inputs["admissions"], "canonical workflow admissions")
    if ledger.get("schema_version") != LEDGER_SCHEMA:
        raise RenderError("canonical workflow admissions schema is not supported")
    if ledger.get("$schema") != "schemas/production-workflow-admissions.schema.json":
        raise RenderError("canonical workflow admissions document schema differs")
    rows = ledger.get("admissions")
    if not isinstance(rows, list) or not rows:
        raise RenderError("canonical workflow admissions must be a non-empty list")
    rendered_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RenderError(f"workflow admission {index} must be an object")
        if row.get("kind") != "qualification-admission":
            raise RenderError(
                f"workflow admission {index} is not a qualification-admission row"
            )
        object_path = row.get("object_path")
        object_sha256 = row.get("object_sha256")
        if not isinstance(object_path, str) or not isinstance(object_sha256, str):
            raise RenderError(f"workflow admission {index} object pointer is invalid")
        try:
            object_raw = (tree / object_path).read_bytes()
        except OSError as exc:
            raise RenderError(
                f"workflow admission {index} object is missing: {exc}"
            ) from exc
        if _digest_bytes(object_raw) != object_sha256:
            raise RenderError(f"workflow admission {index} object digest changed")
        admission = _load_json_bytes(object_raw, f"workflow admission {index} object")
        if admission.get("evidence_class") != REQUIRED_EVIDENCE_CLASS:
            raise RenderError(
                f"workflow admission {index} evidence class is not "
                f"{REQUIRED_EVIDENCE_CLASS}"
            )
        if admission.get("bundle_version") != REQUIRED_BUNDLE_VERSION:
            raise RenderError(
                f"workflow admission {index} is not the synthetic tutorial bundle"
            )
        serialized = json.dumps(admission, ensure_ascii=False)
        if "mockmed" in serialized.lower() or "production_acceptance" in admission:
            raise RenderError(
                f"workflow admission {index} must not invent MockMed "
                "production_acceptance"
            )
        public_row = dict(row)
        for field in PUBLIC_OBJECT_FIELDS:
            if field not in admission:
                raise RenderError(
                    f"workflow admission {index} is missing remote-safe field {field}"
                )
            public_row[field] = admission[field]
        rendered_rows.append(public_row)
    return {
        "schema_version": OUTPUT_SCHEMA,
        "source": source,
        "policy_sha256": ledger["policy_sha256"],
        "admissions": rendered_rows,
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
            prefix="openadapt-workflow-admissions-"
        ) as directory:
            tree = Path(directory) / "profile"
            materialize_commit(source["source_commit"], tree)
            inputs = read_pinned_files(source, tree)
            output = encode(render(source, inputs, tree=tree))
        if args.check:
            if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != output:
                raise RenderError(
                    "docs/production-workflow-admissions.json differs from the "
                    "exact canonical source"
                )
        else:
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            temporary = OUTPUT_PATH.with_suffix(".json.tmp")
            temporary.write_bytes(output)
            temporary.replace(OUTPUT_PATH)
    except (OSError, RenderError, subprocess.SubprocessError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    action = "Validated" if args.check else "Rendered"
    print(f"{action} the public workflow-admission ledger from exact canonical inputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
