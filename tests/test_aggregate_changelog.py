"""Tests for aggregate_changelog.py"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from aggregate_changelog import aggregate, fetch_releases, load_repos, summarize_body


def test_aggregate_writes_changelog(tmp_path, mocker):
    """Aggregate should write a changelog.md file."""
    mock_releases = [
        {"tag_name": "v0.3.0", "published_at": "2026-02-15T00:00:00Z",
         "html_url": "https://github.com/OpenAdaptAI/test/releases/v0.3.0",
         "body": "Added new CLI command", "draft": False},
        {"tag_name": "v0.2.0", "published_at": "2026-01-10T00:00:00Z",
         "html_url": "https://github.com/OpenAdaptAI/test/releases/v0.2.0",
         "body": "Fixed import error", "draft": False},
    ]
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_releases
    mocker.patch("aggregate_changelog.requests.get", return_value=mock_resp)

    repos = [
        {"name": "test-pkg", "github": "OpenAdaptAI/test-pkg", "changelog": True},
    ]
    result = aggregate(repos=repos, docs_dir=tmp_path)
    content = (tmp_path / "changelog.md").read_text()

    assert "test-pkg" in content
    assert "v0.3.0" in content
    assert "v0.2.0" in content
    assert "Added new CLI" in content


def test_aggregate_skips_drafts(tmp_path, mocker):
    """Draft releases should be skipped."""
    mock_releases = [
        {"tag_name": "v0.4.0-rc", "published_at": "2026-03-01T00:00:00Z",
         "html_url": "https://example.com", "body": "Draft", "draft": True},
        {"tag_name": "v0.3.0", "published_at": "2026-02-15T00:00:00Z",
         "html_url": "https://example.com", "body": "Released", "draft": False},
    ]
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_releases
    mocker.patch("aggregate_changelog.requests.get", return_value=mock_resp)

    repos = [{"name": "pkg", "github": "OpenAdaptAI/pkg", "changelog": True}]
    aggregate(repos=repos, docs_dir=tmp_path)
    content = (tmp_path / "changelog.md").read_text()

    assert "v0.3.0" in content
    assert "v0.4.0-rc" not in content


def test_aggregate_handles_no_releases(tmp_path, mocker):
    """Should still write a file even if repos have no releases."""
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    mocker.patch("aggregate_changelog.requests.get", return_value=mock_resp)

    repos = [{"name": "empty", "github": "OpenAdaptAI/empty", "changelog": True}]
    aggregate(repos=repos, docs_dir=tmp_path)
    assert (tmp_path / "changelog.md").exists()


def test_summarize_body_skips_redundant_version_heading():
    """A leading heading that only restates the version is dropped, and the
    first real note is returned as heading-free inline text."""
    body = "## v1.7.1 (2026-07-19)\n\nFixed halt-on-drift regression"
    assert summarize_body(body, "v1.7.1") == "Fixed halt-on-drift regression"


def test_summarize_body_version_only_returns_empty():
    """When the body is nothing but the version header, there is no note to
    render, so aggregate should append nothing rather than echo the heading."""
    assert summarize_body("## v1.7.1 (2026-07-19)", "v1.7.1") == ""


def test_summarize_body_strips_leading_hash_from_first_note():
    """A real leading heading (not a version restatement) is rendered inline so
    it does not disrupt the changelog page's heading hierarchy."""
    assert summarize_body("# Highlights\nStuff", "v2.0.0") == "Highlights"


def test_aggregate_drops_duplicate_version_heading(tmp_path, mocker):
    """End-to-end: the changelog must not contain an echoed `## vX` heading
    line, which previously duplicated the tag and broke heading hierarchy."""
    mock_releases = [
        {"tag_name": "v1.7.1", "published_at": "2026-07-19T00:00:00Z",
         "html_url": "https://github.com/OpenAdaptAI/test/releases/v1.7.1",
         "body": "## v1.7.1 (2026-07-19)\n\nHalt-on-drift fix", "draft": False},
    ]
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_releases
    mocker.patch("aggregate_changelog.requests.get", return_value=mock_resp)

    repos = [{"name": "test-pkg", "github": "OpenAdaptAI/test-pkg", "changelog": True}]
    aggregate(repos=repos, docs_dir=tmp_path)
    content = (tmp_path / "changelog.md").read_text()

    assert "## v1.7.1 (2026-07-19)" not in content
    assert "Halt-on-drift fix" in content


def test_fetch_releases_refuses_to_replace_changelog_on_http_error(mocker):
    mock_resp = mocker.Mock()
    mock_resp.status_code = 500
    mocker.patch("aggregate_changelog.requests.get", return_value=mock_resp)
    with pytest.raises(RuntimeError, match="Refusing to replace the changelog"):
        fetch_releases("OpenAdaptAI/broken")


def test_fetch_releases_authenticates_when_github_token_is_available(
    monkeypatch, mocker
):
    monkeypatch.setenv("GH_TOKEN", "test-token")
    mock_resp = mocker.Mock(status_code=200)
    mock_resp.json.return_value = []
    get = mocker.patch("aggregate_changelog.requests.get", return_value=mock_resp)

    fetch_releases("OpenAdaptAI/example")

    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"


def test_private_repo_is_not_loaded_into_public_changelog(tmp_path):
    registry = tmp_path / "repos.yml"
    registry.write_text(
        "repos:\n"
        "  - name: public\n"
        "    github: OpenAdaptAI/public\n"
        "    changelog: true\n"
        "  - name: private\n"
        "    github: OpenAdaptAI/private\n"
        "    changelog: false\n"
    )

    assert [repo["name"] for repo in load_repos(registry)] == ["public"]


def test_summarize_body_skips_licence_boilerplate():
    """Every python-semantic-release body opens with the same licence line.

    openadapt-flow v1.24.0 reached the published changelog carrying only that
    sentence, so the page recorded a release with no visible content while its
    actual "Bug Fixes" notes were dropped.
    """
    body = (
        "## v1.24.0 (2026-07-27)\n\n"
        "_This release is published under the MIT License._\n\n"
        "### Bug Fixes\n\n"
        "- Harden rich action admission\n"
    )
    assert summarize_body(body, "v1.24.0") == "Bug Fixes"


def test_summarize_body_boilerplate_only_returns_empty():
    """A release whose body is only version header plus licence has no notes."""
    body = "## v1.7.1 (2026-07-19)\n\n_This release is published under the MIT License._"
    assert summarize_body(body, "v1.7.1") == ""


def test_summarize_body_keeps_informative_emphasised_line():
    """Only the licence sentence is boilerplate, not emphasis in general."""
    body = "## v2.0.0 (2026-07-27)\n\n_Breaking: the compile API moved._"
    assert summarize_body(body, "v2.0.0") == "_Breaking: the compile API moved._"
