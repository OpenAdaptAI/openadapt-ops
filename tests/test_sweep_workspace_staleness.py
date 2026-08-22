"""The stranded-work sweep must fire on real strandings and stay quiet otherwise.

A daily issue that cries wolf gets muted, and a muted alert is worse than none.
These tests prove the classifiers FAIL on the exact conditions this sweep exists
to catch -- including the 2026-08-21 incident that motivated it -- and stay
quiet on the lookalikes that would make it noise: fresh agent branches, open
pull requests, queue and dependency machinery, and clean current local trees.
"""

import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sweep_workspace_staleness import (  # noqa: E402
    ACTIVE,
    DEFAULT,
    IGNORED,
    OPEN_PR,
    STALE_UNMERGED,
    classify_branch,
    detect_default_branch,
    inspect_tree,
    parse_status_porcelain,
    render,
    sync_tree,
)

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=30)
FRESH = NOW - timedelta(hours=2)


def classify(name="feat/experiment", default="main", prs=(), date=OLD, days=14.0):
    return classify_branch(name, default, set(prs), date, NOW, days)


# --------------------------------------------------------------------------
# Remote classification: it must fire on strandings
# --------------------------------------------------------------------------


def test_stale_unmerged_branch_without_pr_fires():
    assert classify() == STALE_UNMERGED


def test_age_just_past_cutoff_fires():
    assert classify(date=NOW - timedelta(days=14, hours=1)) == STALE_UNMERGED


# --------------------------------------------------------------------------
# Remote classification: it must stay quiet on the lookalikes
# --------------------------------------------------------------------------


def test_default_branch_never_fires():
    assert classify(name="main", date=OLD) == DEFAULT


def test_open_pr_head_is_live_work():
    assert classify(prs=("feat/experiment",)) == OPEN_PR


def test_fresh_branch_without_pr_is_not_stranded():
    assert classify(date=FRESH) == ACTIVE


def test_queue_machinery_is_ignored():
    assert classify(name="gh-readonly-queue/main/pr-123") == IGNORED


def test_dependabot_branch_is_ignored():
    assert classify(name="dependabot/pip/uv-0.12.4") == IGNORED


def test_cutoff_boundary_inside_window_stays_quiet():
    assert classify(date=NOW - timedelta(days=13, hours=23)) == ACTIVE


# --------------------------------------------------------------------------
# Local-tree parsing
# --------------------------------------------------------------------------


def test_status_porcelain_counts_entries():
    text = " M a.py\n?? b.txt\n\nM  c.py"
    assert parse_status_porcelain(text) == 3


def test_status_porcelain_empty_tree_is_zero():
    assert parse_status_porcelain("") == 0


# --------------------------------------------------------------------------
# Local trees: real git repositories in a scratch directory
# --------------------------------------------------------------------------


def _git(cwd, *args):
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _configure_identity(path):
    _git(path, "config", "user.email", "sweep@example.com")
    _git(path, "config", "user.name", "Sweep Test")


def _make_origin(tmp_path, branch="main"):
    """A real bare remote carrying one commit, like any repository on GitHub."""
    bare = tmp_path / f"origin-{branch}.git"
    _git(tmp_path, "init", "-q", "-b", branch, "--bare", str(bare))
    seed = tmp_path / f"seed-{branch}"
    seed.mkdir()
    _git(seed, "init", "-q", "-b", branch)
    _configure_identity(seed)
    (seed / "f.txt").write_text("one\n")
    _git(seed, "add", ".")
    _git(seed, "commit", "-qm", "one")
    _git(seed, "push", "-q", str(bare), branch)
    return bare


def _clone(tmp_path, bare, name, branch="main"):
    clone = tmp_path / name
    _git(tmp_path, "clone", "-q", "-b", branch, str(bare), str(clone))
    _configure_identity(clone)
    return clone


def test_inspect_and_sync_fast_forward_a_clean_default_clone(tmp_path):
    origin = _make_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")

    # Origin moves ahead; the clone does not know yet.
    other = _clone(tmp_path, origin, "other")
    (other / "g.txt").write_text("two\n")
    _git(other, "add", ".")
    _git(other, "commit", "-qm", "two")
    _git(other, "push", "-q", "origin", "main")

    report = inspect_tree(clone)
    assert report["on_default"] is True
    assert report["behind"] == 1
    assert report["unpushed"] == 0
    assert report["dirty"] == 0

    assert sync_tree(report) == "fast-forwarded"
    after = inspect_tree(clone)
    assert after["behind"] == 0


def test_sync_refuses_a_dirty_tree(tmp_path):
    origin = _make_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    (clone / "f.txt").write_text("local edit\n")

    report = inspect_tree(clone)
    assert report["dirty"] >= 1
    outcome = sync_tree(report)
    assert outcome.startswith("skipped")
    # The dirty state must survive untouched.
    assert "local edit" in (clone / "f.txt").read_text()


def test_sync_refuses_a_feature_branch(tmp_path):
    origin = _make_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    _git(clone, "switch", "-qc", "feat/side")

    report = inspect_tree(clone)
    outcome = sync_tree(report)
    assert outcome.startswith("skipped")
    assert report["branch"] == "feat/side"


def test_unpushed_commits_are_counted_not_synced(tmp_path):
    origin = _make_origin(tmp_path)
    clone = _clone(tmp_path, origin, "clone")
    (clone / "h.txt").write_text("mine\n")
    _git(clone, "add", ".")
    _git(clone, "commit", "-qm", "local only")

    report = inspect_tree(clone)
    assert report["unpushed"] == 1
    assert report["behind"] == 0
    assert sync_tree(report) == "skipped: has local commits"


def test_detect_default_branch_reads_the_remote(tmp_path):
    origin = _make_origin(tmp_path, branch="trunk")
    clone = _clone(tmp_path, origin, "clone", branch="trunk")
    name, ref = detect_default_branch(clone)
    assert name == "trunk"
    assert ref == "origin/trunk"


# --------------------------------------------------------------------------
# Rendering: silence and honesty rules
# --------------------------------------------------------------------------


ROW = {
    "repo": "OpenAdaptAI/openadapt-example",
    "branch": "feat/old",
    "last_commit": "2026-07-01",
    "age_days": 51,
    "url": "https://github.com/OpenAdaptAI/openadapt-example/tree/feat/old",
}

LOCAL_ROW = {
    "name": "openadapt-example",
    "branch": "feat/wip",
    "behind": 7,
    "unpushed": 2,
    "dirty": 3,
}


def test_render_names_local_invisibility_instead_of_faking_clean():
    body = render([ROW], [], None, [], 14, "https://run.example")
    assert "were not visible from this runner" in body
    assert "current and clean" not in body


def test_render_lists_problem_trees():
    body = render([], [], [LOCAL_ROW], [], 14, "")
    assert "| openadapt-example | feat/wip | 7 | 2 | 3 |" in body


def test_render_says_all_clear_only_when_it_ran_locally_and_found_none():
    body = render([], [], [], [], 14, "")
    assert "current and clean" in body


def test_render_marks_duplicate_clones():
    duplicate = dict(LOCAL_ROW, name="openadapt-hosted", duplicate_of="openadapt-cloud")
    body = render([], [], [LOCAL_ROW, duplicate], [], 14, "")
    assert "same remote as `openadapt-cloud`" in body


def test_render_reports_unreadable_private_repositories():
    body = render([ROW], ["OpenAdaptAI/private-one"], None, [], 14, "")
    assert "OpenAdaptAI/private-one" in body
    assert "OA_SWEEP_TOKEN" in body


def _rows(count: int) -> list[dict]:
    return [
        dict(ROW, branch=f"feat/old-{index}", age_days=100 - index)
        for index in range(count)
    ]


def test_render_caps_remote_table_and_counts_the_rest():
    from sweep_workspace_staleness import MAX_REMOTE_ROWS

    rows = _rows(MAX_REMOTE_ROWS + 7)
    body = render(rows, [], None, [], 14, "")
    assert f"{MAX_REMOTE_ROWS + 7} stranded branch(es) past the cutoff" in body
    assert f"oldest {MAX_REMOTE_ROWS} shown" in body
    assert "+7 older stranded branch(es)" in body
    assert "+7 older stranded branch(es)" in body
    # Exactly the cap is listed; nothing hidden leaks into the body.
    assert body.count("feat/old-") == MAX_REMOTE_ROWS
    assert "feat/old-40" not in body


def test_render_body_never_exceeds_github_limit():
    from sweep_workspace_staleness import MAX_BODY_CHARS

    wide = [
        dict(ROW, branch="feat/" + "x" * 400 + str(index), url="https://e.example")
        for index in range(200)
    ]
    body = render(wide, [], None, [], 14, "https://run.example")
    assert len(body) <= 65536
    if len(body) > MAX_BODY_CHARS:
        assert "[truncated at" in body
