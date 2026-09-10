"""Tests for generate_whats_new.py"""

import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from generate_whats_new import generate, llm_summarize, load_repos

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_load_repos_omits_private_update_feeds(tmp_path):
    registry = tmp_path / "repos.yml"
    registry.write_text(
        "repos:\n"
        "  - name: public\n"
        "    github: OpenAdaptAI/public\n"
        "  - name: private\n"
        "    github: OpenAdaptAI/private\n"
        "    public_updates: false\n"
    )

    assert [repo["name"] for repo in load_repos(registry)] == ["public"]


def test_generate_without_llm(tmp_path, mocker, monkeypatch):
    """Without API key, should produce a raw PR list page."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    sample_prs = json.loads((FIXTURES / "sample_prs.json").read_text())
    mocker.patch("generate_whats_new.fetch_merged_prs", return_value=sample_prs)

    repos = [
        {"name": "openadapt-evals", "github": "OpenAdaptAI/openadapt-evals"},
    ]
    result = generate(repos=repos, docs_dir=tmp_path, days=7)

    content = (tmp_path / "whats-new.md").read_text()
    assert "What's New" in content
    assert "openadapt-evals" in content
    assert "evaluation pipeline" in content


def test_generate_with_no_prs(tmp_path, mocker, monkeypatch):
    """Should handle case where no PRs are found."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    mocker.patch("generate_whats_new.fetch_merged_prs", return_value=[])

    repos = [{"name": "empty-repo", "github": "OpenAdaptAI/empty-repo"}]
    generate(repos=repos, docs_dir=tmp_path, days=7)

    content = (tmp_path / "whats-new.md").read_text()
    assert "No merged PRs" in content or "What's New" in content


def test_llm_summarize_no_api_key(monkeypatch):
    """LLM summary should return None without API key."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = llm_summarize("some prs", 7)
    assert result is None


def test_llm_summarize_no_anthropic_package(monkeypatch, mocker):
    """LLM summary should return None if anthropic package not installed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mocker.patch.dict("sys.modules", {"anthropic": None})

    # Force reimport to pick up the mocked module
    import importlib
    import generate_whats_new
    importlib.reload(generate_whats_new)

    result = generate_whats_new.llm_summarize("some prs", 7)
    assert result is None


def test_generate_writes_artifact(tmp_path, mocker, monkeypatch):
    """Generate a sample What's New page without modifying tracked fixtures."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    sample_prs = json.loads((FIXTURES / "sample_prs.json").read_text())
    mocker.patch("generate_whats_new.fetch_merged_prs", return_value=sample_prs)

    repos = [
        {"name": "openadapt-evals", "github": "OpenAdaptAI/openadapt-evals"},
        {"name": "openadapt-ml", "github": "OpenAdaptAI/openadapt-ml"},
    ]
    artifact = pathlib.Path(generate(repos=repos, docs_dir=tmp_path, days=7))

    assert artifact == tmp_path / "whats-new.md"
    assert "openadapt-evals" in artifact.read_text()


@pytest.mark.parametrize("failure", [
    subprocess.TimeoutExpired("gh", 15),
    FileNotFoundError("gh"),
    subprocess.CompletedProcess(["gh"], 1, "", "private diagnostic"),
    subprocess.CompletedProcess(["gh"], 0, "invalid json", ""),
    subprocess.CompletedProcess(["gh"], 0, "{}", ""),
])
def test_failed_pr_fetch_preserves_existing_digest(tmp_path, monkeypatch, mocker, failure):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    target = tmp_path / "whats-new.md"
    target.write_text("previous published digest\n")
    if isinstance(failure, Exception):
        mocker.patch("generate_whats_new.subprocess.run", side_effect=failure)
    else:
        mocker.patch("generate_whats_new.subprocess.run", return_value=failure)
    with pytest.raises(RuntimeError) as exc:
        generate(repos=[{"name": "flow", "github": "OpenAdaptAI/openadapt-flow"}], docs_dir=tmp_path)
    assert "private diagnostic" not in str(exc.value)
    assert target.read_text() == "previous published digest\n"


def test_cli_merge_date_reaches_generated_digest(tmp_path, monkeypatch, mocker):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    payload = [{"number": 1, "title": "Release record", "url": "https://github.com/OpenAdaptAI/openadapt-flow/pull/1", "mergedAt": "2026-09-09T19:22:00Z"}]
    mocker.patch("generate_whats_new.subprocess.run", return_value=subprocess.CompletedProcess(["gh"], 0, json.dumps(payload), ""))
    generate(repos=[{"name": "flow", "github": "OpenAdaptAI/openadapt-flow"}], docs_dir=tmp_path)
    assert "merged 2026-09-09" in (tmp_path / "whats-new.md").read_text()
