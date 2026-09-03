"""Protect the publish boundary of the documentation sync workflow."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")
PREPARE_JOB = WORKFLOW.split("  prepare-sync:\n", 1)[1].split(
    "  deploy-main:\n", 1
)[0]
DEPLOY_JOB = WORKFLOW.split("  deploy-main:\n", 1)[1]


def test_sync_never_pushes_generated_docs_to_main() -> None:
    assert "HEAD:main" not in WORKFLOW
    assert "git push origin main" not in WORKFLOW


def test_sync_records_generated_docs_on_its_own_branch() -> None:
    assert "BRANCH: docs/auto-sync" in PREPARE_JOB
    assert 'git push --force origin "HEAD:refs/heads/${BRANCH}"' in PREPARE_JOB


def test_sync_opens_and_auto_merges_a_pull_request() -> None:
    assert "gh pr create" in PREPARE_JOB
    assert "gh pr merge --squash --auto" in PREPARE_JOB
    assert "pull-requests: write" in PREPARE_JOB
    assert "contents: write" in PREPARE_JOB


def test_sync_checks_for_an_empty_diff_before_it_opens_a_pull_request() -> None:
    guard = PREPARE_JOB.index("git diff --staged --quiet")
    commit = PREPARE_JOB.index("git commit -m")
    create = PREPARE_JOB.index("gh pr create")
    assert guard < commit < create
    assert 'echo "changed=false" >> "$GITHUB_OUTPUT"' in WORKFLOW


def test_sync_ignores_a_diff_that_is_only_the_generation_clock() -> None:
    assert r"""git diff --staged --quiet -I'^> \*Last updated: '""" in WORKFLOW


def test_non_push_triggers_prepare_a_pr_but_never_deploy() -> None:
    assert "if: github.event_name != 'push'" in WORKFLOW
    assert "Sync READMEs" in PREPARE_JOB
    assert "actions/deploy-pages" not in PREPARE_JOB
    assert "actions/upload-pages-artifact" not in PREPARE_JOB


def test_only_a_merged_main_push_can_deploy() -> None:
    assert (
        "if: github.event_name == 'push' && github.ref == 'refs/heads/main'"
        in WORKFLOW
    )
    assert "actions/deploy-pages" in DEPLOY_JOB
    assert "ref: ${{ github.sha }}" in DEPLOY_JOB
    assert "Sync READMEs" not in DEPLOY_JOB


def test_missing_generated_source_pr_fails_before_any_publication() -> None:
    gate = PREPARE_JOB.index('if [ -z "${PR_URL}" ]; then')
    error = PREPARE_JOB.index("::error::${BRANCH} holds generated source")
    assert gate < error
    assert "exit 1" in PREPARE_JOB[error:]


def test_sync_pull_request_title_does_not_skip_the_merge_build() -> None:
    # The squash commit takes the pull request title. `[skip ci]` in that title
    # would stop the push-triggered build that deploys the merged source.
    title_line = next(
        line for line in WORKFLOW.splitlines() if line.strip().startswith("--title ")
    )
    assert "[skip ci]" not in title_line
