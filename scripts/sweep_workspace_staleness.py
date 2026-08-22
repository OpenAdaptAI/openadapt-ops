#!/usr/bin/env python3
"""Sweep for stranded work: stale branches on GitHub and stale local trees.

WHY THIS EXISTS
---------------
On 2026-08-21 the workspace check ``bin/oa-fresh`` found 32 local clones behind
their origin, several by hundreds of commits, carrying unpushed or uncommitted
work. Reading a stale tree and reporting what is inside it has produced four
confident wrong findings in this workspace. ``bin/oa-fresh`` answers the local
question, but it is a local script: nothing runs it on a schedule, so it only
helps whoever remembers to run it.

This repository already owns the only committed multi-repository registry and
already files ONE issue per day from a scheduled sweep
(``default-branch-sweep.yml``, ``published-version-claims.yml``), so this copies
that pattern for the stranded-work question.

TWO DETECTORS, TWO PLACES THEY CAN RUN
--------------------------------------
1. **Remote detector (runs anywhere, default).** A branch pushed to GitHub that
   is not the default branch, has no open pull request, and has had no commit
   for ``--stale-days`` days is stranded: nobody is reviewing it, nothing will
   merge it, and every day it ages the harder salvage becomes. This needs only
   the REST API, so the hosted daily cron runs it.

2. **Local detector (needs the trees; opt-in via ``--local-root``).** For each
   first-level git clone under a workspace root it reports how far behind its
   origin the clone is, how many local commits are unpushed, and how many files
   are uncommitted. This is ``bin/oa-fresh`` ported here so one issue can carry
   both halves of the answer. A hosted runner cannot see these trees: until a
   self-hosted runner attached to the workspace machine runs this repository,
   the daily issue says plainly that local trees were not visible instead of
   implying they are fine.

SYNC MODE IS THE ONLY MUTATION, AND IT CANNOT LOSE WORK
-------------------------------------------------------
With ``--sync``, a tree is moved only when it is ON ITS DEFAULT BRANCH, CLEAN,
and has NO LOCAL COMMITS -- exactly ``bin/oa-fresh``'s rule -- and the only
mutation attempted is ``git merge --ff-only``, which refuses unless the move is
a pure fast-forward. The script never stashes, never discards, never checks out
a branch, never force-pushes, and never touches a dirty tree or a feature
branch. Anything else is reported for a human.

COST
----
Standard library only. The remote detector spends two list reads plus one read
per branch tip per repository; a few hundred API reads a day against the token
budget, with an explicit per_page on every call. Local mode costs one fetch per
clone, same as running ``bin/oa-fresh`` by hand.

ONE ISSUE, REWRITTEN IN PLACE
-----------------------------
Same rule as the other sweeps: a new issue every day is the same as no issue;
editing a body does not notify; silence when everything is current keeps the
alert unmuted.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ORG = "OpenAdaptAI"

# Branch-name prefixes that are machinery, not someone's stranded work.
IGNORED_BRANCH_PREFIXES = ("gh-readonly-queue/", "dependabot/", "l10n_")

# GitHub rejects an issue body over 65536 characters; keep the table readable
# long before that and guard the total as a last resort.
MAX_REMOTE_ROWS = 40
MAX_BODY_CHARS = 60000

# Remote classification outcomes worth asserting in tests.
DEFAULT = "default"
OPEN_PR = "open-pr"
STALE_UNMERGED = "stale-unmerged"
ACTIVE = "active"
IGNORED = "ignored"


class Reader:
    """Minimal authenticated GET client with an explicit per_page everywhere."""

    def __init__(self, token: str | None) -> None:
        self.token = token
        self.calls = 0

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        import urllib.request

        query = ""
        if params:
            query = "?" + "&".join(f"{key}={value}" for key, value in params.items())
        request = urllib.request.Request(f"https://api.github.com{path}{query}")
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "openadapt-ops-staleness-sweep")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        self.calls += 1
        try:
            with urllib.request.urlopen(request) as response:
                return json.load(response)
        except Exception:
            return None

    def get_all(self, path: str, params: dict[str, str] | None = None) -> list:
        """List with pagination; one page covers most repositories."""
        merged_params = dict(params or {})
        merged_params.setdefault("per_page", "100")
        items: list = []
        page = 1
        while True:
            merged_params["page"] = str(page)
            batch = self.get(path, merged_params)
            if not isinstance(batch, list) or not batch:
                break
            items.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return items


def parse_time(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def classify_branch(
    name: str,
    default_branch: str,
    open_pr_head_refs: set[str],
    last_commit_date: datetime,
    now: datetime,
    stale_days: float,
) -> str:
    """Classify one remote branch as stranded, machinery, or live work.

    A branch is STALE_UNMERGED only when it is not the default, not ignored
    machinery, carries no open pull request, and its newest commit predates the
    cutoff. Everything else stays quiet: a fresh branch without a pull request
    may be an hour old, and alarming on those would bury the real strandings.
    """
    if name == default_branch:
        return DEFAULT
    if any(name.startswith(prefix) for prefix in IGNORED_BRANCH_PREFIXES):
        return IGNORED
    if name in open_pr_head_refs:
        return OPEN_PR
    if last_commit_date < now - timedelta(days=stale_days):
        return STALE_UNMERGED
    return ACTIVE


def owned_repositories(reader: Reader) -> list[dict]:
    """Every repository in the organisation we own; archived ones excluded."""
    repositories = reader.get_all(f"/orgs/{ORG}/repos", {"type": "all"})
    if not isinstance(repositories, list):
        return []
    return [repo for repo in repositories if not repo.get("archived", False)]


def sweep_repository_remote(
    reader: Reader, repo: dict, now: datetime, stale_days: float
) -> dict:
    """Return the stranded-branch rows for one repository."""
    full_name = repo["full_name"]
    default_branch = repo.get("default_branch") or "main"
    pulls = reader.get_all(f"/repos/{full_name}/pulls", {"state": "open"})
    open_pr_head_refs = {
        pull.get("head", {}).get("ref") for pull in pulls if isinstance(pull, dict)
    } - {None}
    branches = reader.get_all(f"/repos/{full_name}/branches", {"per_page": "100"})
    rows: list[dict] = []
    if not isinstance(branches, list):
        # A private repository returns 404 to a token without access. That is a
        # visibility boundary to report, never a finding.
        return {"repo": full_name, "readable": False, "rows": []}
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        name = branch.get("name", "")
        sha = (branch.get("commit") or {}).get("sha")
        detail = reader.get(f"/repos/{full_name}/commits/{sha}") if sha else None
        dates: list[str] = []
        if isinstance(detail, dict):
            commit = detail.get("commit") or {}
            author_date = ((commit.get("author") or {}).get("date")) or ""
            committer_date = ((commit.get("committer") or {}).get("date")) or ""
            dates = [d for d in (author_date, committer_date) if d]
        if not dates:
            continue
        last_date = max(parse_time(d) for d in dates)
        verdict = classify_branch(
            name, default_branch, open_pr_head_refs, last_date, now, stale_days
        )
        if verdict != STALE_UNMERGED:
            continue
        age_days = (now - last_date).total_seconds() / 86400
        rows.append(
            {
                "repo": full_name,
                "branch": name,
                "last_commit": last_date.date().isoformat(),
                "age_days": round(age_days),
                "url": f"https://github.com/{full_name}/tree/{name}",
            }
        )
    return {"repo": full_name, "readable": True, "rows": rows}


# --------------------------------------------------------------------------
# Local-tree detector (bin/oa-fresh, ported)
# --------------------------------------------------------------------------


def git(tree_path: Path, *args: str) -> tuple[int, str]:
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(tree_path), *args],
        capture_output=True,
        text=True,
        timeout=180,
    )
    return completed.returncode, completed.stdout + completed.stderr


def local_trees(root: Path) -> list[Path]:
    """First-level directories under root that are git clones."""
    found: list[Path] = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and (entry / ".git").exists():
            found.append(entry)
    return found


def parse_status_porcelain(text: str) -> int:
    """Count changed entries in ``git status --porcelain`` output."""
    return len([line for line in text.splitlines() if line.strip()])


def count_commits(tree_path: Path, range_spec: str) -> int:
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(tree_path), "rev-list", "--count", range_spec],
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return -1


def detect_default_branch(tree_path: Path) -> tuple[str, str]:
    """Return (name, tracking-ref) for origin's default branch."""
    code, out = git(tree_path, "ls-remote", "--symref", "origin", "HEAD")
    if code == 0:
        for line in out.splitlines():
            if line.startswith("ref:"):
                ref = line[len("ref:") :].split("\t")[0].strip()
                if ref.startswith("refs/heads/"):
                    name = ref[len("refs/heads/") :]
                    return name, f"origin/{name}"
    return "main", "origin/main"


def inspect_tree(tree_path: Path) -> dict:
    """Read-only staleness report for one clone, mirroring bin/oa-fresh."""
    code, raw_branch = git(tree_path, "symbolic-ref", "--short", "HEAD")
    branch = raw_branch.strip() if (code == 0 and raw_branch.strip()) else "(detached)"
    git(tree_path, "fetch", "origin", "--quiet")
    default_name, default_ref = detect_default_branch(tree_path)
    ahead_source = default_ref
    if branch != "(detached)":
        code, _ = git(tree_path, "rev-parse", "--verify", "--quiet", f"origin/{branch}")
        if code == 0:
            ahead_source = f"origin/{branch}"
    behind = count_commits(tree_path, f"HEAD..{default_ref}")
    unpushed = count_commits(tree_path, f"{ahead_source}..HEAD")
    _code, status_text = git(tree_path, "status", "--porcelain")
    dirty = parse_status_porcelain(status_text)
    _code, raw_remote = git(tree_path, "remote", "get-url", "origin")
    return {
        "name": tree_path.name,
        "path": str(tree_path),
        "branch": branch,
        "behind": max(behind, 0),
        "unpushed": max(unpushed, 0),
        "dirty": dirty,
        "remote_url": raw_remote.strip(),
        "on_default": branch == default_name,
        "duplicate_of": "",
    }


def sync_tree(report: dict) -> str:
    """bin/oa-fresh's exact safety rule, then one fast-forward attempt.

    Returns a short outcome string. Anything other than 'fast-forwarded' means
    the tree was left exactly as it was.
    """
    if report["dirty"]:
        return "skipped: dirty tree"
    if not report["on_default"]:
        return "skipped: not on the default branch"
    if report["unpushed"]:
        return "skipped: has local commits"
    code, _output = git(
        Path(report["path"]), "merge", "--ff-only", "origin/" + report["branch"]
    )
    return "fast-forwarded" if code == 0 else "refused fast-forward"


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_local_table(local_rows: list[dict]) -> list[str]:
    lines = ["### Local workspace trees with problems", ""]
    lines.append("| Clone | Branch | Behind | Unpushed | Uncommitted |")
    lines.append("|---|---|---|---|---|")
    for row in sorted(
        local_rows,
        key=lambda item: (-item["behind"], -item["unpushed"], item["name"]),
    ):
        name = row["name"]
        if row.get("duplicate_of"):
            name = f"{name} (same remote as `{row['duplicate_of']}`)"
        lines.append(
            f"| {name} | {row['branch']} | {row['behind']} "
            f"| {row['unpushed']} | {row['dirty']} |"
        )
    return lines


def render(
    remote_rows: list[dict],
    unreadable: list[str],
    local_rows: list[dict] | None,
    synced: list[tuple[str, str]],
    stale_days: float,
    run_url: str,
) -> str:
    now = datetime.now(timezone.utc).date().isoformat()
    lines: list[str] = [
        "# Workspace staleness sweep",
        "",
        f"Swept {now}. Stranded-branch cutoff: {stale_days:g} days.",
        "",
    ]
    if remote_rows:
        ordered = sorted(remote_rows, key=lambda item: (-item["age_days"], item["repo"]))
        shown = ordered[:MAX_REMOTE_ROWS]
        lines.append(
            f"{len(ordered)} stranded branch(es) past the cutoff"
            + (f" (oldest {MAX_REMOTE_ROWS} shown)." if len(ordered) > MAX_REMOTE_ROWS else ".")
        )
        lines.append("")
        lines.append("| Repository | Stranded branch | Last commit | Age (days) |")
        lines.append("|---|---|---|---|")
        for row in shown:
            lines.append(
                f"| {row['repo']} | [{row['branch']}]({row['url']}) "
                f"| {row['last_commit']} | {row['age_days']} |"
            )
        hidden = len(ordered) - len(shown)
        if hidden:
            per_repo: dict[str, int] = {}
            for row in ordered[MAX_REMOTE_ROWS:]:
                per_repo[row["repo"]] = per_repo.get(row["repo"], 0) + 1
            summary = ", ".join(f"{name} ({count})" for name, count in sorted(per_repo.items()))
            lines.append("")
            lines.append(
                f"+{hidden} older stranded branch(es) not listed: {summary}. "
                "The full list is in the run log."
            )
        lines.append("")
        lines.append(
            "A stranded branch is not the default branch, has no open pull "
            "request, and has had no commit past the cutoff. Triage it: merge, "
            "supersede deliberately, or archive it. Nothing is deleted by this "
            "sweep."
        )
    else:
        lines.append("No stranded remote branches past the cutoff.")
    lines.append("")
    if unreadable:
        lines.append(
            "Not readable this run: "
            + ", ".join(sorted(unreadable))
            + ". The repository token cannot read private repositories; set "
            "the `OA_SWEEP_TOKEN` secret with read access to cover them."
        )
        lines.append("")
    if local_rows is None:
        lines.append(
            "**Local workspace trees were not visible from this runner**, so "
            "clones-behind-origin, unpushed-commit, and uncommitted-file counts "
            "are absent from this report. Run "
            "`scripts/sweep_workspace_staleness.py --local-root <workspace>` on "
            "the workspace machine, or attach a self-hosted runner there with "
            "`OA_SRC_ROOT` set, to fill this gap."
        )
    elif local_rows:
        lines.extend(render_local_table(local_rows))
        lines.append("")
    else:
        lines.append("Local trees: every checked-out clone is current and clean.")
    if synced:
        lines.append("")
        lines.append("Fast-forward attempts this run:")
        lines.append("")
        for name, outcome in synced:
            lines.append(f"- `{name}`: {outcome}")
    if run_url:
        lines.append("")
        lines.append(f"Produced by run {run_url}.")
    body = "\n".join(lines)
    # GitHub rejects issue bodies over 65536 characters; the first scheduled
    # run died exactly there (2026-08-22, GraphQL "Body is too long"). The
    # table cap above bounds the usual cause; this guard bounds every cause.
    if len(body) > MAX_BODY_CHARS:
        note = (
            f"\n\n---\n[truncated at {MAX_BODY_CHARS} of {len(body)} characters "
            "to fit the GitHub issue limit; full output is in the run log.]"
        )
        body = body[: MAX_BODY_CHARS - len(note)] + note
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", help="write the issue body to this file")
    parser.add_argument("--github-output", help="append alert= and clear= to this file")
    parser.add_argument("--run-url", default="", help="link back to the producing run")
    parser.add_argument(
        "--stale-days",
        type=float,
        default=14.0,
        help="a remote branch with no commit this old and no open PR is stranded",
    )
    parser.add_argument(
        "--local-root",
        default="",
        help="also inspect first-level git clones under this directory",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help=(
            "with --local-root: fast-forward clean default-branch clones; "
            "no other mutation of any kind"
        ),
    )
    parser.add_argument(
        "--offline-fixture",
        help="read a JSON fixture of remote rows instead of the API (for tests)",
    )
    args = parser.parse_args(argv)

    if args.sync and not args.local_root:
        parser.error("--sync requires --local-root")

    token = (
        os.environ.get("OA_SWEEP_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )

    synced: list[tuple[str, str]] = []
    local_rows: list[dict] | None = None
    if args.local_root:
        root = Path(args.local_root).expanduser().resolve()
        if not root.is_dir():
            # Fail loud rather than render a body that implies the trees are
            # fine: a silent all-clear from a wrong path is the exact failure
            # mode this sweep exists to prevent.
            print(f"sweep: --local-root {root} is not a directory", file=sys.stderr)
            return 2
        reports = [inspect_tree(tree) for tree in local_trees(root)]
        seen_urls: dict[str, str] = {}
        for report in reports:
            url = report["remote_url"]
            if url and url in seen_urls:
                report["duplicate_of"] = seen_urls[url]
            else:
                seen_urls[url] = report["name"]
        if args.sync:
            for report in reports:
                if report["behind"] > 0:
                    outcome = sync_tree(report)
                    synced.append((report["name"], outcome))
                    if outcome == "fast-forwarded":
                        report["behind"] = 0
        local_rows = [
            report
            for report in reports
            if report["behind"] or report["unpushed"] or report["dirty"]
        ]

    now = datetime.now(timezone.utc)
    unreadable: list[str] = []
    remote_rows: list[dict] = []
    if args.offline_fixture:
        fixture = json.loads(Path(args.offline_fixture).read_text(encoding="utf-8"))
        remote_rows = fixture.get("rows", [])
        unreadable = fixture.get("unreadable", [])
    else:
        reader = Reader(token)
        repositories = owned_repositories(reader)
        if not repositories:
            print(
                f"sweep: the {ORG} repository listing returned nothing; refusing "
                "to report 'everything is fine' from an empty list",
                file=sys.stderr,
            )
            return 2
        for repo in repositories:
            result = sweep_repository_remote(reader, repo, now, args.stale_days)
            if not result["readable"]:
                unreadable.append(result["repo"])
            remote_rows.extend(result["rows"])

    body = render(
        remote_rows,
        unreadable,
        local_rows,
        synced,
        args.stale_days,
        args.run_url,
    )
    print(body)
    alert = bool(remote_rows) or bool(local_rows)
    print(
        f"\nswept: {len(remote_rows)} stranded remote branches, "
        f"{len(local_rows or [])} problem local trees, "
        f"{len(synced)} fast-forward attempts",
        file=sys.stderr,
    )
    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as handle:
            handle.write(body + "\n")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"alert={'true' if alert else 'false'}\n")
            handle.write(f"clear={'false' if alert else 'true'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
