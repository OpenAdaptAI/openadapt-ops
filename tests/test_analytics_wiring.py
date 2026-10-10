"""PostHog reaches the published docs only through the deploy build.

mkdocs.yml reads NEXT_PUBLIC_POSTHOG_KEY when `mkdocs build` runs, and
overrides/main.html emits PostHog only when that key is set. The deploy
workflow built the site with no such variable, so docs.openadapt.ai never
loaded PostHog even though ANALYTICS.md describes it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _steps(workflow: str, job: str) -> list[dict]:
    source = (ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8")
    return yaml.safe_load(source)["jobs"][job]["steps"]


def _build(tmp_path: Path, key: str | None) -> str:
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("NEXT_PUBLIC_POSTHOG_")
    }
    if key is not None:
        env["NEXT_PUBLIC_POSTHOG_KEY"] = key
    out = tmp_path / ("with-key" if key else "without-key")
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--quiet", "--site-dir", str(out)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return (out / "index.html").read_text(encoding="utf-8")


def test_the_deploy_build_receives_the_posthog_settings() -> None:
    build = next(
        step
        for step in _steps("sync.yml", "sync-and-deploy")
        if step.get("name") == "Build MkDocs site"
    )
    env = build.get("env", {})
    assert env.get("NEXT_PUBLIC_POSTHOG_KEY") == "${{ vars.NEXT_PUBLIC_POSTHOG_KEY }}"
    assert "vars.NEXT_PUBLIC_POSTHOG_HOST" in env.get("NEXT_PUBLIC_POSTHOG_HOST", "")
    # A configured key that does not reach the HTML fails the deploy.
    assert "posthog.init" in build["run"]


def test_pull_request_builds_stay_free_of_analytics() -> None:
    for step in _steps("ci.yml", "validate"):
        assert "NEXT_PUBLIC_POSTHOG" not in str(step.get("env", {})), step.get("name")


def test_a_build_with_the_key_emits_posthog_and_one_without_does_not(
    tmp_path: Path,
) -> None:
    assert "posthog.init('phc_test'" in _build(tmp_path, "phc_test")
    assert "posthog.init" not in _build(tmp_path, None)
