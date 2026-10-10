"""Protect the publish boundary of the documentation sync workflow.

`main` is protected and accepts changes only through a pull request. The sync
workflow generates documentation source, so it must record that source on its
own branch and let a pull request carry it to `main`. A direct push to `main`
is rejected by the protection, and the rejection silently stops the deploy that
follows it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")
STEPS = yaml.safe_load(WORKFLOW)["jobs"]["sync-and-deploy"]["steps"]


def step_running(command: str) -> dict:
    return next(step for step in STEPS if command in step.get("run", ""))


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
        " && steps.docs_pr.outputs.app_missing != 'true'"
        " && steps.docs_pr.outputs.pr_url == '' }}"
    ) in WORKFLOW


def test_sync_pull_request_title_does_not_skip_the_merge_build() -> None:
    # The squash commit takes the pull request title. `[skip ci]` in that title
    # would stop the push-triggered build that deploys the merged source.
    title_line = next(
        line for line in WORKFLOW.splitlines() if line.strip().startswith("--title ")
    )
    assert "[skip ci]" not in title_line


def test_the_pull_request_is_pushed_opened_and_merged_with_an_app_token() -> None:
    # An event raised with the workflow's own GITHUB_TOKEN starts no workflow
    # run: the auto-sync pull request opened on 2026-09-21 sat with its
    # required checks in action_required, so auto-merge never fired. An app
    # installation token raises ordinary events.
    app = next(
        step
        for step in STEPS
        if step.get("uses", "").startswith("actions/create-github-app-token@")
    )
    assert len(app["uses"].split("@", 1)[1].split()[0]) == 40
    assert app["with"]["client-id"] == "${{ vars.DOCS_SYNC_APP_CLIENT_ID }}"
    assert app["with"]["private-key"] == "${{ secrets.DOCS_SYNC_APP_PRIVATE_KEY }}"
    token = f"steps.{app['id']}.outputs.token"

    # Checkout persists the token that `git push` uses for the branch.
    checkout = next(
        step for step in STEPS if step.get("uses", "").startswith("actions/checkout@")
    )
    assert STEPS.index(app) < STEPS.index(checkout)
    assert token in checkout["with"]["token"]

    record = step_running("gh pr create")
    assert 'git push --force origin "HEAD:refs/heads/${BRANCH}"' in record["run"]
    assert record["env"]["GH_TOKEN"] == "${{ " + token + " }}"
    assert "secrets.GITHUB_TOKEN" not in record["env"]["GH_TOKEN"]


def test_a_stuck_auto_sync_pull_request_fails_the_run() -> None:
    record = step_running("gh pr create")
    assert "statusCheckRollup" in record["run"]
    assert "stuck=true" in record["run"]
    assert "app_missing=true" in record["run"]
    gate = next(
        step
        for step in STEPS
        if "steps.docs_pr.outputs.stuck" in step.get("if", "")
    )
    assert "steps.docs_pr.outputs.app_missing" in gate["if"]
    assert "exit 1" in gate["run"]
    deploy = next(step for step in STEPS if step.get("id") == "deploy")
    assert STEPS.index(record) < STEPS.index(deploy) < STEPS.index(gate)


def test_the_pull_request_body_does_not_ask_for_a_manual_reopen() -> None:
    assert "close and reopen this PR" not in WORKFLOW
