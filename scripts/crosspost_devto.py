#!/usr/bin/env python3
"""Cross-post OpenAdapt blog posts to dev.to with canonical URLs.

Reads the blog RSS feed and creates one dev.to article per post that does not
already exist there. Every created article sets ``canonical_url`` to the
original blog post URL, so search engines keep ranking the blog as the
canonical source.

The feed URL is verified against the Hugo configuration of the blog
(``hugo.toml`` points its RSS menu entry at ``/index.xml``); ``/feed.xml`` is
not served.

Dry-run mode is ON by default and prints what would be posted without touching
the API. Pass ``--apply`` to create articles. Idempotency comes from listing
the authenticated account's existing articles and skipping any whose
``canonical_url`` already matches a feed post.

The API key is read from the ``DEVTO_API_KEY`` environment variable and is
never written to disk or logs. Dependencies: standard library plus httpx.

Usage:
    python scripts/crosspost_devto.py                  # dry run (default)
    DEVTO_API_KEY=... python scripts/crosspost_devto.py --apply
    python scripts/crosspost_devto.py --feed tests/fixtures/sample_feed.xml
"""

from __future__ import annotations

import argparse
import html
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import httpx

DEVTO_API = "https://dev.to/api"
DEFAULT_FEED_URL = "https://blog.openadapt.ai/index.xml"
BLOG_HOME = "https://blog.openadapt.ai"
HTTP_TIMEOUT = 30.0
PER_PAGE = 1000  # dev.to maximum for /api/articles/me/all


def load_feed(source: str) -> str:
    """Return the raw RSS/XML text for a URL or local file path."""
    if re.match(r"^https?://", source):
        response = httpx.get(source, timeout=HTTP_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
        return response.text
    return pathlib.Path(source).read_text(encoding="utf-8")


def parse_feed(xml_text: str) -> list[dict]:
    """Parse RSS 2.0 items into ordered post dicts (oldest last)."""
    root = ET.fromstring(xml_text)
    posts = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        description = _strip_html(item.findtext("description") or "")
        posts.append(
            {
                "title": title,
                "url": link,
                "pub_date": (item.findtext("pubDate") or "").strip(),
                "description": html.unescape(description),
            }
        )
    return posts


def _strip_html(text: str) -> str:
    """Collapse markup to plain text for use inside a markdown quote."""
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", without_tags).strip()


def build_article(post: dict) -> dict:
    """Build the dev.to POST /api/articles JSON payload for one post."""
    lines = []
    if post["description"]:
        lines.append(f"> {post['description']}")
        lines.append("")
    lines.append(
        f"Read the full post on the [OpenAdapt blog]({post['url']})."
    )
    article = {
        "title": post["title"],
        "published": True,
        "body_markdown": "\n".join(lines),
        "canonical_url": post["url"],
    }
    return {"article": article}


def fetch_existing_canonical_urls(api_key: str) -> set[str]:
    """Return every canonical_url on the authenticated dev.to account."""
    urls: set[str] = set()
    with httpx.Client(
        base_url=DEVTO_API,
        headers={"api-key": api_key},
        timeout=HTTP_TIMEOUT,
    ) as client:
        page = 1
        while True:
            response = client.get(
                "/articles/me/all",
                params={"per_page": PER_PAGE, "page": page},
            )
            response.raise_for_status()
            batch = response.json()
            for article in batch:
                canonical = article.get("canonical_url")
                if canonical:
                    urls.add(canonical)
            if len(batch) < PER_PAGE:
                return urls
            page += 1


def create_article(api_key: str, payload: dict) -> dict:
    """POST one article to dev.to and return the created article."""
    response = httpx.post(
        f"{DEVTO_API}/articles",
        json=payload,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def plan(posts: list[dict], existing: set[str]) -> list[dict]:
    """Return posts that are not yet on dev.to, preserving feed order."""
    return [post for post in posts if post["url"] not in existing]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cross-post blog RSS entries to dev.to "
        "(dry-run by default).",
    )
    parser.add_argument(
        "--feed",
        default=DEFAULT_FEED_URL,
        help=f"Feed URL or local XML path (default: {DEFAULT_FEED_URL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Post at most N articles with --apply (0 means no limit)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing articles. Without this flag nothing is posted.",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("DEVTO_API_KEY", "")
    if args.apply and not api_key:
        print(
            "Error: --apply requires the DEVTO_API_KEY environment variable.",
            file=sys.stderr,
        )
        return 2

    posts = parse_feed(load_feed(args.feed))
    print(f"Feed {args.feed}: {len(posts)} post(s).")

    existing: set[str] = set()
    if api_key:
        existing = fetch_existing_canonical_urls(api_key)
        print(f"dev.to account already has {len(existing)} canonical URL(s).")
    elif not args.apply:
        print(
            "DEVTO_API_KEY is unset: printing the full feed without an "
            "idempotency check."
        )

    missing = plan(posts, existing)
    skipped = len(posts) - len(missing)
    if skipped:
        print(f"Skipping {skipped} already-cross-posted article(s).")
    if not missing:
        print("Nothing to do: the blog and dev.to are in sync.")
        return 0

    for index, post in enumerate(missing):
        if args.limit and index >= args.limit:
            print(f"--limit {args.limit} reached; stopping.")
            break
        payload = build_article(post)
        if args.apply:
            created = create_article(api_key, payload)
            print(f"Created: {created.get('url')} <- {post['url']}")
        else:
            print(f"[dry-run] would post title={post['title']!r}")
            print(f"[dry-run]   canonical_url={post['url']}")
            print(f"[dry-run]   body_markdown={payload['article']['body_markdown']!r}")
    if not args.apply:
        print("Dry run only. Re-run with --apply and DEVTO_API_KEY to post.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
