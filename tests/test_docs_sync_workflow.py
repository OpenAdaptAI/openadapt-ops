"""Protect the publish boundary of the documentation sync workflow.

`main` is protected and accepts changes only through a pull request. The sync
workflow generates documentation source, so it must record that source on its
own branch and let a pull request carry it to `main`. A direct push to `main`
is rejected by the protection, and the rejection silently stops the deploy that
follows it.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")


def test_sync_never_pushes_generated_docs_to_main() -> None:
    assert "HEAD:main" not in WORKFLOW
    assert "git push origin main" not in WORKFLOW


def test_sync_records_generated_docs_on_its_own_branch() -> None:
    assert "BRANCH: docs/auto-sync" in WORKFLOW
    assert 'git push --force origin "HEAD:refs/heads/${BRANCH}"' in WORKFLOW


def test_sync_opens_and_auto_merges_a_pull_request() -> None:
    assert "gh pr create" in WORKFLOW
    assert "gh pr merge --squash --auto" in WORKFLOW
    assert "pull-requests: write" in WORKFLOW
    assert "contents: write" in WORKFLOW


def test_sync_checks_for_an_empty_diff_before_it_opens_a_pull_request() -> None:
    guard = WORKFLOW.index("git diff --staged --quiet")
    commit = WORKFLOW.index("git commit -m")
    create = WORKFLOW.index("gh pr create")
    assert guard < commit < create
    assert 'echo "changed=false" >> "$GITHUB_OUTPUT"' in WORKFLOW


def test_sync_ignores_a_diff_that_is_only_the_generation_clock() -> None:
    assert r"""git diff --staged --quiet -I'^> \*Last updated: '""" in WORKFLOW


def test_sync_publishes_recorded_source_then_fails_on_a_missing_pull_request() -> None:
    push = WORKFLOW.index('git push --force origin "HEAD:refs/heads/${BRANCH}"')
    deploy = WORKFLOW.index("actions/deploy-pages")
    gate = WORKFLOW.index("Confirm the generated source is queued for main")
    assert push < deploy < gate
    assert (
        "if: ${{ steps.docs_pr.outputs.changed == 'true'"
        " && steps.docs_pr.outputs.pr_url == '' }}"
    ) in WORKFLOW


def test_sync_pull_request_title_does_not_skip_the_merge_build() -> None:
    # The squash commit takes the pull request title. `[skip ci]` in that title
    # would stop the push-triggered build that deploys the merged source.
    title_line = next(
        line for line in WORKFLOW.splitlines() if line.strip().startswith("--title ")
    )
    assert "[skip ci]" not in title_line
