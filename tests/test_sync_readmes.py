"""Tests for sync_readmes.py"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from sync_readmes import sync, load_repos, fetch_readme

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_load_repos():
    repos = load_repos()
    assert len(repos) > 0
    assert all("name" in r and "github" in r and "lifecycle" in r for r in repos)
    assert {r["lifecycle"] for r in repos} <= {
        "beta", "experimental", "research", "deprecated",
    }
    lifecycle_by_name = {r["name"]: r["lifecycle"] for r in repos}
    assert lifecycle_by_name["openadapt-agent"] == "beta"


def test_sync_renders_pages(tmp_path, mocker):
    """Sync should render a page for each repo using the template."""
    sample_readme = (FIXTURES / "sample_readme.md").read_text()
    mocker.patch("sync_readmes.fetch_readme", return_value=sample_readme)

    repos = [
        {"name": "test-pkg", "github": "OpenAdaptAI/test-pkg",
         "doc_page": "packages/test-pkg.md", "category": "core"},
    ]
    results = sync(repos=repos, docs_dir=tmp_path, templates_dir=ROOT / "templates")

    assert len(results) == 1
    out_file = tmp_path / "packages" / "test-pkg.md"
    assert out_file.exists()
    content = out_file.read_text()
    assert "test-pkg" in content
    assert "openadapt-example" in content  # from sample README
    assert "Auto-generated" in content


def test_sync_creates_directories(tmp_path, mocker):
    """Sync should create the packages/ directory if it doesn't exist."""
    mocker.patch("sync_readmes.fetch_readme", return_value="# Test")
    repos = [
        {"name": "deep-pkg", "github": "OpenAdaptAI/deep-pkg",
         "doc_page": "nested/deep/deep-pkg.md", "category": "core"},
    ]
    sync(repos=repos, docs_dir=tmp_path, templates_dir=ROOT / "templates")
    assert (tmp_path / "nested" / "deep" / "deep-pkg.md").exists()


def test_fetch_readme_handles_failure(mocker):
    """fetch_readme should return a fallback message on HTTP error."""
    mock_resp = mocker.Mock()
    mock_resp.status_code = 404
    mocker.patch("sync_readmes.requests.get", return_value=mock_resp)
    result = fetch_readme("OpenAdaptAI/nonexistent")
    assert "not available" in result


def test_sync_skips_repos_without_doc_page(tmp_path, mocker):
    """Repos without a doc_page feed changelog/what's-new but are not mirrored
    as published pages, so sync renders nothing for them."""
    mocker.patch("sync_readmes.fetch_readme", return_value="# Test")
    repos = [
        {"name": "no-page", "github": "OpenAdaptAI/no-page", "category": "core"},
    ]
    results = sync(repos=repos, docs_dir=tmp_path, templates_dir=ROOT / "templates")
    assert results == []
    assert not (tmp_path / "packages").exists()


def test_sync_configured_repos_are_page_free(tmp_path, mocker):
    """The configured repos.yml intentionally sets no doc_page: the docs site
    presents a single curated Ecosystem page instead of README mirrors."""
    mocker.patch("sync_readmes.fetch_readme", return_value="# Test")
    repos = load_repos()
    results = sync(repos=repos, docs_dir=tmp_path, templates_dir=ROOT / "templates")
    assert results == []
