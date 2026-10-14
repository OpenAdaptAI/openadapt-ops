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
4. The compatibility table in ``docs/reference/compatibility.md`` names every
   tracked package and the supported Python range.

Network checks (run daily; PyPI is the authority):

5. Every ``pypi-latest`` claim's version equals PyPI's newest release.
6. The newest ``vX.Y.Z`` entry in each tracked section of ``docs/changelog.md``
   equals PyPI's newest release for that package. The changelog is the docs'
   always-live statement of "what the current release is", so it is guarded
   structurally rather than by phrase.
7. Every range in the compatibility table equals what the newest ``openadapt``
   and ``openadapt-flow`` releases require (``requires_dist`` and
   ``requires_python``). The table once said Flow >=1.7 and types 0.9 while
   the releases required Flow >=1.29 and types 0.17.

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
COMPATIBILITY_PATH = DOCS_DIR / "reference" / "compatibility.md"
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

# Which released metadata each package range in the compatibility table must
# equal: (package whose requires_dist states it, extras that must all state
# the same range; None is the base install). The launcher decides the Flow and
# Capture ranges a user gets; Flow decides the types and privacy ranges.
COMPATIBILITY_SOURCES: dict[str, tuple[str, tuple[str | None, ...]]] = {
    "openadapt-flow": ("openadapt", (None,)),
    "openadapt-capture": ("openadapt", ("capture",)),
    "openadapt-privacy": ("openadapt-flow", ("privacy",)),
    "openadapt-types": (
        "openadapt-flow",
        (None, "console", "execute", "interop", "reward"),
    ),
}
# The supported Python range is the engine's.
COMPATIBILITY_PYTHON_SOURCE = "openadapt-flow"
COMPATIBILITY_HEADING = "## Current compatibility contract"
TABLE_RANGE = re.compile(
    r"`(?P<name>[a-z][a-z0-9-]*)(?:\[[^\]]*\])?\s+(?P<spec>[<>=!~][^`]*)`"
)
REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9._-]+)\s*(?:\[[^\]]*\])?\s*(?P<spec>[^;]*?)\s*"
    r"(?:;\s*(?P<marker>.+))?$"
)
SPEC_CLAUSE = re.compile(r"(?P<op>>=|<=|==|!=|~=|>|<)\s*(?P<version>\d+(?:\.\d+)*)")


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


def parse_compatibility_table(text: str) -> list[tuple[str, str]]:
    """Return (component, compatible range) for each row of the contract table."""
    if COMPATIBILITY_HEADING not in text:
        return []
    section = text.split(COMPATIBILITY_HEADING, 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.lstrip().startswith("|") or len(cells) < 2:
            continue
        if cells[0] == "Component" or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append((cells[0], cells[1]))
    return rows


def check_compatibility_structure(text: str, report: Report) -> None:
    """The contract table exists and names every tracked range."""
    rows = parse_compatibility_table(text)
    if not rows:
        report.error(
            f"docs/reference/compatibility.md has no {COMPATIBILITY_HEADING!r} "
            "table, so its ranges cannot be compared with the released metadata"
        )
        return
    named = {match.group("name") for _, cell in rows for match in TABLE_RANGE.finditer(cell)}
    for package in sorted(set(COMPATIBILITY_SOURCES) - named):
        report.error(
            f"docs/reference/compatibility.md: the compatibility table has no "
            f"`{package}` range, but readers need the range the released "
            "packages require"
        )
    if not any(component == "Python" for component, _ in rows):
        report.error("docs/reference/compatibility.md: the compatibility table has no Python row")


def _spec_meaning(spec: str) -> frozenset[tuple[str, tuple[int, ...]]]:
    """A specifier as a set of (operator, release) with trailing zeros dropped."""
    clauses = set()
    for match in SPEC_CLAUSE.finditer(spec):
        release = [int(part) for part in match.group("version").split(".")]
        while len(release) > 1 and release[-1] == 0:
            release.pop()
        clauses.add((match.group("op"), tuple(release)))
    return frozenset(clauses)


def _released_ranges(requires_dist: list[str], package: str) -> dict[str | None, str]:
    """Map each extra (None for the base install) to its range for ``package``."""
    ranges: dict[str | None, str] = {}
    for line in requires_dist:
        match = REQUIREMENT.match(line.strip())
        if not match or match.group("name").lower() != package:
            continue
        extra = re.search(r"extra\s*==\s*[\"']([^\"']+)[\"']", match.group("marker") or "")
        ranges[extra.group(1) if extra else None] = match.group("spec")
    return ranges


def _python_range(requires_python: str) -> str:
    """``>=3.10,<3.13`` as the table writes it: ``3.10-3.12``."""
    lower = upper = None
    for match in SPEC_CLAUSE.finditer(requires_python):
        release = tuple(int(part) for part in match.group("version").split("."))
        if match.group("op") == ">=":
            lower = release
        elif match.group("op") == "<" and len(release) >= 2:
            upper = (release[0], release[1] - 1)
    if lower is None:
        return requires_python
    start = ".".join(str(part) for part in lower[:2])
    if upper is None:
        return f"{start} and newer"
    return f"{start}-{upper[0]}.{upper[1]}"


def check_compatibility_table(text: str, metadata: dict, report: Report) -> None:
    """Every documented range equals what the newest releases require.

    ``metadata`` maps a package name to its PyPI ``info`` fields
    (``requires_dist`` and ``requires_python``).
    """
    def label(source: str, extra: str | None) -> str:
        return f"{source}[{extra}]" if extra else source

    expected: dict[str, str] = {}
    for package, (source, extras) in COMPATIBILITY_SOURCES.items():
        ranges = _released_ranges(metadata[source].get("requires_dist") or [], package)
        missing = [label(source, extra) for extra in extras if extra not in ranges]
        if missing:
            report.error(
                f"compatibility table: {', '.join(missing)} no longer requires "
                f"{package}; update the table row that says it does"
            )
            continue
        meanings = {_spec_meaning(ranges[extra]) for extra in extras}
        if len(meanings) > 1:
            stated = ", ".join(f"{label(source, extra)} {ranges[extra]}" for extra in extras)
            report.error(
                f"compatibility table: {source} now pins different {package} "
                f"ranges ({stated}), so one table row can't state them"
            )
            continue
        expected[package] = ranges[extras[0]]

    for component, cell in parse_compatibility_table(text):
        if component == "Python":
            want = _python_range(metadata[COMPATIBILITY_PYTHON_SOURCE].get("requires_python") or "")
            if cell != want:
                report.error(
                    f"compatibility table: Python says {cell!r}, but "
                    f"{COMPATIBILITY_PYTHON_SOURCE} requires Python {want}"
                )
            continue
        for match in TABLE_RANGE.finditer(cell):
            package, spec = match.group("name"), match.group("spec").strip()
            if package not in expected:
                continue
            if _spec_meaning(spec) != _spec_meaning(expected[package]):
                source = COMPATIBILITY_SOURCES[package][0]
                report.error(
                    f"compatibility table row {component!r}: `{package} {spec}` "
                    f"differs from the newest {source} release, which requires "
                    f"{package}{expected[package]}"
                )


# --------------------------------------------------------------------------
# Network checks
# --------------------------------------------------------------------------


def fetch_package_info(package: str) -> dict:
    request = urllib.request.Request(
        PYPI_URL_TEMPLATE.format(package=package),
        headers={"User-Agent": "openadapt-docs-version-claim-checker"},
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.load(response)["info"]


def fetch_latest_version(package: str) -> str:
    return fetch_package_info(package)["version"]


def check_compatibility_against_pypi(
    report: Report, require_network: bool, path: Path = COMPATIBILITY_PATH
) -> None:
    sources = sorted({source for source, _ in COMPATIBILITY_SOURCES.values()})
    metadata = {}
    for package in sources:
        try:
            metadata[package] = fetch_package_info(package)
        except (urllib.error.URLError, TimeoutError, KeyError) as exc:
            emit = report.error if require_network else report.warning
            emit(f"could not fetch PyPI metadata for {package}: {exc}")
            return
    check_compatibility_table(path.read_text(encoding="utf-8"), metadata, report)


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
    check_compatibility_structure(COMPATIBILITY_PATH.read_text(encoding="utf-8"), report)

    if not args.offline:
        check_against_pypi(
            registry, changelog_claims, report, require_network=args.require_network
        )
        check_compatibility_against_pypi(report, require_network=args.require_network)

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
