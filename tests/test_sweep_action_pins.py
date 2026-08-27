"""The pin sweep must fire on a real unpinned action and stay quiet otherwise.

Proving a detector passes today is worthless on its own. These tests prove it
FAILS on the exact conditions it exists to catch -- including the real incident
that motivated it -- and that it stays quiet on the conditions that would make
it noise, because an alert that fires on a 112-item backlog every week gets
muted, and a muted alert is worse than none.

The 2026-08 incident, reproduced below as
``test_fires_on_the_pypi_publish_reference_that_broke_a_release``: twelve
repositories referenced ``pypa/gh-action-pypi-publish`` by a floating tag or by
the v1.14.0 SHA. v1.14.0 bundles twine 6.1.0, which rejects
``Metadata-Version: 2.5``. openadapt-evals 0.91.0 published its tag, its version
commit and its GitHub release, then failed to upload, leaving PyPI stale.
"""

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sweep_action_pins import (  # noqa: E402
    BARE,
    BRANCH,
    TAG,
    classify,
    key,
    regressions,
    render,
)

GOOD = "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33"


# --- what counts as pinned -------------------------------------------------


def test_a_full_commit_sha_is_pinned():
    assert classify(GOOD) is None
    assert classify("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1") is None


def test_fires_on_the_pypi_publish_reference_that_broke_a_release():
    """The exact reference that stranded openadapt-evals 0.91.0 on PyPI."""
    tier, action = classify("pypa/gh-action-pypi-publish@release/v1")
    assert tier == TAG
    assert action == "pypa/gh-action-pypi-publish"


def test_a_branch_reference_is_the_worst_tier():
    """superfly/flyctl-actions@master, live in the organisation in 2026-08."""
    assert classify("superfly/flyctl-actions/setup-flyctl@master") == (
        BRANCH,
        "superfly/flyctl-actions/setup-flyctl",
    )
    assert classify("some/action@main")[0] == BRANCH


def test_a_bare_reference_has_no_ref_at_all():
    assert classify("some/action") == (BARE, "some/action")


def test_a_major_tag_is_not_pinned_even_though_it_looks_stable():
    assert classify("actions/checkout@v4")[0] == TAG
    assert classify("python-semantic-release/publish-action@v9.15.2")[0] == TAG


def test_a_short_sha_is_not_a_pin():
    """Seven characters is ambiguous and GitHub does not treat it as immutable."""
    assert classify("actions/checkout@3d3c42e")[0] == TAG


def test_an_uppercase_sha_is_not_accepted_as_a_pin():
    assert classify("actions/checkout@3D3C42E5AAC5BA805825DA76410C181273BA90B1")[0] == TAG


# --- what is deliberately not reported -------------------------------------


def test_a_local_action_is_not_third_party():
    assert classify("./.github/actions/setup") is None


def test_a_docker_reference_is_out_of_scope():
    assert classify("docker://alpine:3.20") is None


# --- the baseline keeps the backlog quiet ----------------------------------


def _finding(repo="openadapt-ml", workflow="release.yml", ref="actions/checkout@v4",
             tier=TAG, line=10):
    return {"repo": repo, "workflow": workflow, "line": line, "ref": ref,
            "action": ref.split("@")[0], "tier": tier}


def test_an_accepted_reference_does_not_alert():
    finding = _finding()
    assert regressions([finding], {key(finding): TAG}) == []


def test_a_new_reference_alerts():
    finding = _finding()
    assert len(regressions([finding], {})) == 1


def test_a_reference_that_got_worse_alerts_even_though_it_is_in_the_baseline():
    """Accepting `@v4` must not silently accept `@master` on the same step."""
    was = _finding(ref="actions/checkout@v4", tier=TAG)
    now = _finding(ref="actions/checkout@master", tier=BRANCH)
    # Same file, different ref -> a different identity, so it alerts as new.
    assert len(regressions([now], {key(was): TAG})) == 1
    # And an identity whose tier degraded in place alerts too.
    assert len(regressions([now], {key(now): TAG})) == 1


def test_moving_a_step_within_a_file_does_not_alert():
    """A line-sensitive baseline would churn on every unrelated edit."""
    before = _finding(line=10)
    after = _finding(line=42)
    assert regressions([after], {key(before): TAG}) == []


# --- the report -------------------------------------------------------------


def test_the_report_says_when_it_only_saw_public_repositories():
    body = render([], [], repos=38, private_seen=False, run_url="")
    assert "public half" in body


def test_the_report_does_not_claim_a_gap_when_private_repositories_were_visible():
    body = render([], [], repos=38, private_seen=True, run_url="")
    assert "public half" not in body


def test_the_backlog_is_counted_but_not_listed_as_needing_attention():
    findings = [_finding(), _finding(workflow="ci.yml")]
    body = render(findings, [], repos=38, private_seen=True, run_url="")
    assert "Already in the reviewed backlog: **2**" in body
    assert "need attention" not in body


def test_a_regression_is_named_with_its_file_and_line():
    finding = _finding()
    new = regressions([finding], {})
    body = render([finding], new, repos=38, private_seen=True, run_url="")
    assert "1 reference(s) need attention" in body
    assert "`openadapt-ml`" in body
    assert "`release.yml`" in body


# --- the committed baseline stays loadable ---------------------------------


def test_the_committed_baseline_matches_the_schema_the_script_expects():
    path = REPO_ROOT / "action-pin-baseline.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    ids = [row["id"] for row in payload["accepted"]]
    assert ids == sorted(ids), "baseline rows must stay sorted so diffs stay readable"
    assert len(ids) == len(set(ids)), "baseline rows must be unique"
    for row in payload["accepted"]:
        assert row["tier"] in {BARE, TAG, BRANCH}
        assert row["id"].count("|") == 2
