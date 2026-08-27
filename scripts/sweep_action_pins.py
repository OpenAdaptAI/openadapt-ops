#!/usr/bin/env python3
"""Sweep every repository we own for a GitHub Action that is not pinned to a commit.

WHY THIS EXISTS
---------------
A ``uses:`` reference that names a tag or a branch resolves to whatever the
upstream owner points it at today. The owner can move a tag. Nothing in our
repositories records that it moved, so a release can change behaviour with no
commit of ours to review, to blame, or to revert.

This is not hypothetical here. ``pypa/gh-action-pypi-publish`` v1.14.0 bundles
twine 6.1.0 and packaging 25.0, which reject ``Metadata-Version: 2.5`` -- the
version current hatchling emits. It broke the openadapt-evals 0.91.0 release
AFTER the tag, the version commit and the GitHub release had already landed, so
PyPI stayed stale while every other artifact said the version shipped. Twelve
repositories were corrected by hand in 2026-08. Nothing stops the next one.

Nothing else detects this. ``dependency-review.yml`` reads dependency manifests,
not workflow ``uses:`` lines. ``codeql.yml`` analyses code. Dependabot proposes
version bumps but is equally happy to leave a floating tag floating.

WHAT COUNTS AS PINNED
---------------------
Only a full 40-character commit SHA. A tag is mutable by the upstream owner,
including a ``vN`` major tag that is *designed* to move. A branch is worse: it
tracks another project's HEAD continuously.

Three tiers, worst first:

- ``branch``   -- ``@master``, ``@main``: tracks upstream HEAD, changes silently.
- ``tag``      -- ``@v4``, ``@v9.15.2``: mutable, and major tags move by design.
- ``bare``     -- no ``@`` at all: resolves to the default branch.

A local action (``./.github/actions/x``) is not third-party and is not reported.
A reusable workflow in our own organisation is still reported: the same
mutability argument applies, and we can pin our own SHAs.

WHY A BASELINE, AND NOT A DAILY COUNT
-------------------------------------
There are around 112 unpinned references today across roughly 19 repositories.
A job that reports all of them every week is the muted-alert failure this
repository already warns about in ``sweep_default_branch_ci.py``: "a daily issue
that cries wolf gets muted, and a muted alert is worse than none".

So the reviewed backlog lives in ``action-pin-baseline.json`` and the sweep
alerts only on what is NOT in it -- a NEW unpinned action, or one that moved to
a worse tier. The backlog is counted in the body but never raises the alarm, so
the number falls as people choose to work on it rather than because a bot
nagged. Regenerate the baseline deliberately, and review the diff::

    python scripts/sweep_action_pins.py --write-baseline

That mirrors ``public-artifacts.json`` in openadapt-flow: a reviewed inventory
that validation never regenerates on its own.

REPOSITORY LIST
---------------
The live organisation listing, not ``repos.yml`` -- the same choice
``sweep_default_branch_ci.py`` makes and for the same reason. ``repos.yml`` is
the docs-site registry and deliberately omits internal tooling; a sweep built on
it would have missed openadapt-consilium and openadapt-viewer, both of which
needed this exact fix in 2026-08. Archived repositories are excluded (frozen,
cannot be repaired) and so are forks ("write access is not authority").

PERMISSIONS
-----------
A public repository's contents API is readable with no authentication, so the
default repository-scoped ``GITHUB_TOKEN`` reads every public repository we own
and needs no new secret. A private repository never appears in the listing that
token sees, so the report says which half of the organisation it looked at
rather than quietly understating the count.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ORG = "OpenAdaptAI"
API = "https://api.github.com"
ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "action-pin-baseline.json"
SCHEMA_VERSION = 1

SHA = re.compile(r"\A[0-9a-f]{40}\Z")
# `uses:` at any indentation, with or without a leading list dash. Stops at
# whitespace or a trailing comment so `@sha # v1.2.3` yields the sha.
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*[\"']?([^\s\"'#]+)")
BRANCHY = {"master", "main", "trunk", "develop", "dev", "latest", "HEAD"}

BRANCH, TAG, BARE = "branch", "tag", "bare"
TIER_RANK = {BARE: 0, TAG: 1, BRANCH: 2}
TIER_NOTE = {
    BRANCH: "tracks the upstream default branch, so it changes with no commit here",
    TAG: "a tag is mutable by the upstream owner; a major tag moves by design",
    BARE: "no ref at all, so it resolves to the upstream default branch",
}


class Reader:
    """Minimal GitHub reader. Standard library only, so the job needs no install."""

    def __init__(self, token: str | None) -> None:
        self.token = token

    def get(self, path: str, raw: bool = False):
        request = urllib.request.Request(f"{API}/{path}")
        request.add_header("Accept", "application/vnd.github.raw" if raw else "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            if error.code in (403, 404):
                return None
            raise
        return payload if raw else json.loads(payload)


def classify(ref: str) -> tuple[str, str] | None:
    """Return ``(tier, action)`` for a reference that is not commit-pinned."""
    if ref.startswith(".") or ref.startswith("/"):
        return None  # a local action in this repository
    if ref.startswith("docker://"):
        return None  # a container reference; digest policy is a separate question
    if "@" not in ref:
        return BARE, ref
    action, _, at = ref.rpartition("@")
    if SHA.fullmatch(at):
        return None
    return (BRANCH if at in BRANCHY else TAG), action


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
        (r for r in found if not r.get("archived") and not r.get("fork")),
        key=lambda r: r["name"].lower(),
    )


def sweep_repository(reader: Reader, repo: dict) -> list[dict]:
    slug = repo["full_name"]
    listing = reader.get(f"repos/{slug}/contents/.github/workflows")
    if not listing:
        return []
    findings: list[dict] = []
    for entry in listing:
        name = entry.get("name", "")
        if not name.endswith((".yml", ".yaml")):
            continue
        body = reader.get(f"repos/{slug}/contents/.github/workflows/{name}", raw=True)
        if body is None:
            continue
        for number, line in enumerate(body.splitlines(), 1):
            match = USES.match(line)
            if not match:
                continue
            verdict = classify(match.group(1))
            if verdict is None:
                continue
            tier, action = verdict
            findings.append(
                {
                    "repo": repo["name"],
                    "workflow": name,
                    "line": number,
                    "ref": match.group(1),
                    "action": action,
                    "tier": tier,
                }
            )
    return findings


def key(finding: dict) -> str:
    """Identity of a finding for baseline comparison.

    Deliberately excludes the line number: moving a step within a file is not a
    new risk, and a line-sensitive baseline would churn on every unrelated edit.
    """
    return f"{finding['repo']}|{finding['workflow']}|{finding['ref']}"


def load_baseline() -> dict[str, str]:
    if not BASELINE_PATH.exists():
        return {}
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(
            f"{BASELINE_PATH.name}: unsupported schema_version "
            f"{payload.get('schema_version')!r}; expected {SCHEMA_VERSION}"
        )
    return {row["id"]: row["tier"] for row in payload.get("accepted", [])}


def worst_tier_per_identity(findings: list[dict]) -> dict[str, str]:
    """Collapse findings to one row per identity, keeping the worst tier.

    One workflow file commonly uses ``actions/checkout@v4`` in several jobs.
    Those are the same decision, not several, and ``key()`` deliberately ignores
    the line number -- so the baseline carries one row for them. Without this the
    file grew 112 rows for 93 decisions, and ``load_baseline`` silently collapsed
    the duplicates anyway, which made the committed file disagree with the file
    the validator actually used.
    """
    worst: dict[str, str] = {}
    for finding in findings:
        identity = key(finding)
        if identity not in worst or TIER_RANK[finding["tier"]] > TIER_RANK[worst[identity]]:
            worst[identity] = finding["tier"]
    return worst


def write_baseline(findings: list[dict]) -> Path:
    """Explicitly regenerate the reviewed backlog. Validation never calls this."""
    BASELINE_PATH.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "note": (
                    "Reviewed backlog of GitHub Actions that are not pinned to a commit "
                    "SHA. The sweep alerts on anything absent from this file, so adding "
                    "a row here is an explicit decision to accept that reference for now. "
                    "Regenerate with: python scripts/sweep_action_pins.py --write-baseline"
                ),
                "accepted": [
                    {"id": identity, "tier": tier}
                    for identity, tier in sorted(worst_tier_per_identity(findings).items())
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return BASELINE_PATH


def regressions(findings: list[dict], baseline: dict[str, str]) -> list[dict]:
    """Findings that are new, or that moved to a worse tier than was accepted."""
    out = []
    for finding in findings:
        accepted = baseline.get(key(finding))
        if accepted is None:
            out.append({**finding, "why": "not in the reviewed backlog"})
        elif TIER_RANK[finding["tier"]] > TIER_RANK.get(accepted, 0):
            out.append({**finding, "why": f"worse than the accepted `{accepted}`"})
    return out


def render(findings, new, repos, private_seen, run_url) -> str:
    lines = ["# Actions that are not pinned to a commit", ""]
    if new:
        lines += [
            f"**{len(new)} reference(s) need attention.** Each one is new, or worse "
            "than what the reviewed backlog accepted.",
            "",
            "| repository | workflow | line | reference | why |",
            "| --- | --- | --- | --- | --- |",
        ]
        for f in sorted(new, key=key):
            lines.append(
                f"| `{f['repo']}` | `{f['workflow']}` | {f['line']} | "
                f"`{f['ref']}` | {f['why']} ({TIER_NOTE[f['tier']]}) |"
            )
        lines += [
            "",
            "Pin each one to a full 40-character commit SHA, with the version in a "
            "trailing comment:",
            "",
            "```yaml",
            "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
            "```",
            "",
            "If a reference is deliberate for now, accept it explicitly:",
            "",
            "```bash",
            "python scripts/sweep_action_pins.py --write-baseline",
            "```",
            "",
        ]
    backlog = len(findings) - len(new)
    lines += [
        "## Coverage",
        "",
        f"- Repositories read: **{repos}** (non-archived, non-fork).",
        f"- Unpinned references in total: **{len(findings)}**.",
        f"- Already in the reviewed backlog: **{backlog}** (not alerted on).",
    ]
    if not private_seen:
        lines.append(
            "- Private repositories were **not** visible to this token, so this "
            "covers the public half of the organisation only."
        )
    if run_url:
        lines += ["", f"Produced by {run_url}."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", help="write the issue body to this file")
    parser.add_argument("--github-output", help="append alert= and clear= to this file")
    parser.add_argument("--run-url", default="", help="link back to the run")
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="regenerate the reviewed backlog, then exit without alerting",
    )
    args = parser.parse_args(argv)

    reader = Reader(os.environ.get("OA_SWEEP_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    repositories = owned_repositories(reader)
    if not repositories:
        print("The organisation listing came back empty; refusing to report an all-clear.", file=sys.stderr)
        return 2

    findings: list[dict] = []
    for repo in repositories:
        findings.extend(sweep_repository(reader, repo))

    if args.write_baseline:
        path = write_baseline(findings)
        unique = len(worst_tier_per_identity(findings))
        print(f"Wrote {unique} accepted decision(s) covering {len(findings)} reference(s) to {path}.")
        print("Review the diff before you commit it.")
        return 0

    new = regressions(findings, load_baseline())
    body = render(
        findings,
        new,
        len(repositories),
        any(r.get("private") for r in repositories),
        args.run_url,
    )
    if args.markdown:
        Path(args.markdown).write_text(body, encoding="utf-8")
    else:
        print(body, end="")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"alert={'true' if new else 'false'}\n")
            handle.write(f"clear={'false' if new else 'true'}\n")
    print(
        f"{len(repositories)} repositories, {len(findings)} unpinned, {len(new)} needing attention.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
