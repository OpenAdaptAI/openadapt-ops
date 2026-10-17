"""The sitemap lists only pages a search engine may index.

Old URLs redirect through the mkdocs-redirects `redirect_maps` in mkdocs.yml
(and any page with `redirect_to` in its front matter is a stub that
overrides/main.html refreshes away). Neither kind of redirect may appear in
the sitemap: an earlier layout listed 30 redirect stubs among 104 URLs.
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


def _url_for(rel: Path) -> str:
    rel = rel.with_suffix("")
    parts = rel.parts[:-1] if rel.name in ("index", "README") else rel.parts
    return SITE_URL + "".join(f"{part}/" for part in parts)


def _redirect_map() -> dict[str, str]:
    config = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and "redirects" in plugin:
            return plugin["redirects"]["redirect_maps"]
    return {}


def _redirect_stub_urls() -> set[str]:
    urls = {_url_for(Path(old)) for old in _redirect_map()}
    for page in DOCS.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        front = yaml.safe_load(text.split("---\n", 2)[1]) or {}
        if front.get("redirect_to"):
            urls.add(_url_for(page.relative_to(DOCS)))
    return urls


def test_redirect_sources_are_not_also_pages() -> None:
    clashes = sorted(old for old in _redirect_map() if (DOCS / old).exists())
    assert clashes == []


def test_redirect_targets_exist() -> None:
    missing = sorted(
        f"{old} -> {new}"
        for old, new in _redirect_map().items()
        if not (DOCS / new.split("#", 1)[0]).is_file()
    )
    assert missing == []


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


def test_the_repository_still_has_redirects() -> None:
    # Guards the test below against passing only because the redirects are gone.
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
