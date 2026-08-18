#!/usr/bin/env python3
"""Render shared documentation artifact values from the claim registry.

``docs/published-version-claims.json`` is the only editable source for a
rendered version claim. Authored pages keep invisible, inline markers around
the generated value so the Markdown remains readable on GitHub and MkDocs.

Usage:
    python scripts/render_published_version_claims.py
    python scripts/render_published_version_claims.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "published-version-claims.json"

NAME = re.compile(r"[A-Za-z0-9_.-]+")
MARKER = re.compile(
    r"<!-- version-claim:(?P<id>[A-Za-z0-9_.-]+):"
    r"(?P<field>[A-Za-z0-9_.-]+) -->"
    r"(?P<value>[^<\r\n]+?)"
    r"<!-- /version-claim:(?P=id):(?P=field) -->"
)
CLAIM_COMMENT = re.compile(
    r"<!--(?:(?!-->).)*version-claim:(?:(?!-->).)*-->",
    re.DOTALL | re.IGNORECASE,
)
FIELD_PATTERNS = {
    "version": re.compile(r"\d+\.\d+\.\d+"),
    "release_commit": re.compile(r"[0-9a-f]{40}"),
    "wheel_sha256": re.compile(r"[0-9a-f]{64}"),
    "sdist_sha256": re.compile(r"[0-9a-f]{64}"),
}


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_version_claims(
    registry: dict,
    *,
    root: Path = ROOT,
    check: bool = False,
) -> tuple[list[str], list[Path]]:
    """Validate markers and render their claim versions.

    The function validates the complete marker inventory before it writes a
    file. This prevents a malformed or unregistered marker from producing a
    partial update.
    """

    errors: list[str] = []
    claims: dict[str, dict] = {}
    expected: Counter[tuple[str, str, str]] = Counter()

    for claim in registry.get("claims", []):
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not NAME.fullmatch(claim_id):
            errors.append("a rendered version claim has no valid id")
            continue
        if claim_id in claims:
            errors.append(f"duplicate claim id {claim_id!r}")
            continue
        claims[claim_id] = claim

        rendered_locations = claim.get("rendered_locations") or []
        for location in rendered_locations:
            file_name = location.get("file")
            if not isinstance(file_name, str) or not file_name.startswith("docs/"):
                errors.append(
                    f"claim {claim_id!r} has invalid rendered file {file_name!r}"
                )
                continue
            values = location.get("values")
            if not isinstance(values, dict) or not values:
                errors.append(
                    f"claim {claim_id!r} has no rendered values for {file_name}"
                )
                continue
            for field, count in values.items():
                if not isinstance(field, str) or not NAME.fullmatch(field):
                    errors.append(
                        f"claim {claim_id!r} has invalid rendered field {field!r}"
                    )
                    continue
                value = claim.get(field)
                if not isinstance(value, str) or not value:
                    errors.append(
                        f"claim {claim_id!r} has no value for rendered field "
                        f"{field!r}"
                    )
                pattern = FIELD_PATTERNS.get(field)
                if pattern is not None and (
                    not isinstance(value, str) or not pattern.fullmatch(value)
                ):
                    errors.append(
                        f"claim {claim_id!r} field {field!r} has invalid value "
                        f"{value!r}"
                    )
                if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                    errors.append(
                        f"claim {claim_id!r} has invalid marker count {count!r} "
                        f"for {file_name} field {field!r}"
                    )
                    continue
                expected[(file_name, claim_id, field)] += count

    docs_dir = root / "docs"
    actual: Counter[tuple[str, str, str]] = Counter()
    source_by_path: dict[Path, str] = {}
    for path in sorted(docs_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        source_by_path[path] = text
        matches = list(MARKER.finditer(text))
        if len(CLAIM_COMMENT.findall(text)) != len(matches) * 2:
            errors.append(
                f"{path.relative_to(root)} has an incomplete or malformed "
                "version-claim marker pair"
            )
        relative = path.relative_to(root).as_posix()
        for match in matches:
            actual[(relative, match.group("id"), match.group("field"))] += 1

    for key in sorted(set(expected) | set(actual)):
        expected_count = expected[key]
        actual_count = actual[key]
        if expected_count != actual_count:
            file_name, claim_id, field = key
            errors.append(
                f"claim {claim_id!r} field {field!r}: {file_name} has "
                f"{actual_count} rendered marker(s); the registry requires "
                f"{expected_count}"
            )

    if errors:
        return errors, []

    rendered_by_path: dict[Path, str] = {}
    for path, text in source_by_path.items():
        if not CLAIM_COMMENT.search(text):
            continue

        def replace(match: re.Match[str]) -> str:
            claim_id = match.group("id")
            field = match.group("field")
            value = str(claims[claim_id][field])
            return (
                f"<!-- version-claim:{claim_id}:{field} -->{value}"
                f"<!-- /version-claim:{claim_id}:{field} -->"
            )

        rendered_by_path[path] = MARKER.sub(replace, text)

    changed = [
        path
        for path, rendered in rendered_by_path.items()
        if source_by_path[path] != rendered
    ]
    if check and changed:
        rendered_names = ", ".join(
            path.relative_to(root).as_posix() for path in changed
        )
        errors.append(
            "rendered version claims are stale in "
            f"{rendered_names}; run "
            "`python scripts/render_published_version_claims.py`"
        )
        return errors, []

    if not check:
        for path in changed:
            path.write_text(rendered_by_path[path], encoding="utf-8")
    return [], changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when committed rendered values differ from the registry.",
    )
    args = parser.parse_args()

    try:
        registry = load_registry()
        errors, changed = render_version_claims(registry, check=args.check)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"ERROR: could not render published version claims: {exc}",
            file=sys.stderr,
        )
        return 1

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    if args.check:
        print("OK: rendered version claims match the registry.")
    elif changed:
        print(f"Updated {len(changed)} documentation file(s).")
    else:
        print("Rendered version claims are already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
