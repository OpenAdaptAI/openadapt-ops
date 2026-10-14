"""The cross-repository sweep must fire on a real red branch and stay quiet otherwise.

Proving a detector passes today is worthless on its own. These tests prove it
FAILS on the exact conditions it exists to catch -- including the real incident
that motivated it -- and that it stays quiet on the conditions that would make it
noise, because a daily issue that cries wolf gets muted, and a muted alert is
worse than none.

The 2026-07-28 incident, reproduced below as
``test_reports_a_failure_that_happened_after_the_retirement``:
``openadapt-grounding``, ``openadapt-retrieval`` and ``openadapt-viewer`` failed
``Release and PyPI Publish`` on ``main`` from 2026-02-18, kept failing for five
months, failed again on a push at 00:04Z, and were switched to
``workflow_dispatch``-only at 02:22Z. Trusting the current trigger alone would
call all three permanently stale and would also miss the next dispatched failure.
"""

import base64
import pathlib
import sys
from datetime import datetime, timedelta, timezone

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sweep_default_branch_ci import (  # noqa: E402
    FAILING,
    GREEN,
    IN_FLIGHT,
    NOT_A_FAILURE,
    NOT_PUSH_GATED,
    RETIRED,
    STALE_GREEN,
    classify_run,
    is_github_managed,
    is_push_gated,
    is_scheduled,
    render,
    schedule_expiry_warning,
    should_alert,
    sweep_repository,
    token_sees_private,
)

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
HEAD = "a" * 40
OLD = "b" * 40

PUSH_GATED = "name: CI\non:\n  push:\n    branches: [main]\n  pull_request:\njobs: {}\n"
DISPATCH_ONLY = "name: Release\non:\n  workflow_dispatch:\njobs: {}\n"
SCHEDULE_ONLY = "name: Nightly\non:\n  schedule:\n    - cron: '0 3 * * *'\njobs: {}\n"

ACTIVE = {"id": 1, "state": "active", "path": ".github/workflows/ci.yml"}


def run(**kwargs):
    base = {
        "name": "CI",
        "status": "completed",
        "conclusion": "success",
        "head_sha": HEAD,
        "created_at": "2026-07-28T10:00:00Z",
        "path": ".github/workflows/ci.yml",
    }
    base.update(kwargs)
    return base


def classify(r, workflow=ACTIVE, source=PUSH_GATED, changed_at=None, head=HEAD, grace=6.0):
    return classify_run(r, workflow, source, changed_at, head, NOW, grace)[0]


# --------------------------------------------------------------------------
# It must fire on what is not green
# --------------------------------------------------------------------------


def test_a_failed_run_on_a_live_workflow_is_a_failure():
    assert classify(run(conclusion="failure")) == FAILING


def test_cancelled_is_not_green():
    """The reason bin/oa-green exists: 12 of 13 jobs ticked proves nothing."""
    assert classify(run(conclusion="cancelled")) == FAILING


def test_timed_out_and_startup_failure_are_not_green():
    assert classify(run(conclusion="timed_out")) == FAILING
    assert classify(run(conclusion="startup_failure")) == FAILING


def test_a_run_stuck_in_progress_past_the_grace_period_is_a_failure():
    stuck = run(status="in_progress", conclusion=None, created_at="2026-07-27T12:00:00Z")
    assert classify(stuck) == FAILING


def test_reports_a_failure_that_happened_after_the_retirement():
    """The 2026-07-28 incident. A dispatch-only workflow that failed TODAY is live.

    Switching a workflow to workflow_dispatch must not silence a failure that
    happened under that very configuration.
    """
    outcome = classify(
        run(name="Release and PyPI Publish", conclusion="failure",
            created_at="2026-07-28T04:00:00Z"),
        source=DISPATCH_ONLY,
        changed_at="2026-07-28T02:22:00Z",
    )
    assert outcome == FAILING


def test_a_failed_scheduled_run_is_live_even_after_a_later_workflow_edit():
    """A cron failure is live evidence, not frozen manual-run history."""
    outcome, explanation = classify_run(
        run(
            name="Production DB backup freshness",
            conclusion="failure",
            created_at="2026-07-28T01:00:00Z",
        ),
        ACTIVE,
        SCHEDULE_ONLY,
        "2026-07-28T02:22:00Z",
        HEAD,
        NOW,
        6.0,
    )
    assert outcome == FAILING
    assert "retired" not in explanation


def test_a_failure_predating_a_workflow_edit_stays_red_but_says_so():
    """openadapt-wright: 9 for 9 failures in March, a gate added on 2026-07-28.

    No green run exists, so it stays red. The reader is told to re-run rather
    than re-diagnose, because a path-filtered workflow may not be triggered
    again for months.
    """
    outcome, explanation = classify_run(
        run(name="Deploy Worker", conclusion="failure", created_at="2026-03-19T17:59:55Z"),
        ACTIVE, PUSH_GATED, "2026-07-28T02:22:22Z", HEAD, NOW, 6.0,
    )
    assert outcome == FAILING
    assert "re-run it" in explanation


def test_a_red_github_managed_workflow_is_a_failure():
    """Dependabot and CodeQL default setup have no file, but they are live."""
    managed = {"id": 9, "state": "active", "path": "dynamic/dependabot/dependabot-updates"}
    assert classify(run(conclusion="failure"), workflow=managed, source=None) == FAILING


def test_an_inactivity_disabled_workflow_is_failing():
    """openadapt-herald's weekly digest, 2026-07-13 to at least 2026-10-09.

    GitHub disabled the scheduled workflow after 60 days without repository
    activity and never turns it back on. Calling that "retired" let the sweep
    pass for weeks while the digest had stopped. Nobody chose to stop it, so it
    is a failure whatever its last run concluded.
    """
    disabled = {"id": 1, "state": "disabled_inactivity", "path": ".github/workflows/x.yml"}
    for conclusion in ("success", "failure"):
        outcome, explanation = classify_run(
            run(conclusion=conclusion), disabled, SCHEDULE_ONLY, None, HEAD, NOW, 6.0
        )
        assert outcome not in NOT_A_FAILURE, conclusion
        assert "60 days" in explanation
        assert "gh workflow enable x.yml" in explanation


def test_a_schedule_near_the_inactivity_limit_warns():
    """Evals, capture and tray were 4 to 5 weeks from the same 60-day limit."""
    # Last commit 50 days before now: GitHub disables the schedule in 10 days.
    warning = schedule_expiry_warning(ACTIVE, SCHEDULE_ONLY, "2026-06-08T12:00:00Z", NOW)
    assert warning is not None
    assert "2026-08-07" in warning
    # Last commit 10 days before now: 50 days remain, so nothing to say yet.
    assert schedule_expiry_warning(ACTIVE, SCHEDULE_ONLY, "2026-07-18T12:00:00Z", NOW) is None
    # Only a schedule expires, and only an active one can still be saved.
    assert schedule_expiry_warning(ACTIVE, PUSH_GATED, "2026-06-08T12:00:00Z", NOW) is None
    disabled = {**ACTIVE, "state": "disabled_manually"}
    assert schedule_expiry_warning(disabled, SCHEDULE_ONLY, "2026-06-08T12:00:00Z", NOW) is None


class _FakeReader:
    """Canned GitHub reads, keyed by the request path without its query."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    def get(self, path):
        self.calls += 1
        return self.responses.get(path.split("?", 1)[0])


def _encoded(source):
    return {"content": base64.b64encode(source.encode()).decode()}


def _repository_responses(slug, workflows, runs, last_commit_at, sources):
    responses = {
        f"repos/{slug}/actions/workflows": {"workflows": workflows},
        f"repos/{slug}/actions/runs": {"workflow_runs": runs},
        f"repos/{slug}/commits/main": {
            "sha": HEAD,
            "commit": {"committer": {"date": last_commit_at}},
        },
    }
    for path, source in sources.items():
        responses[f"repos/{slug}/contents/{path}"] = _encoded(source)
    return responses


def test_the_sweep_reports_an_auto_disabled_workflow_missing_from_the_run_feed():
    """Only active workflows got a run top-up, so a disabled one could vanish."""
    slug = "OpenAdaptAI/openadapt-herald"
    digest = {
        "id": 7,
        "name": "weekly-digest",
        "state": "disabled_inactivity",
        "path": ".github/workflows/release-announce.yml",
        "html_url": "https://github.com/OpenAdaptAI/openadapt-herald/blob/main/x.yml",
    }
    reader = _FakeReader(
        _repository_responses(slug, [digest], [], "2026-07-28T00:00:00Z", {})
    )
    result = sweep_repository(
        reader, {"full_name": slug, "default_branch": "main", "private": False}, 6.0
    )
    assert [entry["workflow"] for entry in result["failures"]] == ["weekly-digest"]
    assert "60 days" in result["failures"][0]["explanation"]


def test_the_sweep_warns_before_a_public_schedule_is_disabled():
    slug = "OpenAdaptAI/openadapt-evals"
    path = ".github/workflows/evidence-freshness.yml"
    nightly = {"id": 3, "name": "evidence-freshness", "state": "active", "path": path}
    green = run(name="evidence-freshness", workflow_id=3, head_sha=OLD, path=path)
    # 50 days before the real clock, so about 10 days remain.
    last_commit = (datetime.now(timezone.utc) - timedelta(days=50)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    responses = _repository_responses(
        slug, [nightly], [green], last_commit, {path: SCHEDULE_ONLY}
    )

    public = sweep_repository(
        _FakeReader(responses), {"full_name": slug, "default_branch": "main"}, 6.0
    )
    assert public["failures"] == []
    assert [entry["workflow"] for entry in public["warnings"]] == ["evidence-freshness"]

    # The 60-day rule applies to public repositories only.
    private = sweep_repository(
        _FakeReader(responses),
        {"full_name": slug, "default_branch": "main", "private": True},
        6.0,
    )
    assert private["warnings"] == []


def test_a_warning_alone_raises_the_alert_and_is_reported():
    class _Reader:
        calls = 0

    warned = [{
        "repo": "OpenAdaptAI/openadapt-evals", "branch": "main", "failures": [],
        "notes": [], "unreadable": False,
        "warnings": [{"workflow": "evidence-freshness", "outcome": "schedule-expiring",
                      "explanation": "GitHub disables this schedule around 2026-11-02",
                      "url": ""}],
    }]
    assert should_alert(warned)
    assert not should_alert([{**warned[0], "warnings": []}])
    body = render(warned, _Reader(), "", 6.0)
    assert "1 scheduled workflow will stop" in body
    assert "evidence-freshness" in body
    assert "2026-11-02" in body


# --------------------------------------------------------------------------
# It must stay quiet on what is not a failure
# --------------------------------------------------------------------------


def test_a_success_on_head_is_green():
    assert classify(run()) == GREEN
    assert classify(run(conclusion="neutral")) == GREEN
    assert classify(run(conclusion="skipped")) == GREEN


def test_a_deleted_workflow_is_retired_not_failing():
    """GitHub keeps old runs for ever; a deleted workflow's last failure is history."""
    outcome = classify(
        run(conclusion="failure", created_at="2026-02-18T04:54:00Z"),
        workflow=None,
        source=None,
        changed_at="2026-07-01T00:00:00Z",
    )
    assert outcome == RETIRED


def test_a_manually_disabled_workflow_is_retired():
    """Someone turned it off on purpose; its last run is history."""
    disabled = {"id": 1, "state": "disabled_manually", "path": ".github/workflows/x.yml"}
    assert classify(run(conclusion="failure"), workflow=disabled) == RETIRED


def test_a_dispatch_only_workflow_whose_failure_predates_retirement_is_not_a_failure():
    """The other half of the 2026-07-28 incident: the five-month-old failure itself."""
    outcome = classify(
        run(name="Release and PyPI Publish", conclusion="failure",
            created_at="2026-07-28T00:04:00Z"),
        source=DISPATCH_ONLY,
        changed_at="2026-07-28T02:22:00Z",
    )
    assert outcome == NOT_PUSH_GATED


def test_a_schedule_only_workflow_failure_is_live():
    outcome, explanation = classify_run(
        run(conclusion="failure", created_at="2026-01-01T00:00:00Z"),
        ACTIVE,
        SCHEDULE_ONLY,
        "2026-06-01T00:00:00Z",
        HEAD,
        NOW,
        6.0,
    )
    assert outcome == FAILING
    assert "retired" not in explanation


def test_a_young_in_flight_run_does_not_alert():
    """A run that started 20 minutes ago is not a defect; alerting on it flaps."""
    fresh = run(status="in_progress", conclusion=None, created_at="2026-07-28T11:40:00Z")
    assert classify(fresh) == IN_FLIGHT


# --------------------------------------------------------------------------
# A green run on an older tree is a note, and only where it means something
# --------------------------------------------------------------------------


def test_a_green_run_on_an_older_commit_is_reported_as_stale():
    assert classify(run(head_sha=OLD)) == STALE_GREEN


def test_a_stale_green_nightly_workflow_is_not_reported():
    """A scheduled workflow is SUPPOSED to have last run on an older commit."""
    assert classify(run(head_sha=OLD), source=SCHEDULE_ONLY) == GREEN


def test_a_stale_green_github_managed_workflow_is_not_reported():
    managed = {"id": 9, "state": "active", "path": "dynamic/dependabot/dependabot-updates"}
    assert classify(run(head_sha=OLD), workflow=managed, source=None) == GREEN


# --------------------------------------------------------------------------
# Trigger parsing
# --------------------------------------------------------------------------


def test_push_gating_detection():
    assert is_push_gated(PUSH_GATED)
    assert not is_push_gated(DISPATCH_ONLY)
    assert not is_push_gated(SCHEDULE_ONLY)
    assert is_push_gated("on: [push, workflow_dispatch]\njobs: {}\n")
    assert is_push_gated("on: push\njobs: {}\n")
    assert is_push_gated('"on":\n  pull_request:\njobs: {}\n')
    # YAML 1.1 turns a bare `on` key into `true`; some formatters emit that.
    assert is_push_gated("true:\n  push:\njobs: {}\n")


def test_schedule_detection():
    assert is_scheduled(SCHEDULE_ONLY)
    assert is_scheduled("on: [workflow_dispatch, schedule]\njobs: {}\n")
    assert not is_scheduled(DISPATCH_ONLY)
    assert not is_scheduled("this is not a workflow at all")


def test_a_later_jobs_key_does_not_leak_into_the_on_block():
    """`jobs:` starts at column 0, so the on-block read stops there."""
    source = "on:\n  workflow_dispatch:\njobs:\n  push:\n    runs-on: ubuntu-latest\n"
    assert not is_push_gated(source)


def test_a_commented_out_trigger_does_not_count():
    assert not is_push_gated("on:\n  workflow_dispatch:\n  # push:\njobs: {}\n")


def test_an_unparseable_workflow_is_assumed_live():
    """Assuming live keeps a real failure visible; assuming retired hides one."""
    assert is_push_gated("this is not a workflow at all")


def test_github_managed_paths():
    assert is_github_managed("dynamic/dependabot/dependabot-updates")
    assert is_github_managed("dynamic/github-code-scanning/codeql")
    assert not is_github_managed(".github/workflows/ci.yml")


# --------------------------------------------------------------------------
# The report must say which half of the organisation it looked at
# --------------------------------------------------------------------------


def test_a_token_that_lists_no_private_repository_is_detected():
    """The first real run said "1 of 26" while 8 private repositories were invisible."""
    assert not token_sees_private([{"name": "a", "private": False}])
    assert token_sees_private([{"name": "a", "private": False}, {"name": "b", "private": True}])


def test_the_report_says_so_when_it_saw_no_private_repository():
    class _Reader:
        calls = 0

    clean = [{"repo": "OpenAdaptAI/x", "branch": "main", "failures": [], "notes": [],
              "unreadable": False}]
    hidden = render(clean, _Reader(), "", 6.0, sees_private=False)
    assert "PUBLIC repositories we own" in hidden
    assert "saw no private repository" in hidden

    full = render(clean, _Reader(), "", 6.0, sees_private=True)
    assert "PUBLIC repositories" not in full
    assert "saw no private repository" not in full
