"""The sitemap lists only pages a search engine may index.

A page with `redirect_to` in its front matter is a stub: overrides/main.html
gives it a 0-second refresh and `noindex`. MkDocs' default sitemap lists every
built page, so 30 of its 104 URLs told crawlers to index pages that tell
crawlers not to index them.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE_URL = yaml.load(
    (ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
)["site_url"].rstrip("/") + "/"


def _redirect_stub_urls() -> set[str]:
    urls = set()
    for page in DOCS.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        front = yaml.safe_load(text.split("---\n", 2)[1]) or {}
        if not front.get("redirect_to"):
            continue
        rel = page.relative_to(DOCS).with_suffix("")
        parts = rel.parts[:-1] if rel.name in ("index", "README") else rel.parts
        urls.add(SITE_URL + "".join(f"{part}/" for part in parts))
    return urls


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--quiet", "--site-dir", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return out


def _sitemap_urls(site: Path) -> list[str]:
    return re.findall(r"<loc>([^<]+)</loc>", (site / "sitemap.xml").read_text("utf-8"))


def test_the_repository_still_has_redirect_stubs() -> None:
    # Guards the test below against passing only because the stubs are gone.
    assert len(_redirect_stub_urls()) >= 20


def test_the_sitemap_omits_every_redirect_stub(site: Path) -> None:
    listed = set(_sitemap_urls(site))
    assert listed
    assert sorted(listed & _redirect_stub_urls()) == []


def test_every_sitemap_url_is_an_indexable_page(site: Path) -> None:
    offenders = []
    for url in _sitemap_urls(site):
        assert url.startswith(SITE_URL), url
        path = url[len(SITE_URL):]
        page = site / path / "index.html" if path.endswith("/") or not path else site / path
        html = page.read_text(encoding="utf-8")
        if 'name="robots" content="noindex' in html or 'http-equiv="refresh"' in html:
            offenders.append(url)
    assert offenders == []
