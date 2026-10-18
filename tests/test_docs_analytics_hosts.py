"""Docs analytics loads only on docs.openadapt.ai, and never under automation.

In October 2026 about 80% of the "users" GA4 counted were bots or our own
automation: a crawl of docs.openadapt.ai from an emulated iPhone, QA on
deploy previews, and pages served from localhost and 127.0.0.1. GA4 and
PostHog on the docs now load only when the hostname is in mkdocs.yml
`extra.analytics_hosts` (an allowlist) and navigator.webdriver is not true.

This builds the site with a test PostHog key and runs the page's analytics
scripts against a stub browser (tests/js/docs_google_analytics_harness.cjs).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests/js/docs_google_analytics_harness.cjs"
GTAG = "https://www.googletagmanager.com/gtag/js?id="


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("site-hosts")
    env = {k: v for k, v in os.environ.items() if not k.startswith("NEXT_PUBLIC_POSTHOG_")}
    env["NEXT_PUBLIC_POSTHOG_KEY"] = "phc_test"
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--quiet", "--site-dir", str(site)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return site / "index.html"


def _run(page: Path, signals: dict) -> dict:
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
    # Material's definition, its call, and the PostHog block must all be on
    # the page, or an empty result proves nothing.
    assert result["scripts"] >= 3, result
    return result


def _loaded_nothing(result: dict) -> bool:
    return result["inserted"] == [] and result["dataLayer"] == [] and not result["posthogInit"]


def test_the_allowlist_is_the_production_docs_host() -> None:
    class Loader(yaml.SafeLoader):
        pass

    # mkdocs.yml uses !ENV and !!python/name tags; read past them.
    Loader.add_multi_constructor("", lambda loader, suffix, node: None)
    config = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=Loader)
    assert config["extra"]["analytics_hosts"] == ["docs.openadapt.ai"]


@pytest.mark.parametrize("hostname", ["docs.openadapt.ai", "DOCS.OpenAdapt.ai", "docs.openadapt.ai."])
def test_production_loads_google_analytics_and_posthog(page: Path, hostname: str) -> None:
    result = _run(page, {"location.hostname": hostname})
    assert any(src.startswith(GTAG) for src in result["inserted"]), result
    assert any("posthog" in src for src in result["inserted"]), result
    assert result["posthogInit"], result
    assert any(entry[0] == "config" for entry in result["dataLayer"]), result


@pytest.mark.parametrize(
    "hostname",
    [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "openadaptai.github.io",
        "deploy-preview-12--openadapt-docs.netlify.app",
        "openadapt.ai",
        "blog.openadapt.ai",
        "docs.openadapt.ai.evil.example",
        "",
    ],
)
def test_other_hosts_load_nothing(page: Path, hostname: str) -> None:
    assert _loaded_nothing(_run(page, {"location.hostname": hostname}))


def test_automation_loads_nothing_even_on_production(page: Path) -> None:
    assert _loaded_nothing(_run(page, {"navigator.webdriver": True}))
    # webdriver false is an ordinary browser.
    result = _run(page, {"navigator.webdriver": False})
    assert any(src.startswith(GTAG) for src in result["inserted"]), result


def test_both_trackers_share_one_gate() -> None:
    include = '{% include "partials/integrations/analytics/openadapt-gate.html" %}'
    google = (ROOT / "overrides/partials/integrations/analytics/google.html").read_text()
    main = (ROOT / "overrides/main.html").read_text()
    assert include in google
    assert include in main
    # The gate runs before Do-Not-Track and before anything loads.
    assert google.index(include) < google.index("doNotTrack")
    assert main.index(include) < main.index("posthog.init(")
