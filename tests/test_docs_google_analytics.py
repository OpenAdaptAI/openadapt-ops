"""Google Analytics on the docs honors Do-Not-Track and keeps Google signals off.

The OpenAdapt privacy policy says every browser analytics path honors
Do-Not-Track and that Google signals are disabled. On docs.openadapt.ai,
Material's Google Analytics integration ran for every visitor: it loaded
gtag.js and sent `config` (which sets the _ga cookies) even when the browser
sent Do-Not-Track, and it never turned Google signals off. PostHog on the same
page already checked Do-Not-Track.

This builds the site and runs the page's analytics scripts against a stub
browser in Node (tests/js/docs_google_analytics_harness.cjs).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests/js/docs_google_analytics_harness.cjs"
OVERRIDE = ROOT / "overrides/partials/integrations/analytics/google.html"
GTAG = "https://www.googletagmanager.com/gtag/js?id="


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("site")
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--quiet", "--site-dir", str(site)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return site / "index.html"


def _run(page: Path, signals: dict[str, str]) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required for the docs analytics contract")
    completed = subprocess.run(
        [node, str(HARNESS), str(page), json.dumps(signals)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    result = json.loads(completed.stdout)
    # The page must still carry the analytics scripts, or this proves nothing.
    assert result["scripts"] >= 2, result
    return result


@pytest.mark.parametrize(
    "signals",
    [
        {"navigator.doNotTrack": "1"},
        {"navigator.doNotTrack": "yes"},
        {"window.doNotTrack": "1"},
        {"navigator.msDoNotTrack": "1"},
    ],
)
def test_do_not_track_loads_no_google_analytics(page: Path, signals: dict[str, str]) -> None:
    result = _run(page, signals)
    assert result["inserted"] == []
    assert result["dataLayer"] == []


def test_without_do_not_track_google_signals_stay_off(page: Path) -> None:
    result = _run(page, {"navigator.doNotTrack": "0"})
    assert len(result["inserted"]) == 1 and result["inserted"][0].startswith(GTAG)
    configs = [entry for entry in result["dataLayer"] if entry[0] == "config"]
    # The page-load config and the one sent on instant navigation.
    assert len(configs) == 2, result
    for _, _property, *options in configs:
        assert options and options[0].get("allow_google_signals") is False, configs
        assert options[0].get("allow_ad_personalization_signals") is False, configs


def test_the_override_names_the_locked_material_version() -> None:
    # The override replaces a Material partial. When uv.lock moves to another
    # Material release, compare that release's google.html with the override,
    # then update the version named in the override's comment.
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = [pkg["version"] for pkg in lock["package"] if pkg["name"] == "mkdocs-material"]
    named = re.findall(r"analytics/google\.html\s+\(([0-9][0-9.]*)", OVERRIDE.read_text())
    assert named == locked


def test_one_signal_that_is_off_does_not_hide_another_that_is_on(page: Path) -> None:
    # A browser can expose more than one Do-Not-Track property. "0" or
    # "unspecified" on one of them must not mask "1" on another.
    for signals in (
        {"navigator.doNotTrack": "0", "window.doNotTrack": "1"},
        {"navigator.doNotTrack": "unspecified", "navigator.msDoNotTrack": "1"},
    ):
        result = _run(page, signals)
        assert result["inserted"] == [], signals
        assert result["dataLayer"] == [], signals


def test_search_sends_only_the_query_length(page: Path) -> None:
    # ANALYTICS.md promises that search records only `query_length`. Material's
    # own script sent the query text as `search_term`.
    result = _run(page, {})
    query = result["searchQuery"]
    searches = [entry for entry in result["dataLayer"] if entry[:2] == ["event", "search"]]
    assert searches == [["event", "search", {"query_length": len(query)}]], result
    assert query not in json.dumps(result["dataLayer"]), result
