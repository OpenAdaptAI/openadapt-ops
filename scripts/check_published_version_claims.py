#!/usr/bin/env python3
"""Fail loudly when docs.openadapt.ai advertises a superseded release.

On 2026-07-27 ``openadapt-flow`` 1.24.0 published and four sentences on
docs.openadapt.ai -- one of them on the security-review page -- still asserted
that the live runner reported "the published Flow 1.23.0 identity". The number
was correct at that time because the managed runtime pinned 1.23.0; the word
*published* was what became false. Nothing could detect that, because no
machine-readable record said which numbers in these docs are supposed to track
the current release and which are deliberately frozen.

``docs/published-version-claims.json`` is that record. This script enforces it.

Offline checks (run on every pull request; no network, cannot be flaky):

1. Every registered claim location still exists and still contains its exact
   recorded context. A reword that turns a pinned or historical number back
   into a publication claim therefore cannot land silently.
2. No authored page contains a "published X.Y.Z"-shaped sentence that is not
   registered as ``pypi-latest``. This is the specific sentence shape that went
   wrong; adding another one now requires declaring that it must track PyPI.
3. ``docs/changelog.md`` parses and every tracked repository has releases.

Network checks (run daily; PyPI is the authority):

4. Every ``pypi-latest`` claim's version equals PyPI's newest release.
5. The newest ``vX.Y.Z`` entry in each tracked section of ``docs/changelog.md``
   equals PyPI's newest release for that package. The changelog is the docs'
   always-live statement of "what the current release is", so it is guarded
   structurally rather than by phrase.

A changelog entry BEHIND PyPI is stale docs and fails. One AHEAD of PyPI is a
release whose PyPI upload has not landed yet and warns. An unreachable PyPI
warns rather than fails: an index outage is not evidence of drift, and a guard
that goes red for reasons unrelated to its subject stops being read -- that is
exactly how the 1.23.0 drift survived in the sibling launcher repository.

Standard library only: no dependency install, no lockfile, no cache.

Usage:
    python scripts/check_published_version_claims.py [--offline]
        [--require-network]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "published-version-claims.json"
CHANGELOG_PATH = ROOT / "docs" / "changelog.md"
DOCS_DIR = ROOT / "docs"
PYPI_URL_TEMPLATE = "https://pypi.org/pypi/{package}/json"
HTTP_TIMEOUT_SECONDS = 30

# The sentence shape that went wrong: prose asserting that some version is the
# published/current one. Both orderings ("published Flow 1.23.0" and "1.23.0 is
# the current published release") are matched, bounded to a single sentence so
# an unrelated version elsewhere in the paragraph cannot be swept in.
PUBLICATION_CLAIM_PATTERNS = (
    re.compile(
        r"(?i)\b(?:current(?:ly)?|latest)?\s*published\b[^.\n]{0,70}?\bv?\d+\.\d+\.\d+\b"
    ),
    re.compile(
        r"(?i)\bv?\d+\.\d+\.\d+\b[^.\n]{0,50}?\b(?:is\s+the\s+)?"
        r"(?:current(?:ly)?|latest)\s+published\b"
    ),
)

CHANGELOG_SECTION = re.compile(r"^##\s+(?P<name>\S+)\s*$")
CHANGELOG_ENTRY = re.compile(r"^-\s+\*\*\[(?P<tag>[^\]]+)\]")
SEMVER_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def release_tuple(version: str) -> tuple[int, ...] | None:
    """Numeric release segment of a version, or None if not comparable."""
    parts = version.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Offline checks
# --------------------------------------------------------------------------


def check_claim_locations(registry: dict, report: Report, root: Path = ROOT) -> None:
    """Every registered claim must still say what the registry says it says."""
    for claim in registry.get("claims", []):
        locations = claim.get("locations") or []
        if not locations:
            report.error(
                f"claim {claim.get('id')!r} registers no locations; a claim "
                "nothing points at cannot be kept honest"
            )
        for location in locations:
            path = root / location["file"]
            if not path.is_file():
                report.error(
                    f"claim {claim.get('id')!r}: {location['file']} does not exist"
                )
                continue
            if location["context"] not in path.read_text(encoding="utf-8"):
                report.error(
                    f"claim {claim.get('id')!r} ({claim.get('kind')}, "
                    f"{claim.get('package')} {claim.get('version')}): "
                    f"{location['file']} no longer contains its registered "
                    f"context {location['context']!r}. Either restore the text "
                    "or update docs/published-version-claims.json in the same "
                    "change, so a reword cannot quietly turn a pinned or "
                    "historical version into a claim about the current release."
                )


def scan_for_unregistered_claims(
    registry: dict, report: Report, root: Path = ROOT
) -> None:
    """No authored page may assert a published version that is not registered.

    Auto-generated aggregations are skipped: they restate upstream release
    notes verbatim and are historical records of what a release said, not
    authored claims. ``docs/changelog.md`` is instead guarded structurally.
    """
    generated = {
        (root / name).resolve() for name in registry.get("generated_pages", [])
    }
    registered = {
        claim["version"]
        for claim in registry.get("claims", [])
        if claim.get("kind") == "pypi-latest"
    }
    docs = root / "docs"
    for path in sorted(docs.rglob("*.md")):
        if path.resolve() in generated:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PUBLICATION_CLAIM_PATTERNS:
            for match in pattern.finditer(text):
                versions = re.findall(r"\d+\.\d+\.\d+", match.group(0))
                if versions and versions[0] in registered:
                    continue
                line = text[: match.start()].count("\n") + 1
                report.error(
                    f"{path.relative_to(root)}:{line}: unregistered publication "
                    f"claim {match.group(0).strip()!r}. This sentence asserts a "
                    "CURRENT PUBLISHED version, which is exactly the claim that "
                    "went stale on 2026-07-27. Either register it in "
                    "docs/published-version-claims.json with kind 'pypi-latest' "
                    "so it is compared to PyPI daily, or reword it to say what "
                    "the version actually is (a deployment pin, or the version "
                    "a retained measurement was taken on)."
                )


def parse_changelog(text: str) -> dict[str, list[str]]:
    """Map each ``## <repo>`` section to its release tags, newest first."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        heading = CHANGELOG_SECTION.match(raw)
        if heading:
            current = heading.group("name")
            sections.setdefault(current, [])
            continue
        entry = CHANGELOG_ENTRY.match(raw)
        if entry and current is not None:
            sections[current].append(entry.group("tag"))
    return sections


def newest_semver_tag(tags: list[str]) -> str | None:
    """Newest plain ``vX.Y.Z`` tag, ignoring installer-style prefixed tags.

    openadapt-desktop publishes both an engine ``vX.Y.Z`` release and a
    prerelease ``desktop-vX.Y.Z`` installer release. Only the former
    corresponds to a PyPI distribution.
    """
    for tag in tags:
        match = SEMVER_TAG.match(tag)
        if match:
            return match.group("version")
    return None


def check_changelog_structure(
    registry: dict, report: Report, changelog_path: Path = CHANGELOG_PATH
) -> dict[str, str]:
    """Return {package: version} claimed by the changelog, reporting gaps."""
    if not changelog_path.is_file():
        report.error(f"{changelog_path} does not exist")
        return {}
    sections = parse_changelog(changelog_path.read_text(encoding="utf-8"))
    claimed: dict[str, str] = {}
    for repo, package in registry.get("changelog_tracks_pypi", {}).items():
        if repo not in sections:
            report.error(
                f"docs/changelog.md has no '## {repo}' section, but the "
                "registry expects it to advertise that package's releases"
            )
            continue
        version = newest_semver_tag(sections[repo])
        if version is None:
            report.error(
                f"docs/changelog.md '## {repo}' section lists no vX.Y.Z release"
            )
            continue
        claimed[package] = version
    return claimed


# --------------------------------------------------------------------------
# Network checks
# --------------------------------------------------------------------------


def fetch_latest_version(package: str) -> str:
    request = urllib.request.Request(
        PYPI_URL_TEMPLATE.format(package=package),
        headers={"User-Agent": "openadapt-docs-version-claim-checker"},
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.load(response)["info"]["version"]


def compare_claim_to_pypi(
    label: str, package: str, claimed: str, published: str, report: Report
) -> None:
    """Compare one docs version claim against PyPI's newest release.

    Behind PyPI is stale documentation and fails. Ahead of PyPI means a GitHub
    release exists whose PyPI upload has not landed yet, which warns.
    """
    if claimed == published:
        return
    claimed_release = release_tuple(claimed)
    published_release = release_tuple(published)
    if (
        claimed_release is not None
        and published_release is not None
        and claimed_release > published_release
    ):
        report.warning(
            f"{label}: docs advertise {package} {claimed} but PyPI's newest is "
            f"{published}. A release is published on GitHub but not yet on "
            "PyPI, or the index has not propagated."
        )
        return
    report.error(
        f"{label}: docs advertise {package} {claimed} but the current "
        f"published release is {published}. The published documentation is "
        "advertising a superseded release."
    )


def check_against_pypi(
    registry: dict,
    changelog_claims: dict[str, str],
    report: Report,
    require_network: bool,
) -> None:
    wanted: dict[str, list[tuple[str, str]]] = {}
    for claim in registry.get("claims", []):
        if claim.get("kind") != "pypi-latest":
            continue
        wanted.setdefault(claim["package"], []).append(
            (f"claim {claim['id']!r}", claim["version"])
        )
    for package, version in changelog_claims.items():
        wanted.setdefault(package, []).append(("docs/changelog.md", version))

    for package, claims in sorted(wanted.items()):
        try:
            published = fetch_latest_version(package)
        except (urllib.error.URLError, TimeoutError, KeyError) as exc:
            emit = report.error if require_network else report.warning
            emit(f"could not fetch PyPI metadata for {package}: {exc}")
            continue
        for label, claimed in claims:
            compare_claim_to_pypi(label, package, claimed, published, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip the PyPI comparison (airgapped environments).",
    )
    parser.add_argument(
        "--require-network",
        action="store_true",
        help="Treat an unreachable PyPI as a failure instead of a warning.",
    )
    args = parser.parse_args()

    registry = load_registry()
    report = Report()

    check_claim_locations(registry, report)
    scan_for_unregistered_claims(registry, report)
    changelog_claims = check_changelog_structure(registry, report)

    if not args.offline:
        check_against_pypi(
            registry, changelog_claims, report, require_network=args.require_network
        )

    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if report.errors:
        print(
            f"\nFAILED: {len(report.errors)} error(s), "
            f"{len(report.warnings)} warning(s).",
            file=sys.stderr,
        )
        return 1
    scope = "offline checks only" if args.offline else "including PyPI comparison"
    print(
        f"OK: published version claims validated ({scope}); "
        f"{len(report.warnings)} warning(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
