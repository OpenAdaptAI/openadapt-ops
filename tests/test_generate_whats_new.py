"""Tests for generate_whats_new.py"""

import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import generate_whats_new
from generate_whats_new import generate, group_by_release, line_for, llm_sentences, load_repos

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_release_tags(request, mocker):
    """Unless a test drives gh itself, no repository has a release."""
    if not request.node.name.startswith(("test_failed_pr_fetch", "test_cli_merge_date")):
        mocker.patch("generate_whats_new.fetch_release_tags", return_value=[])


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


def test_llm_sentences_no_api_key(monkeypatch):
    """Without an API key the page uses PR titles."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm_sentences([{"url": "u", "title": "t"}]) == {}


def test_llm_sentences_no_anthropic_package(monkeypatch, mocker):
    """Without the anthropic package the page uses PR titles."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mocker.patch.dict("sys.modules", {"anthropic": None})

    # Force reimport to pick up the mocked module
    import importlib
    import generate_whats_new
    importlib.reload(generate_whats_new)

    assert generate_whats_new.llm_sentences([{"url": "u", "title": "t"}]) == {}
    importlib.reload(generate_whats_new)


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
    responses = {"pr": json.dumps(payload), "api": "[]"}
    mocker.patch(
        "generate_whats_new.subprocess.run",
        side_effect=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, responses[cmd[1]], ""),
    )
    generate(repos=[{"name": "flow", "github": "OpenAdaptAI/openadapt-flow"}], docs_dir=tmp_path)
    assert "merged 2026-09-09" in (tmp_path / "whats-new.md").read_text()


MONOREPO = {
    "name": "OpenAdapt",
    "github": "OpenAdaptAI/OpenAdapt",
    "releases": {
        "tag_prefix": "v",
        "paths": [
            {"path": "packages/flow/", "package": "openadapt-flow", "tag_prefix": "openadapt-flow-v"},
            {"path": "packages/types/", "package": "openadapt-types", "tag_prefix": "openadapt-types-v"},
        ],
    },
}


def _pr(number, sha, *paths, merged="2026-10-17T12:00:00Z"):
    return {
        "number": number,
        "title": f"change {number}",
        "url": f"https://github.com/OpenAdaptAI/OpenAdapt/pull/{number}",
        "mergedAt": merged,
        "mergeCommit": {"oid": sha} if sha else None,
        "files": [{"path": path} for path in paths],
    }


def test_line_for_picks_the_package_with_most_files():
    assert line_for(_pr(1, "a", "packages/flow/x.py", "packages/flow/y.py", "packages/types/z.py"), MONOREPO)["package"] == "openadapt-flow"
    assert line_for(_pr(2, "b", "README.md", ".github/ci.yml"), MONOREPO) == {"package": "OpenAdapt", "tag_prefix": "v"}
    assert line_for(_pr(3, "c", "src/x.py"), {"name": "solo", "github": "o/solo"}) == {"package": "solo", "tag_prefix": "v"}


def test_group_by_release_uses_the_oldest_containing_tag(mocker):
    tags = {
        "openadapt-flow-v": [("openadapt-flow-v2.3.0", (2, 3, 0)), ("openadapt-flow-v2.2.0", (2, 2, 0)), ("openadapt-flow-v2.1.0", (2, 1, 0))],
        "v": [("v1.17.0", (1, 17, 0))],
        "openadapt-types-v": [],
    }
    contains = {("openadapt-flow-v2.3.0", "old"), ("openadapt-flow-v2.2.0", "old"), ("openadapt-flow-v2.3.0", "new")}
    mocker.patch("generate_whats_new.fetch_release_tags", side_effect=lambda slug, prefix: tags[prefix])
    mocker.patch("generate_whats_new.tag_contains", side_effect=lambda slug, tag, sha: (tag, sha) in contains)

    grouped = group_by_release(MONOREPO, [
        _pr(10, "old", "packages/flow/a.py"),
        _pr(11, "new", "packages/flow/b.py"),
        _pr(12, "main-only", "packages/flow/c.py"),
        _pr(13, "root", "README.md"),
        _pr(14, None, "packages/flow/d.py"),
        _pr(15, "types", "packages/types/e.py"),
    ])

    assert [(r["label"], [p["number"] for p in r["prs"]]) for r in grouped["releases"]] == [
        ("openadapt-flow 2.3.0", [11]),
        ("openadapt-flow 2.2.0", [10]),
    ]
    assert [p["number"] for p in grouped["unreleased"]] == [12, 13, 14, 15]


def test_unreleased_prs_are_labeled_on_the_page(tmp_path, mocker, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    mocker.patch("generate_whats_new.fetch_merged_prs", return_value=[_pr(20, "x", "packages/flow/a.py"), _pr(21, "y", "packages/flow/b.py")])
    mocker.patch("generate_whats_new.fetch_release_tags", return_value=[("openadapt-flow-v2.2.0", (2, 2, 0))])
    mocker.patch("generate_whats_new.tag_contains", side_effect=lambda slug, tag, sha: sha == "x")

    generate(repos=[MONOREPO], docs_dir=tmp_path)
    page = (tmp_path / "whats-new.md").read_text()

    released, unreleased = page.split("### Merged, not released yet")
    assert "### Released in openadapt-flow 2.2.0" in released
    assert "pull/20" in released and "pull/21" not in released
    assert "pull/21" in unreleased and "openadapt-flow" in unreleased


def test_llm_rewrites_sentences_but_not_sections(tmp_path, mocker, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    prs = [_pr(30, "x", "packages/flow/a.py")]
    mocker.patch("generate_whats_new.fetch_merged_prs", return_value=prs)
    mocker.patch("generate_whats_new.llm_sentences", return_value={prs[0]["url"]: "Added a thing."})

    generate(repos=[MONOREPO], docs_dir=tmp_path)
    page = (tmp_path / "whats-new.md").read_text()

    assert "[Added a thing.](https://github.com/OpenAdaptAI/OpenAdapt/pull/30)" in page
    assert "### Merged, not released yet" in page and "### Released in" not in page


def test_failed_release_lookup_preserves_existing_digest(tmp_path, mocker, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    target = tmp_path / "whats-new.md"
    target.write_text("previous published digest\n")
    mocker.patch("generate_whats_new.fetch_merged_prs", return_value=[_pr(40, "x", "packages/flow/a.py")])
    mocker.patch("generate_whats_new.fetch_release_tags", side_effect=RuntimeError("GitHub request failed"))
    with pytest.raises(RuntimeError):
        generate(repos=[MONOREPO], docs_dir=tmp_path)
    assert target.read_text() == "previous published digest\n"
