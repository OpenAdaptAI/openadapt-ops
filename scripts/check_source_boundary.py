#!/usr/bin/env python3
"""Enforce the generated public source policy on docs source and site output."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "source-policy.public.json"
POLICY_SCHEMA_VERSION = 1
REPOSITORY_NAME = "openadapt-ops"
REPOSITORY_SLUG = "OpenAdaptAI/openadapt-ops"

# These files implement or carry the policy, so their literal rules are data.
SOURCE_ALLOWLIST = frozenset(
    {
        "scripts/check_source_boundary.py",
        "source-policy.public.json",
        "tests/test_source_boundary.py",
    }
)


class PolicyError(RuntimeError):
    """The generated policy cannot be enforced safely."""


class ScanError(RuntimeError):
    """The complete source or generated site cannot be scanned."""


def _strings(container: dict, key: str, where: str) -> tuple[str, ...]:
    value = container.get(key)
    if not isinstance(value, list) or not value:
        raise PolicyError(f"{where}.{key} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise PolicyError(f"{where}.{key} must contain non-empty strings")
    return tuple(value)


def _regex(patterns: Iterable[str], where: str) -> re.Pattern[str]:
    try:
        return re.compile(
            "|".join(f"(?:{pattern})" for pattern in patterns), re.IGNORECASE
        )
    except re.error as exc:
        raise PolicyError(
            f"{where} contains an invalid regular expression: {exc}"
        ) from exc


@dataclass(frozen=True)
class SourcePolicy:
    path_tokens: tuple[str, ...]
    private_path_segments: frozenset[str]
    content_signatures: tuple[bytes, ...]
    source_content_regex: re.Pattern[str]
    built_path_prefixes: tuple[str, ...]
    built_content_regex: re.Pattern[str]
    policy_digest: str
    policy_last_updated: str

    @classmethod
    def from_document(cls, document: object) -> SourcePolicy:
        if not isinstance(document, dict):
            raise PolicyError("the rendered policy must be a JSON object")
        if document.get("schema_version") != POLICY_SCHEMA_VERSION:
            raise PolicyError(
                "the rendered policy uses an unknown or missing schema_version"
            )
        policy_digest = document.get("policy_digest")
        if not isinstance(policy_digest, str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", policy_digest
        ):
            raise PolicyError("policy_digest must be a lowercase sha256 digest")
        policy_last_updated = document.get("policy_last_updated")
        if not isinstance(policy_last_updated, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", policy_last_updated
        ):
            raise PolicyError("policy_last_updated must use YYYY-MM-DD")

        crown_jewels = frozenset(_strings(document, "crown_jewel_categories", "policy"))
        repositories = document.get("public_repositories")
        if not isinstance(repositories, dict):
            raise PolicyError("public_repositories must be an object")
        repository = repositories.get(REPOSITORY_NAME)
        if not isinstance(repository, dict):
            raise PolicyError(f"public_repositories.{REPOSITORY_NAME} is missing")
        if repository.get("classification") != "public":
            raise PolicyError(f"public_repositories.{REPOSITORY_NAME} must be public")
        if repository.get("slug") != REPOSITORY_SLUG:
            raise PolicyError(
                f"public_repositories.{REPOSITORY_NAME}.slug must be "
                f"{REPOSITORY_SLUG}"
            )
        must_not_contain = repository.get("must_not_contain")
        if (
            not isinstance(must_not_contain, list)
            or any(not isinstance(item, str) for item in must_not_contain)
            or frozenset(must_not_contain) != crown_jewels
        ):
            raise PolicyError(
                f"public_repositories.{REPOSITORY_NAME}.must_not_contain must "
                "contain every crown-jewel category"
            )

        enforcement = document.get("enforcement")
        if not isinstance(enforcement, dict):
            raise PolicyError("enforcement must be an object")
        path_tokens = tuple(
            item.lower() for item in _strings(enforcement, "path_tokens", "enforcement")
        )
        private_segments = frozenset(
            item.lower()
            for item in _strings(enforcement, "private_path_segments", "enforcement")
        )

        signature_parts = enforcement.get("content_signature_parts")
        if not isinstance(signature_parts, list) or not signature_parts:
            raise PolicyError(
                "enforcement.content_signature_parts must be a non-empty list"
            )
        signatures: list[bytes] = []
        for parts in signature_parts:
            if (
                not isinstance(parts, list)
                or not parts
                or any(not isinstance(part, str) or not part for part in parts)
            ):
                raise PolicyError(
                    "each enforcement.content_signature_parts entry must contain "
                    "non-empty strings"
                )
            signatures.append("".join(parts).encode("utf-8"))

        repository_tree = enforcement.get("repository_tree")
        if not isinstance(repository_tree, dict):
            raise PolicyError("enforcement.repository_tree must be an object")
        source_patterns = _strings(
            repository_tree,
            "content_patterns",
            "enforcement.repository_tree",
        )

        built_artifacts = enforcement.get("built_artifacts")
        if not isinstance(built_artifacts, dict):
            raise PolicyError("enforcement.built_artifacts must be an object")
        built_prefixes = tuple(
            value.strip("/").lower()
            for value in _strings(
                built_artifacts,
                "path_prefixes",
                "enforcement.built_artifacts",
            )
        )
        built_patterns = _strings(
            built_artifacts,
            "content_patterns",
            "enforcement.built_artifacts",
        )

        return cls(
            path_tokens=path_tokens,
            private_path_segments=private_segments,
            content_signatures=tuple(signatures),
            source_content_regex=_regex(
                source_patterns, "enforcement.repository_tree.content_patterns"
            ),
            built_path_prefixes=built_prefixes,
            built_content_regex=_regex(
                built_patterns, "enforcement.built_artifacts.content_patterns"
            ),
            policy_digest=policy_digest,
            policy_last_updated=policy_last_updated,
        )


def load_policy(path: Path = POLICY_PATH) -> SourcePolicy:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyError(
            f"cannot read the rendered source policy {path}: {exc}"
        ) from exc
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyError(f"{path} is not valid JSON: {exc}") from exc
    return SourcePolicy.from_document(document)


def _path_violations(relative_path: str, policy: SourcePolicy) -> list[str]:
    normalized = relative_path.replace(os.sep, "/").strip("/")
    pure = PurePosixPath(normalized)
    if not normalized or pure.is_absolute() or ".." in pure.parts:
        return [f"{relative_path}: unsafe path"]

    lower = normalized.lower()
    violations: list[str] = []
    token = next((item for item in policy.path_tokens if item in lower), None)
    if token:
        violations.append(f"{relative_path}: path contains denylisted token {token!r}")
    segment = next(
        (part for part in lower.split("/") if part in policy.private_path_segments),
        None,
    )
    if segment:
        violations.append(
            f"{relative_path}: path lies under private segment {segment!r}"
        )
    prefix = next(
        (
            item
            for item in policy.built_path_prefixes
            if lower == item or lower.startswith(item + "/")
        ),
        None,
    )
    if prefix:
        violations.append(
            f"{relative_path}: path matches forbidden build prefix {prefix!r}"
        )
    return violations


def _content_violations(
    relative_path: str,
    data: bytes,
    policy: SourcePolicy,
    *,
    generated: bool,
) -> list[str]:
    for signature in policy.content_signatures:
        if signature in data:
            return [f"{relative_path}: content carries a private-artifact signature"]

    text = data.decode("utf-8", errors="ignore")
    regexes = (
        (policy.built_content_regex, "forbidden build-content pattern"),
        (policy.source_content_regex, "forbidden source-content pattern"),
    )
    if generated:
        regexes = regexes[:1]
    violations: list[str] = []
    for regex, label in regexes:
        match = regex.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            violations.append(
                f"{relative_path}:{line}: content matches {label} "
                f"{match.group(0)!r}"
            )
    return violations


def _tracked_files(root: Path) -> list[tuple[str, str]]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--stage", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScanError(f"git ls-files failed in {root}: {exc}") from exc

    entries: list[tuple[str, str]] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, encoded_path = record.split(b"\t", 1)
            mode = metadata.split(b" ", 1)[0].decode("ascii")
            relative_path = encoded_path.decode("utf-8", errors="surrogateescape")
        except (ValueError, UnicodeError) as exc:
            raise ScanError("git ls-files returned an invalid tracked entry") from exc
        entries.append((mode, relative_path))
    return entries


def scan_tracked_source(root: Path, policy: SourcePolicy) -> list[str]:
    violations: list[str] = []
    for mode, relative_path in _tracked_files(root):
        if relative_path in SOURCE_ALLOWLIST:
            continue
        violations.extend(_path_violations(relative_path, policy))
        path = root / relative_path
        if mode == "120000":
            violations.append(
                f"{relative_path}: tracked source contains a symbolic link"
            )
            continue
        if not path.is_file():
            violations.append(f"{relative_path}: tracked entry is not a regular file")
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ScanError(f"cannot read tracked file {relative_path}: {exc}") from exc
        violations.extend(
            _content_violations(relative_path, data, policy, generated=False)
        )
    return violations


def scan_generated_site(site: Path, policy: SourcePolicy) -> list[str]:
    if not site.is_dir():
        raise ScanError(f"generated site directory does not exist: {site}")
    violations: list[str] = []
    for path in sorted(site.rglob("*")):
        relative_path = path.relative_to(site).as_posix()
        if path.is_symlink():
            violations.append(
                f"{relative_path}: generated site contains a symbolic link"
            )
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            violations.append(
                f"{relative_path}: generated site entry is not a regular file"
            )
            continue
        violations.extend(_path_violations(relative_path, policy))
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ScanError(
                f"cannot read generated file {relative_path}: {exc}"
            ) from exc
        violations.extend(
            _content_violations(relative_path, data, policy, generated=True)
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument(
        "--site",
        type=Path,
        default=None,
        help="Also scan every regular file in this generated MkDocs site.",
    )
    args = parser.parse_args(argv)

    try:
        policy = load_policy(args.policy)
        root = args.root.resolve(strict=True)
        violations = scan_tracked_source(root, policy)
        if args.site is not None:
            site = args.site if args.site.is_absolute() else root / args.site
            violations.extend(scan_generated_site(site, policy))
    except (OSError, PolicyError, ScanError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    if violations:
        print("Source-availability boundary violations found.", file=sys.stderr)
        for violation in violations:
            print(f"ERROR: {violation}", file=sys.stderr)
        return 1

    scope = "tracked source and generated site" if args.site else "tracked source"
    print(
        f"OK: {scope} pass source policy {policy.policy_digest} "
        f"({policy.policy_last_updated})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
