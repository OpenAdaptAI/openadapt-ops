#!/usr/bin/env python3
"""Sweep every repository we own for a default branch that is not green.

WHY THIS EXISTS
---------------
Three repositories published a red ``Release and PyPI Publish`` badge at the top
of a PUBLIC repository page for five months and nobody acted. The signal was
never hidden; it was ignored. Adding a fourth per-repository signal would repeat
that. What is missing is one place that looks at ALL of them, once a day, and
files ONE issue.

Nothing else does this. Four repositories carry a ``release-health`` workflow
(``openadapt-flow``, ``openadapt-capture``, ``openadapt-desktop``,
``OpenAdapt``), but each ``.github/release-health.json`` hardcodes a single
``"repository"`` and answers a different question: is releasable work
unpublished? None of them reads another repository's Actions API, and none of
them asks whether the default branch is green. ``bin/oa-green`` in the workspace
asks exactly the right question, but it is a local script and nothing runs it on
a schedule -- so it only helps whoever remembers to run it.

This repository is the right home because it already owns ``repos.yml``, the only
committed multi-repository list, and already files and updates one issue on a
daily cron in ``published-version-claims.yml``. This copies that pattern.

WHAT COUNTS AS GREEN
--------------------
Ported from ``bin/oa-green``, not re-derived:

- ``cancelled``, ``timed_out``, ``startup_failure`` and "still running" are NOT
  green. A cancelled run proves nothing about the tree, and concurrency
  ``cancel-in-progress`` makes cancellations common exactly when several merges
  land together, which is exactly when nobody has attention to spare.
- A red newest run is interrogated before it is believed. GitHub keeps a
  workflow's runs for ever, so a workflow that stopped running leaves its last
  failure as "the newest run" permanently::

      workflow file gone from the default branch -> RETIRED
      workflow disabled                          -> RETIRED
      no push / pull_request trigger left        -> NOT PUSH-GATED
      otherwise                                  -> genuinely NOT GREEN

- A GREEN run whose head SHA is not the current head tested an older tree. That
  is worth saying and is never a failure.

RETIRED and NOT PUSH-GATED are never reported as failures. A daily issue that
cries wolf gets muted, and a muted alert is worse than none -- that is the same
mechanism that let a red badge sit for five months.

TWO CORRECTIONS TO ``oa-green``
-------------------------------
1. **Retirement only excuses a failure that PREDATES it.** ``oa-green`` says so
   itself: "switching a workflow to workflow_dispatch quiets this tool about
   it". That is not hypothetical. ``openadapt-grounding``,
   ``openadapt-retrieval`` and ``openadapt-viewer`` failed
   ``Release and PyPI Publish`` on ``main`` from 2026-02-18, kept failing for
   five months, failed again on a push at 2026-07-28T00:04Z, and were switched
   to ``workflow_dispatch``-only at 2026-07-28T02:22Z. A rule that trusts the
   current trigger alone would call all three "stale" for ever and would also
   stay silent if the next dispatched release failed.

   So a retired or dispatch-only workflow's red run is frozen history **only if
   the run started before the commit that retired it**. A red run that started
   after that commit happened under the current configuration and is live. The
   comparison costs one extra read, and only for a workflow that is already red.

2. **An in-flight run gets a grace period.** ``oa-green`` is a point-in-time
   check a human runs before acting, so any in-flight run correctly fails it. A
   daily cron alerting on every in-flight run would flap for a reason that is
   not a defect, so an in-progress run only counts once it has been running
   longer than ``--running-grace-hours`` (default 6, comfortably longer than the
   longest matrix in the organisation). A younger one is context, not an alert.

Two smaller rules keep the report readable. A ``dynamic/`` workflow path is
GitHub's own synthesised workflow (Dependabot updates, CodeQL default setup): it
has no file in the repository and is never push-gated, so it is neither retired
nor stale-green, and a red one is live. And a stale green run is only worth
saying about a workflow that is actually push-gated -- a nightly or Dependabot
workflow is *supposed* to have last run on an older commit, and reporting each
one buries the handful that mean something.

REPOSITORY LIST
---------------
The live organisation listing, not ``repos.yml``. ``repos.yml`` is the docs-site
registry: 13 entries that deliberately omit internal tooling "so a product
evaluator sees the product, not the toolshed". It is correct for its purpose and
wrong for this one -- it omits roughly 20 repositories we own, including this
one. A sweep built on it would leave uncovered precisely the repositories that
are covered by nothing today.

Archived repositories are excluded: their history is frozen and cannot be
repaired. Forks are excluded: their default branch tracks somebody else's tree,
and AGENTS.md is explicit that a red branch on an upstream we forked is not our
business ("write access is not authority").

PERMISSIONS
-----------
A public repository's Actions API is readable with no authentication at all, so
the default repository-scoped ``GITHUB_TOKEN`` reads every public repository we
own and no new secret is needed.

A private repository is not merely 404 to that token: it does not appear in the
organisation listing at all, so the sweep cannot even name it as skipped. The
first real run therefore reported "1 of 26 repositories we own" while 8 private
repositories were invisible. An understated count is the muted signal this job
exists to prevent, so the report states plainly when it saw no private
repository. Supply a token with ``actions:read`` on them in ``OA_SWEEP_TOKEN`` to
cover them; a repository that IS listed but whose Actions API refuses the token
is reported as "not readable", never as a failure.

COST
----
About 3 API reads per repository plus one per red workflow: roughly 110 reads
for the whole organisation against a 1000/hour budget. Every list call sets an
explicit ``per_page`` and there is no pagination loop except the organisation
listing itself. Standard library only: no dependency install, no lockfile, no
cache, so the job is a runner start plus a few seconds.

Usage::

    python scripts/sweep_default_branch_ci.py
        [--markdown FILE] [--github-output FILE] [--run-url URL]
        [--running-grace-hours N]
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_ROOT = "https://api.github.com"
ORG = "OpenAdaptAI"
HTTP_TIMEOUT_SECONDS = 45

#: A run with one of these conclusions tested the tree and the tree passed.
#: Everything else -- including ``cancelled``, ``timed_out`` and
#: ``startup_failure`` -- proves nothing about the tree.
GREEN_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})

#: Outcomes of :func:`classify_run`.
GREEN = "green"
STALE_GREEN = "stale-green"
RETIRED = "retired"
NOT_PUSH_GATED = "not-push-gated"
IN_FLIGHT = "in-flight"
FAILING = "failing"

#: Never reported as a failure. Frozen history, not a live signal.
NOT_A_FAILURE = frozenset({GREEN, STALE_GREEN, RETIRED, NOT_PUSH_GATED, IN_FLIGHT})


class Reader:
    """Counted, failure-tolerant GitHub reads.

    A repository the token cannot see returns ``None`` rather than raising, so
    one private repository can never fail the whole sweep.
    """

    def __init__(self, token: str | None) -> None:
        self.token = token
        self.calls = 0

    def get(self, path: str) -> object | None:
        self.calls += 1
        request = urllib.request.Request(f"{API_ROOT}/{path}")
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        request.add_header("User-Agent", "openadapt-default-branch-sweep")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404, 451):
                return None
            raise


_ON_KEY = re.compile(r"^(on|\"on\"|'on'|True|true)\s*:")
_TRIGGER = re.compile(r"\b(push|pull_request|pull_request_target|merge_group)\b")


def is_push_gated(source: str) -> bool:
    """Does this workflow still run on a change to the default branch?

    Text-level, because the standard library has no YAML parser and this job
    installs nothing. The ``on:`` block is located and read to the next
    top-level key. YAML 1.1 turns the bare key ``on`` into ``true``, which some
    formatters emit, so that spelling is accepted too.

    An unparseable file returns ``True``: assuming a workflow is live keeps a
    real failure visible, whereas assuming it is retired would hide one.
    """
    lines = [line for line in source.splitlines() if not line.lstrip().startswith("#")]
    block: list[str] = []
    inside = False
    for line in lines:
        if not inside:
            if _ON_KEY.match(line):
                inside = True
                block.append(line.split(":", 1)[1])
            continue
        if line.strip() and not line[0].isspace():
            break
        block.append(line)
    if not inside:
        return True
    return _TRIGGER.search("\n".join(block)) is not None


def _parse_time(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def is_github_managed(path: str) -> bool:
    """Is this one of GitHub's own synthesised workflows?

    Dependabot updates and CodeQL default setup run under a ``dynamic/`` path
    with no file in the repository. They are never push-gated and can never be
    retired by a commit, so the file-based questions do not apply to them.
    """
    return path.startswith("dynamic/")


def classify_run(
    run: dict,
    workflow: dict | None,
    workflow_source: str | None,
    workflow_changed_at: str | None,
    head_sha: str,
    now: datetime,
    running_grace_hours: float,
) -> tuple[str, str]:
    """Decide what the newest run of one workflow proves. Pure; no I/O.

    ``workflow`` is the live inventory entry, or ``None`` when the workflow no
    longer exists. ``workflow_source`` is the decoded workflow file on the
    default branch, or ``None`` when it is not there. ``workflow_changed_at`` is
    the timestamp of the newest commit touching that path, used to decide
    whether a retirement predates the failure it would excuse.

    Returns ``(outcome, explanation)``.
    """
    sha = (run.get("head_sha") or "")[:7]
    started = _parse_time(run["created_at"])

    if run.get("status") != "completed":
        hours = (now - started).total_seconds() / 3600
        state = run.get("status", "queued")
        if hours >= running_grace_hours:
            return FAILING, f"{state} for {hours:.0f}h on `{sha}` -- stuck, and not evidence"
        return IN_FLIGHT, f"{state} for {hours:.1f}h on `{sha}` -- not yet evidence either way"

    conclusion = run.get("conclusion") or "none"
    path = (workflow or {}).get("path", run.get("path", ""))
    managed = is_github_managed(path)

    if conclusion in GREEN_CONCLUSIONS:
        stale = bool(head_sha) and run.get("head_sha") != head_sha
        # Only meaningful for a workflow that is meant to run on every change.
        # A nightly or Dependabot workflow is supposed to have last run on an
        # older commit, and saying so about each one buries the ones that matter.
        gated = (
            not managed and workflow_source is not None and is_push_gated(workflow_source)
        )
        if stale and gated:
            return STALE_GREEN, (
                f"{conclusion}, but it tested `{sha}` and head is `{head_sha[:7]}` -- "
                "that pass is evidence about a tree nobody runs any more"
            )
        return GREEN, conclusion

    # Red. GitHub keeps this run for ever, so establish whether the workflow can
    # still run before believing that the tree is broken.
    if managed:
        # GitHub manages the trigger; there is nothing to retire and no file to
        # read. A red one is live.
        return FAILING, f"newest run concluded {conclusion} on `{sha}`"

    if workflow is not None and workflow.get("state") not in (None, "active"):
        # A disabled workflow cannot run at all, so this run is necessarily past.
        return RETIRED, f"workflow {workflow['state']}; the {conclusion} run is frozen history"

    retirement: str | None = None
    if workflow is None:
        retirement = f"workflow deleted; the {conclusion} run is kept for ever"
    elif workflow_source is None:
        retirement = (
            f"{workflow['path']} is not on the default branch; "
            f"the {conclusion} run is frozen history"
        )
    elif not is_push_gated(workflow_source):
        retirement = (
            f"dispatch or schedule only, so the {conclusion} run says nothing about the tree"
        )

    if retirement is None:
        detail = f"newest run concluded {conclusion} on `{sha}`"
        if workflow_changed_at and started < _parse_time(workflow_changed_at):
            # Still red, because no green run exists -- but say that the
            # configuration has moved on, so the reader re-runs rather than
            # re-diagnosing. A path-filtered workflow can sit like this for
            # months without another push reaching it.
            detail += (
                f"; the workflow file changed afterwards ({workflow_changed_at}), "
                "so re-run it to find out whether the fix took"
            )
        return FAILING, detail

    # Retirement only excuses a failure that predates it. Three repositories
    # failed a push-triggered release at 2026-07-28T00:04Z and were switched to
    # workflow_dispatch at 02:22Z; trusting the current trigger alone would have
    # hidden the next dispatched failure too.
    if workflow_changed_at and started > _parse_time(workflow_changed_at):
        return FAILING, (
            f"newest run concluded {conclusion} on `{sha}` AFTER the workflow was "
            f"retired ({workflow_changed_at}), so it failed as currently configured"
        )
    if workflow_changed_at:
        retirement += f" (retired {workflow_changed_at}, after that run)"
    return (NOT_PUSH_GATED if workflow is not None and workflow_source else RETIRED), retirement


def token_sees_private(repositories: list[dict]) -> bool:
    """Did the organisation listing include even one private repository?

    A repository-scoped ``GITHUB_TOKEN`` does not merely 404 on a private
    repository's Actions API -- the repository never appears in the organisation
    listing at all, so the sweep cannot report it as "not readable" because it
    never learns it exists. The first real run said "1 of 26 repositories we own"
    while 8 private repositories were invisible. A quietly understated count is
    exactly the muted signal this job exists to prevent, so the report says which
    half of the organisation it actually looked at.
    """
    return any(repo.get("private") for repo in repositories)


def owned_repositories(reader: Reader) -> list[dict]:
    """Every non-archived, non-fork repository in the organisation the token can see."""
    found: list[dict] = []
    page = 1
    while True:
        batch = reader.get(f"orgs/{ORG}/repos?per_page=100&type=all&page={page}")
        if not batch:
            break
        found.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return sorted(
        (repo for repo in found if not repo.get("archived") and not repo.get("fork")),
        key=lambda repo: repo["name"].lower(),
    )


def newest_run_per_workflow(
    reader: Reader, slug: str, branch: str, workflow_ids: list[int]
) -> dict[int, dict]:
    """Newest run per workflow on ``branch``: one list call plus targeted top-ups.

    One very chatty workflow can monopolise the combined feed and silently hide
    another workflow's red run. Any active workflow missing from the feed gets
    one single-run query, so the extra cost is bounded by the size of that gap
    rather than paid once per workflow.
    """
    feed = reader.get(
        f"repos/{slug}/actions/runs?branch={branch}&per_page=100&exclude_pull_requests=true"
    )
    newest: dict[int, dict] = {}
    for run in (feed or {}).get("workflow_runs", []):
        workflow_id = run["workflow_id"]
        if workflow_id not in newest or run["created_at"] > newest[workflow_id]["created_at"]:
            newest[workflow_id] = run

    for workflow_id in workflow_ids:
        if workflow_id in newest:
            continue
        extra = reader.get(
            f"repos/{slug}/actions/workflows/{workflow_id}/runs"
            f"?branch={branch}&per_page=1&exclude_pull_requests=true"
        )
        for run in (extra or {}).get("workflow_runs", []):
            newest[workflow_id] = run
    return newest


def sweep_repository(reader: Reader, repo: dict, running_grace_hours: float) -> dict:
    slug = repo["full_name"]
    branch = repo.get("default_branch") or "main"
    result: dict = {
        "repo": slug,
        "branch": branch,
        "failures": [],
        "notes": [],
        "unreadable": False,
    }

    inventory = reader.get(f"repos/{slug}/actions/workflows?per_page=100")
    if inventory is None:
        result["unreadable"] = True
        return result
    workflows = {entry["id"]: entry for entry in inventory.get("workflows", [])}

    active_ids = [wid for wid, entry in workflows.items() if entry.get("state") == "active"]
    newest = newest_run_per_workflow(reader, slug, branch, active_ids)
    if not newest:
        return result

    head = reader.get(f"repos/{slug}/commits/{branch}")
    head_sha = (head or {}).get("sha", "")
    now = datetime.now(timezone.utc)

    source_cache: dict[str, str | None] = {}
    changed_cache: dict[str, str | None] = {}

    def workflow_source(path: str) -> str | None:
        if path not in source_cache:
            contents = reader.get(f"repos/{slug}/contents/{path}?ref={branch}")
            if contents is None:
                source_cache[path] = None
            else:
                try:
                    source_cache[path] = base64.b64decode(contents.get("content", "")).decode(
                        "utf-8", "replace"
                    )
                except Exception:
                    source_cache[path] = ""
        return source_cache[path]

    def workflow_changed_at(path: str) -> str | None:
        if path not in changed_cache:
            commits = reader.get(f"repos/{slug}/commits?path={path}&sha={branch}&per_page=1")
            changed_cache[path] = (
                commits[0]["commit"]["committer"]["date"] if commits else None
            )
        return changed_cache[path]

    for workflow_id, run in sorted(newest.items(), key=lambda item: item[1]["name"]):
        workflow = workflows.get(workflow_id)
        path = (workflow or {}).get("path", run.get("path", ""))
        completed = run.get("status") == "completed"
        conclusion = run.get("conclusion") or "none"
        red = completed and conclusion not in GREEN_CONCLUSIONS
        stale_green = (
            completed
            and conclusion in GREEN_CONCLUSIONS
            and bool(head_sha)
            and run.get("head_sha") != head_sha
        )

        # Reads are spent only where the answer can change the outcome: a red
        # run, or a green run on an older tree that may be worth a note. An
        # in-flight or up-to-date run costs nothing extra.
        source: str | None = None
        changed_at: str | None = None
        if (red or stale_green) and not is_github_managed(path) and path:
            if workflow is not None and workflow.get("state") == "active":
                source = workflow_source(path)
            if red:
                changed_at = workflow_changed_at(path)

        outcome, explanation = classify_run(
            run, workflow, source, changed_at, head_sha, now, running_grace_hours
        )
        if outcome == GREEN:
            continue
        entry = {
            "workflow": run["name"],
            "outcome": outcome,
            "explanation": explanation,
            "url": run.get("html_url", ""),
        }
        if outcome == FAILING:
            result["failures"].append(entry)
        else:
            result["notes"].append(entry)

    return result


def render(
    results: list[dict],
    reader: Reader,
    run_url: str,
    running_grace_hours: float,
    sees_private: bool = True,
) -> str:
    failing = sorted((r for r in results if r["failures"]), key=lambda r: r["repo"])
    noted = sorted(
        (r for r in results if not r["failures"] and r["notes"]), key=lambda r: r["repo"]
    )
    unreadable = sorted((r for r in results if r["unreadable"]), key=lambda r: r["repo"])

    scope = "repositories we own" if sees_private else "PUBLIC repositories we own"
    lines = [
        f"**{len(failing)} of {len(results)} {scope} do not have a genuinely "
        "green default branch.**",
        "",
    ]

    if not sees_private:
        # Say what was NOT looked at. A count that silently omits half the
        # organisation is the understated signal this job exists to prevent.
        lines += [
            "> **This run saw no private repository.** A repository-scoped `GITHUB_TOKEN` "
            "does not list them at all, so they are not skipped-and-reported here -- this "
            "job never learns they exist. Set an `OA_SWEEP_TOKEN` secret holding a token "
            "with `actions:read` on the private repositories to cover them.",
            "",
        ]

    lines += [
        "`cancelled`, `timed_out` and `startup_failure` are not green: such a run proves "
        "nothing about the tree. The usual cause is concurrency `cancel-in-progress` when "
        "several merges land at once, so re-run the cancelled run rather than assuming the "
        "older success still stands.",
        "",
        "This issue is rewritten in place once a day and closed when everything is green. "
        "Editing a body does not notify, so a long-lived gap does not become a daily ping.",
        "",
    ]

    for result in failing:
        lines.append(
            f"### [{result['repo']}](https://github.com/{result['repo']}) "
            f"(`{result['branch']}`)"
        )
        lines.append("")
        for entry in result["failures"]:
            link = f" ([run]({entry['url']}))" if entry["url"] else ""
            lines.append(f"- **{entry['workflow']}** — {entry['explanation']}{link}")
        for entry in result["notes"]:
            lines.append(f"- _{entry['workflow']}: {entry['outcome']} — {entry['explanation']}_")
        lines.append("")

    if noted:
        lines += [
            "<details><summary>Green, with notes — none of these is a failure</summary>",
            "",
            "`retired` and `not-push-gated` entries are frozen history: GitHub keeps a "
            "workflow's last run for ever, so a workflow that stopped running would "
            "otherwise be reported red permanently. `stale-green` passed on an older tree. "
            f"`in-flight` has been running for less than {running_grace_hours:g}h.",
            "",
        ]
        for result in noted:
            lines.append(f"- **{result['repo']}**")
            for entry in result["notes"]:
                lines.append(
                    f"  - {entry['workflow']}: {entry['outcome']} — {entry['explanation']}"
                )
        lines += ["", "</details>", ""]

    if unreadable:
        lines += [
            "<details><summary>Not readable by this token — skipped, not failed</summary>",
            "",
            "A private repository's Actions API returns 404 to the repository-scoped "
            "`GITHUB_TOKEN`. Set an `OA_SWEEP_TOKEN` secret holding a token with "
            "`actions:read` on these repositories to include them.",
            "",
        ]
        lines += [f"- {result['repo']}" for result in unreadable]
        lines += ["", "</details>", ""]

    lines.append(
        f"Swept {len(results)} repositories in {reader.calls} API reads. {run_url}".strip()
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", help="write the issue body to this file")
    parser.add_argument("--github-output", help="append alert= and clear= to this file")
    parser.add_argument("--run-url", default="", help="link back to the run that produced this")
    parser.add_argument(
        "--running-grace-hours",
        type=float,
        default=6.0,
        help="how long an in-progress run may run before it counts as stuck",
    )
    args = parser.parse_args(argv)

    token = (
        os.environ.get("OA_SWEEP_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )
    reader = Reader(token)

    repositories = owned_repositories(reader)
    if not repositories:
        print(
            f"sweep: the {ORG} repository listing returned nothing; refusing to report "
            "'everything is green' from an empty list",
            file=sys.stderr,
        )
        return 2

    results = [sweep_repository(reader, repo, args.running_grace_hours) for repo in repositories]
    failing = [result for result in results if result["failures"]]
    body = render(
        results,
        reader,
        args.run_url,
        args.running_grace_hours,
        sees_private=token_sees_private(repositories),
    )

    print(body)
    print(
        f"\nswept {len(results)} repositories in {reader.calls} API reads; "
        f"{len(failing)} not green",
        file=sys.stderr,
    )

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as handle:
            handle.write(body + "\n")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"alert={'true' if failing else 'false'}\n")
            handle.write(f"clear={'false' if failing else 'true'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
