"""Tests for crosspost_devto.py (offline; no network calls)."""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import crosspost_devto
from crosspost_devto import (
    build_article,
    fetch_existing_canonical_urls,
    load_feed,
    main,
    parse_feed,
    plan,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture()
def posts():
    return parse_feed((FIXTURES / "sample_feed.xml").read_text(encoding="utf-8"))


def test_parse_feed_extracts_items(posts):
    assert [p["title"] for p in posts] == [
        "The write audit",
        "Compile once, govern every repair & stay safe",
    ]
    assert posts[0]["url"] == "https://blog.openadapt.ai/posts/the-write-audit/"
    assert posts[0]["pub_date"].startswith("Mon, 27 Jul 2026")


def test_parse_feed_strips_html_entities(posts):
    assert "<p>" not in posts[1]["description"]
    assert posts[1]["description"].startswith("Compile one demonstration")


def test_load_feed_reads_local_file():
    text = load_feed(str(FIXTURES / "sample_feed.xml"))
    assert "<rss" in text


def test_build_article_sets_canonical_url_and_teaser(posts):
    payload = build_article(posts[0])
    article = payload["article"]
    assert article["canonical_url"] == posts[0]["url"]
    assert article["published"] is True
    assert article["title"] == posts[0]["title"]
    assert posts[0]["url"] in article["body_markdown"]
    assert article["body_markdown"].startswith(
        f"> {posts[0]['description']}"
    )


def test_plan_skips_existing_canonical_urls(posts):
    existing = {posts[1]["url"]}
    remaining = plan(posts, existing)
    assert [p["url"] for p in remaining] == [posts[0]["url"]]
    assert plan(posts, set()) == posts


def test_fetch_existing_canonical_urls_paginates(mocker):
    pages = [
        [{"canonical_url": "https://a/1"}, {"canonical_url": None}],
        [{"canonical_url": "https://a/2"}],
    ]
    requests_seen = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, path, params=None):
            requests_seen.append((path, params))
            response = mocker.Mock(status_code=200)
            response.json.return_value = pages[self.calls]
            self.calls += 1
            return response

    mocker.patch.object(crosspost_devto.httpx, "Client", FakeClient)
    mocker.patch.object(crosspost_devto, "PER_PAGE", 2)
    urls = fetch_existing_canonical_urls("test-key")
    assert urls == {"https://a/1", "https://a/2"}
    assert [params["page"] for _, params in requests_seen] == [1, 2]


def test_main_dry_run_is_default_and_needs_no_key(mocker, posts, capsys):
    mocker.patch.object(
        crosspost_devto, "load_feed",
        return_value=(FIXTURES / "sample_feed.xml").read_text(),
    )
    post_spy = mocker.patch.object(crosspost_devto.httpx, "post")
    exit_code = main(["--feed", "fixture.xml"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "[dry-run]" in output
    assert posts[0]["url"] in output
    post_spy.assert_not_called()


def test_main_apply_requires_api_key(mocker):
    mocker.patch.dict("os.environ", {}, clear=True)
    mocker.patch.object(
        crosspost_devto, "load_feed", return_value="<rss></rss>",
    )
    assert main(["--apply"]) == 2


def test_main_apply_creates_only_missing_articles(mocker, posts, monkeypatch):
    monkeypatch.setenv("DEVTO_API_KEY", "test-key")
    mocker.patch.object(
        crosspost_devto, "load_feed",
        return_value=(FIXTURES / "sample_feed.xml").read_text(),
    )
    mocker.patch.object(
        crosspost_devto, "fetch_existing_canonical_urls",
        return_value={posts[1]["url"]},
    )
    created = []

    def fake_create(api_key, payload):
        created.append(payload)
        return {"url": "https://dev.to/openadapt/new"}

    mocker.patch.object(crosspost_devto, "create_article", side_effect=fake_create)
    exit_code = main(["--feed", "fixture.xml", "--apply"])
    assert exit_code == 0
    assert len(created) == 1
    assert created[0]["article"]["canonical_url"] == posts[0]["url"]
