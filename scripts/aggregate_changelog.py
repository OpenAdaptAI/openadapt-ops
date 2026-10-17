"""Aggregate CHANGELOGs from all repos into a unified changelog page."""

import os
import pathlib
import re

import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS_YML = ROOT / "repos.yml"
DOCS_DIR = ROOT / "docs"

GITHUB_API = "https://api.github.com"


def load_repos(path=REPOS_YML):
    with open(path) as f:
        return [r for r in yaml.safe_load(f)["repos"] if r.get("changelog")]


def fetch_releases(github_slug, per_page=5):
    """Fetch recent releases from GitHub API."""
    url = f"{GITHUB_API}/repos/{github_slug}/releases?per_page={per_page}"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(
            f"GitHub releases request failed for {github_slug}: HTTP "
            f"{resp.status_code}. Refusing to replace the changelog with an "
            "empty generated page."
        )
    return [
        {"tag": r["tag_name"], "date": r["published_at"][:10],
         "url": r["html_url"], "body": (r.get("body") or "").strip()[:400]}
        for r in resp.json() if not r.get("draft")
    ]


# A release heading in a package CHANGELOG.md, as python-semantic-release
# writes it: "## v2.1.0 (2026-10-16)".
CHANGELOG_HEADING = re.compile(
    r"^## (?P<tag>v\d+\.\d+\.\d+\S*) \((?P<date>\d{4}-\d{2}-\d{2})\)\s*$"
)


def _github_anchor(heading):
    """The anchor GitHub gives a Markdown heading."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def fetch_changelog_file(github_slug, path, ref="main", limit=5):
    """Read release entries from a CHANGELOG.md in a repository.

    Packages in the OpenAdapt monorepo publish to PyPI without a GitHub
    release, so their release history is the package's CHANGELOG.md, not the
    repository's releases feed (which belongs to the root launcher).
    """
    url = f"{GITHUB_API}/repos/{github_slug}/contents/{path}?ref={ref}"
    headers = {"Accept": "application/vnd.github.raw+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(
            f"GitHub contents request failed for {github_slug}/{path}: HTTP "
            f"{resp.status_code}. Refusing to replace the changelog with an "
            "empty generated page."
        )
    releases = []
    current = None
    for line in resp.text.splitlines():
        match = CHANGELOG_HEADING.match(line)
        if match:
            if len(releases) == limit:
                break
            heading = line[3:]
            current = {
                "tag": match["tag"],
                "date": match["date"],
                "url": f"https://github.com/{github_slug}/blob/{ref}/{path}"
                f"#{_github_anchor(heading)}",
                "lines": [],
            }
            releases.append(current)
        elif line.startswith("## "):
            current = None
        elif current is not None and not line.startswith("#"):
            # Section headings ("### Features") say nothing about what
            # shipped; keep the notes under them, without the list marker.
            current["lines"].append(line[2:] if line.startswith("- ") else line)
    return [
        {
            "tag": r["tag"],
            "date": r["date"],
            "url": r["url"],
            "body": "\n".join(r["lines"]).strip()[:400],
        }
        for r in releases
    ]


def fetch_repo_releases(repo):
    """Release entries for one repos.yml entry, from its configured source."""
    if repo.get("changelog_file"):
        return fetch_changelog_file(repo["github"], repo["changelog_file"])
    return fetch_releases(repo["github"])


# Boilerplate that python-semantic-release puts at the top of every release
# body. It is identical in every release of every repository, so surfacing it
# as a release's summary says nothing about what shipped -- openadapt-flow
# v1.24.0 reached the published changelog carrying only this line, with its
# actual "Bug Fixes" content dropped. Match on the licence sentence rather than
# on italics generally, so a genuinely informative emphasised line survives.
BOILERPLATE_MARKERS = ("this release is published under the",)


def _is_boilerplate(text):
    """True when a line is per-release legal boilerplate, not release notes."""
    stripped = text.strip().strip("_*").strip().lower()
    return any(stripped.startswith(marker) for marker in BOILERPLATE_MARKERS)


def summarize_body(body, tag=""):
    """Return a one-line, heading-free summary of a release body.

    GitHub release bodies frequently open with a heading that only restates the
    version (for example ``## v1.7.1 (2026-07-19)``). Injected verbatim, that
    line duplicates the tag we already print and its leading ``#`` corrupts the
    changelog page's heading hierarchy. Skip such redundant leading headings,
    skip the identical licence boilerplate every release carries, and return the
    first real line of notes as inline (heading-free) text. Returns an empty
    string when the body carries no notes beyond those.
    """
    tag_norm = tag.lstrip("vV").strip()
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        text = line.lstrip("#").strip()
        if not text:
            continue
        if _is_boilerplate(text):
            continue
        if line.startswith("#"):
            heading = text.lstrip("vV").strip()
            # A leading heading that merely restates the version is noise.
            if tag and (tag in text or (tag_norm and heading.startswith(tag_norm))):
                continue
        return text
    return ""


def aggregate(repos=None, docs_dir=None):
    repos = repos or load_repos()
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)

    lines = [
        "# Changelog\n",
        "> Release history across the OpenAdapt product repositories.\n",
    ]
    for repo in repos:
        releases = fetch_repo_releases(repo)
        if not releases:
            continue
        lines.append(f"\n## {repo['name']}\n")
        for r in releases:
            lines.append(f"- **[{r['tag']}]({r['url']})** ({r['date']})")
            summary = summarize_body(r["body"], r["tag"])
            if summary:
                lines.append(f"  {summary}")

    out_path = docs_dir / "changelog.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path} ({len(lines)} lines)")
    return str(out_path)


if __name__ == "__main__":
    aggregate()
