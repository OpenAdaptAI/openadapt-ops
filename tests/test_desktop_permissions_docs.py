"""The Desktop install docs must ask for every macOS permission the app needs.

`MACOS_PERMISSIONS` mirrors the rows of the macOS permissions card in
openadapt-desktop `src/screens/Onboarding.tsx` at `desktop-v0.15.0`. Native
recording on macOS refuses to start without Input Monitoring
(`engine/dispatch.py`), so a reader who grants only the first two stalls with
a permission error the page never mentioned.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "docs/desktop/install.md"
TROUBLESHOOTING = ROOT / "docs/guides/troubleshooting.md"

MACOS_PERMISSIONS = ("Screen Recording", "Accessibility", "Input Monitoring")
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4}


def _flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def _macos_tab(text: str) -> str:
    start = text.index('=== "macOS"')
    end = text.index("=== ", start + 1)
    return text[start:end]


def test_install_page_asks_for_every_macos_permission() -> None:
    tab = _macos_tab(_flat(INSTALL))
    for permission in MACOS_PERMISSIONS:
        assert f"Privacy & Security → {permission}" in tab, permission


def test_install_page_counts_the_permissions_correctly() -> None:
    tab = _macos_tab(_flat(INSTALL))
    counts = re.findall(r"\b(one|two|three|four) permissions\b", tab)
    assert counts, "the macOS tab should say how many permissions it needs"
    assert {NUMBER_WORDS[word] for word in counts} == {len(MACOS_PERMISSIONS)}
    assert "both toggles" not in tab


def test_troubleshooting_names_every_macos_permission() -> None:
    tab = _macos_tab(_flat(TROUBLESHOOTING))
    for permission in MACOS_PERMISSIONS:
        assert f"Privacy & Security → {permission}" in tab, permission


def test_install_page_explains_the_input_monitoring_error() -> None:
    text = _flat(INSTALL)
    assert "Input Monitoring permission is required" in text


def test_install_page_calls_the_release_a_pre_release() -> None:
    # GitHub marks desktop-v0.15.0 as a pre-release. The page may not carry a
    # static maturity word such as "Beta" (scripts/validate_docs.py derives
    # product-target state at read time), so it states the release type.
    text = _flat(INSTALL)
    sentence = next(s for s in re.split(r"(?<=\.)\s", text) if "`desktop-v0.15.0`" in s)
    assert "pre-release" in sentence, sentence
    assert "complete" not in text.split("## 2.")[0]


def test_install_page_points_at_the_permissions_section() -> None:
    text = _flat(INSTALL)
    assert "step 3" not in text
