#!/usr/bin/env python3
"""Produce the weekly growth-metrics report as markdown.

Collects, for a fixed ISO week label:

1. GitHub stars and forks for the flagship repos (public GitHub API).
2. Hacker News Algolia hits for "OpenAdapt" with summed points and comments.
3. PyPI downloads over the last 7 days (pypistats.org recent endpoint) for
   ``openadapt`` and ``openadapt-flow``.
4. Blog post count from the blog sitemap (individual /posts/<slug>/ URLs).

Writes ``growth-metrics-YYYY-WW.md`` into ``reports/`` (created on demand and
gitignored). The table layout is deterministic: fixed row order, fixed column
order, no wall-clock timestamps inside the report body.

Dependencies: standard library plus httpx. No API keys are required; if
``GH_TOKEN`` or ``GITHUB_TOKEN`` is set it is attached to GitHub requests to
raise the public rate limit, and is never logged.

Suggested schedule: run once per week, e.g. Mondays 09:00 UTC in the same cron
slot as the docs content sync:

    0 9 * * 1  cd <repo> && uv run python scripts/metrics_weekly.py

Usage:
    python scripts/metrics_weekly.py                 # current ISO week
    python scripts/metrics_weekly.py --week 2026-W34
    python scripts/metrics_weekly.py --output-dir reports
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import httpx

GITHUB_API = "https://api.github.com"
HN_ALGOLIA = "https://hn.algolia.com/api/v1/search"
PYPISTATS = "https://pypistats.org/api/packages/{package}/recent"
BLOG_SITEMAP = "https://blog.openadapt.ai/sitemap.xml"

GITHUB_REPOS = (
    "OpenAdaptAI/OpenAdapt",
    "OpenAdaptAI/openadapt-flow",
    "OpenAdaptAI/openadapt-capture",
)
PYPI_PACKAGES = ("openadapt", "openadapt-flow")

HTTP_TIMEOUT = 30.0


def _get_json(url: str, params: dict | None = None) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(GITHUB_API):
        headers["Authorization"] = f"Bearer {token}"
    response = httpx.get(
        url, params=params, headers=headers, timeout=HTTP_TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.json()


def fetch_github_repo(slug: str) -> dict:
    """Stars and forks for one repository via the public GitHub API."""
    data = _get_json(f"{GITHUB_API}/repos/{slug}")
    return {"stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0)}


def fetch_hn_openadapt() -> dict:
    """HN Algolia story hits for OpenAdapt with summed points and comments."""
    data = _get_json(HN_ALGOLIA, params={"query": "OpenAdapt",
                                         "tags": "story",
                                         "hitsPerPage": 100})
    hits = data.get("hits") or []
    points = sum(h.get("points") or 0 for h in hits)
    comments = sum(h.get("num_comments") or 0 for h in hits)
    return {"hits": data.get("nbHits", len(hits)),
            "points": points,
            "comments": comments}


def fetch_pypi_downloads(package: str) -> int:
    """Downloads over the last week from pypistats.org (no key required)."""
    data = _get_json(PYPISTATS.format(package=package))
    return data.get("data", {}).get("last_week", 0)


def fetch_blog_post_count(sitemap_url: str = BLOG_SITEMAP) -> int:
    """Count individual post URLs in the blog sitemap.

    The sitemap also lists index pages (/posts/, /archive/) and tag pages;
    only URLs of the shape /posts/<slug>/ are posts.
    """
    response = httpx.get(sitemap_url, timeout=HTTP_TIMEOUT,
                         follow_redirects=True)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    count = 0
    for loc in root.findall(".//sm:url/sm:loc", namespace):
        text = (loc.text or "").strip()
        if re.match(r"^https?://[^/]+/posts/.+/$", text):
            count += 1
    return count


def collect_metrics() -> dict:
    """Gather every metric into one deterministic dictionary."""
    metrics: dict = {}
    for slug in GITHUB_REPOS:
        try:
            metrics[f"github:{slug}"] = fetch_github_repo(slug)
        except httpx.HTTPError as exc:
            print(f"warning: GitHub request failed for {slug}: {exc}",
                  file=sys.stderr)
            metrics[f"github:{slug}"] = None

    try:
        metrics["hn"] = fetch_hn_openadapt()
    except httpx.HTTPError as exc:
        print(f"warning: HN Algolia request failed: {exc}", file=sys.stderr)
        metrics["hn"] = None

    for package in PYPI_PACKAGES:
        try:
            metrics[f"pypi:{package}"] = fetch_pypi_downloads(package)
        except httpx.HTTPError as exc:
            print(f"warning: pypistats request failed for {package}: {exc}",
                  file=sys.stderr)
            metrics[f"pypi:{package}"] = None

    try:
        metrics["blog_posts"] = fetch_blog_post_count()
    except httpx.HTTPError as exc:
        print(f"warning: sitemap request failed: {exc}", file=sys.stderr)
        metrics["blog_posts"] = None
    return metrics


def render_report(metrics: dict, week_label: str) -> str:
    """Render the fixed-layout markdown report for one ISO week."""
    lines = [
        f"# Growth metrics — {week_label}",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for slug in GITHUB_REPOS:
        entry = metrics.get(f"github:{slug}")
        stars = "n/a" if entry is None else str(entry["stars"])
        forks = "n/a" if entry is None else str(entry["forks"])
        lines.append(f"| GitHub stars — {slug} | {stars} |")
        lines.append(f"| GitHub forks — {slug} | {forks} |")

    hn = metrics.get("hn")
    hn_hits = "n/a" if hn is None else str(hn["hits"])
    hn_points = "n/a" if hn is None else str(hn["points"])
    hn_comments = "n/a" if hn is None else str(hn["comments"])
    lines.append(f"| Hacker News hits (stories mentioning OpenAdapt) "
                 f"| {hn_hits} |")
    lines.append(f"| Hacker News points (summed) | {hn_points} |")
    lines.append(f"| Hacker News comments (summed) | {hn_comments} |")

    for package in PYPI_PACKAGES:
        downloads = metrics.get(f"pypi:{package}")
        value = "n/a" if downloads is None else f"{downloads:,}"
        lines.append(f"| PyPI downloads last 7d — {package} | {value} |")

    blog_posts = metrics.get("blog_posts")
    value = "n/a" if blog_posts is None else str(blog_posts)
    lines.append(f"| Blog posts (sitemap) | {value} |")

    return "\n".join(lines) + "\n"


def default_week_label(today: datetime.date | None = None) -> str:
    """ISO week label like 2026-W34 for the given date (default: today)."""
    day = today or datetime.date.today()
    iso_year, iso_week, _ = day.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write growth-metrics-YYYY-WW.md into reports/.",
    )
    parser.add_argument(
        "--week",
        default=None,
        help="ISO week label such as 2026-W34 (default: the current week)",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for the report file (default: reports/)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the report instead of writing a file",
    )
    args = parser.parse_args(argv)

    week_label = args.week or default_week_label()
    metrics = collect_metrics()
    report = render_report(metrics, week_label)

    if args.stdout:
        print(report, end="")
        return 0

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"growth-metrics-{week_label}.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
