"""Version pins on the docs are dated, consistent, and not called current.

The deployment matrix, hosted guide, security review, and qualification page
said "the current managed-runtime manifest pins Flow 1.31.0", with that
release's commit and hashes, weeks after Cloud's runner/runtime-version.json
moved to Flow 1.34.0. The OEM guide called `openadapt-types` 0.9.0 the released
contract while Flow required 0.17. A reviewer who checked the hashes against
Cloud found a mismatch.

A pin statement now carries the date it was checked ("As of YYYY-MM-DD"), so
it stays true when Cloud moves on. The registered pin in
docs/published-version-claims.json holds the version, commit, and hashes the
docs state, and the date they were checked against the Cloud manifest. A named
`openadapt-types` release must fall in the range the compatibility table
gives, which a daily check keeps equal to Flow's metadata.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REGISTRY = DOCS / "published-version-claims.json"
COMPATIBILITY = DOCS / "reference/compatibility.md"
DEPLOYMENT_MATRIX = DOCS / "security/evidence.md"
GENERATED_PAGES = {DOCS / "changelog.md", DOCS / "whats-new.md"}

_PIN = re.compile(r"manifest pins (?:the )?Flow (\d+\.\d+\.\d+)")
_DATED = re.compile(r"\bAs of (\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
_TYPES_RELEASE = re.compile(r"`?openadapt-types`?\s+v?(\d+\.\d+\.\d+)\b")


def _pages() -> list[Path]:
    return sorted(
        path
        for path in DOCS.rglob("*")
        if path.suffix in {".md", ".txt"} and path.is_file() and path not in GENERATED_PAGES
    )


def _sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        joined = " ".join(line.strip() for line in paragraph.splitlines())
        for cell in joined.split("|"):
            sentences.extend(s for s in re.split(r"(?<=[.;!?])\s+", cell) if s)
    return sentences


def _pin() -> dict:
    claims = json.loads(REGISTRY.read_text(encoding="utf-8"))["claims"]
    return next(claim for claim in claims if claim["id"] == "hosted-runner-managed-runtime-pin")


def _pin_sentences() -> list[tuple[Path, str]]:
    return [
        (page, sentence)
        for page in _pages()
        for sentence in _sentences(page.read_text(encoding="utf-8"))
        if _PIN.search(sentence)
    ]


def test_every_runtime_pin_sentence_is_dated_and_matches_the_registry() -> None:
    pin = _pin()
    found = _pin_sentences()
    assert len(found) >= 1, found
    problems = []
    for page, sentence in found:
        where = f"{page.relative_to(ROOT)}: {sentence}"
        if _PIN.search(sentence).group(1) != pin["version"]:
            problems.append(f"pins a different Flow than the registry ({pin['version']}): {where}")
        dated = _DATED.search(sentence)
        if not dated or dated.group(1) != pin["verified_on"]:
            problems.append(f"not dated 'As of {pin['verified_on']}': {where}")
        if re.search(r"\bcurrent\b", sentence, re.IGNORECASE):
            problems.append(f"calls a dated pin current: {where}")
    assert problems == [], "\n".join(problems)


def test_the_evidence_page_states_the_registered_artifact_identity() -> None:
    pin = _pin()
    artifact = pin["artifact"]
    text = DEPLOYMENT_MATRIX.read_text(encoding="utf-8")
    for value in (artifact["release_commit"], artifact["wheel_sha256"], artifact["sdist_sha256"]):
        assert re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value), value
        assert f"`{value}`" in text, value
    # The registry evidence names the same values it was checked against.
    for value in artifact.values():
        assert value in pin["evidence"], value


def test_the_hashes_live_only_on_the_evidence_page() -> None:
    artifact = _pin()["artifact"]
    for page in _pages():
        if page == DEPLOYMENT_MATRIX:
            continue
        text = page.read_text(encoding="utf-8")
        for value in artifact.values():
            assert value not in text, f"{page.relative_to(ROOT)} repeats {value}"


def _types_range() -> tuple[tuple[int, ...], tuple[int, ...]]:
    text = COMPATIBILITY.read_text(encoding="utf-8")
    match = re.search(r"`openadapt-types >=(\d+(?:\.\d+)*),<(\d+(?:\.\d+)*)`", text)
    assert match, "the compatibility table names no openadapt-types range"
    return tuple(map(int, match.group(1).split("."))), tuple(map(int, match.group(2).split(".")))


def test_named_openadapt_types_releases_fall_in_the_documented_range() -> None:
    low, high = _types_range()
    problems = []
    for page in _pages():
        for sentence in _sentences(page.read_text(encoding="utf-8")):
            for version in _TYPES_RELEASE.findall(sentence):
                release = tuple(map(int, version.split(".")))
                if not low <= release < high:
                    problems.append(f"{page.relative_to(ROOT)}: {sentence}")
    assert problems == [], "\n".join(problems)
