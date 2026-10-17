"""Every docs.openadapt.ai URL that other places link to still resolves.

tests/fixtures/inbound_docs_urls.json lists the URLs found in PyPI package
descriptions, organization READMEs and package metadata, the website source,
and the live sitemap. Each one must reach a page, either directly or through a
redirect in mkdocs.yml. A URL with an #anchor must land on a heading or an
element with that id, so the link opens at the right place.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FIXTURE = ROOT / "tests" / "fixtures" / "inbound_docs_urls.json"
# Files MkDocs writes itself rather than copying from docs/.
GENERATED = {"sitemap.xml", "sitemap.xml.gz", "search/search_index.json", "404.html"}


def _redirect_map() -> dict[str, str]:
    config = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and "redirects" in plugin:
            return plugin["redirects"]["redirect_maps"]
    raise AssertionError("mkdocs.yml has no redirects plugin")


def _candidates(path: str) -> list[str]:
    """Return the docs/ source files that MkDocs would serve at this URL path."""
    rel = path.strip("/")
    if not rel:
        return ["index.md"]
    if "." in rel.rsplit("/", 1)[-1]:
        return [rel]
    return [f"{rel}.md", f"{rel}/index.md", f"{rel}/README.md"]


def _slug(text: str) -> str:
    text = re.sub(r"<[^>]+>|`|\*|\[|\]\([^)]*\)", "", text)
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s]+", "-", text)


def _ids(page: Path) -> set[str]:
    ids: set[str] = set()
    in_fence = False
    for line in page.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = re.match(r"#{1,6}\s+(.*?)\s*(\{[^}]*\})?\s*$", line)
        if heading:
            attrs = heading.group(2) or ""
            explicit = re.search(r"#([\w-]+)", attrs)
            ids.add(explicit.group(1) if explicit else _slug(heading.group(1)))
        ids.update(re.findall(r'\bid="([\w-]+)"', line))
    return ids


def _resolve(url: str) -> tuple[Path | None, str]:
    """Return (final docs file, anchor) for an inbound URL, or (None, reason)."""
    path, _, anchor = url.partition("#")
    redirects = _redirect_map()
    for candidate in _candidates(path):
        if candidate in GENERATED:
            return DOCS, anchor
        if (DOCS / candidate).is_file():
            return DOCS / candidate, anchor
        if candidate in redirects:
            target, _, target_anchor = redirects[candidate].partition("#")
            if target_anchor and anchor:
                return None, f"{url}: the redirect target already has #{target_anchor}"
            return DOCS / target, anchor or target_anchor
    return None, f"{url}: no page and no redirect"


def _entries() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["urls"]


def _urls(*, anchors: bool = False) -> list[str]:
    skip = "skip_anchor" if anchors else "skip"
    return [
        entry["url"] for entry in _entries() if "skip" not in entry and skip not in entry
    ]


def test_skips_are_rare_and_explained() -> None:
    skipped = [e for e in _entries() if "skip" in e or "skip_anchor" in e]
    assert len(skipped) <= 3
    for entry in skipped:
        assert len(entry.get("skip") or entry.get("skip_anchor")) > 40, entry["url"]


def test_the_fixture_covers_the_old_sections() -> None:
    # Guards the test below against passing on a shrunken list.
    urls = _urls()
    assert len(urls) >= 90
    for section in ("/commercial/", "/concepts/", "/evaluate/", "/guides/", "/get-started/"):
        assert any(url.startswith(section) for url in urls), section


def test_every_inbound_url_resolves() -> None:
    problems = []
    for url in _urls():
        page, detail = _resolve(url)
        if page is None:
            problems.append(detail)
        elif page != DOCS and not page.is_file():
            problems.append(f"{url}: redirects to missing {page.relative_to(DOCS)}")
    assert problems == []


def test_every_inbound_anchor_lands_on_an_id() -> None:
    problems = []
    for url in _urls(anchors=True):
        page, anchor = _resolve(url)
        if page is None or page == DOCS or not anchor or not page.is_file():
            continue
        if anchor not in _ids(page):
            problems.append(f"{url}: no #{anchor} on {page.relative_to(DOCS)}")
    assert problems == []
