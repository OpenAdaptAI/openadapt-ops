"""Tests for metrics_weekly.py (offline; all HTTP mocked)."""

import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from metrics_weekly import (
    BLOG_SITEMAP,
    collect_metrics,
    default_week_label,
    fetch_blog_post_count,
    render_report,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

SAMPLE_SITEMAP = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://blog.openadapt.ai/posts/the-write-audit/</loc></url>
  <url><loc>https://blog.openadapt.ai/posts/other-post/</loc></url>
  <url><loc>https://blog.openadapt.ai/posts/</loc></url>
  <url><loc>https://blog.openadapt.ai/tags/agents/</loc></url>
  <url><loc>https://blog.openadapt.ai/</loc></url>
</urlset>
"""

SAMPLE_METRICS = {
    "github:OpenAdaptAI/OpenAdapt": {"stars": 1200, "forks": 100},
    "github:OpenAdaptAI/openadapt-flow": {"stars": 200, "forks": 20},
    "github:OpenAdaptAI/openadapt-capture": {"stars": 30, "forks": 3},
    "hn": {"hits": 12, "points": 340, "comments": 210},
    "pypi:openadapt": 54321,
    "pypi:openadapt-flow": 4321,
    "blog_posts": 2,
}


def test_default_week_label_format():
    import datetime

    assert default_week_label(datetime.date(2026, 8, 22)) == "2026-W34"


def test_fetch_blog_post_count_counts_only_posts(mocker):
    response = mocker.Mock(status_code=200, text=SAMPLE_SITEMAP)
    mocker.patch.object(httpx, "get", return_value=response)
    assert fetch_blog_post_count() == 2


def test_render_report_is_deterministic_table():
    first = render_report(SAMPLE_METRICS, "2026-W34")
    second = render_report(dict(SAMPLE_METRICS), "2026-W34")
    assert first == second
    lines = first.strip().splitlines()
    assert lines[0] == "# Growth metrics — 2026-W34"
    assert lines[2] == "| Metric | Value |"
    assert "| GitHub stars — OpenAdaptAI/OpenAdapt | 1200 |" in lines
    assert "| GitHub forks — OpenAdaptAI/OpenAdapt | 100 |" in lines
    assert "| GitHub stars — OpenAdaptAI/openadapt-flow | 200 |" in lines
    assert "| Hacker News hits (stories mentioning OpenAdapt) | 12 |" in lines
    assert "| Hacker News points (summed) | 340 |" in lines
    assert "| Hacker News comments (summed) | 210 |" in lines
    assert "| PyPI downloads last 7d — openadapt | 54,321 |" in lines
    assert "| PyPI downloads last 7d — openadapt-flow | 4,321 |" in lines
    assert "| Blog posts (sitemap) | 2 |" in lines


def test_render_report_marks_failed_sources_as_na():
    metrics = {key: None for key in SAMPLE_METRICS}
    report = render_report(metrics, "2026-W35")
    # 3 repos x (stars, forks) + HN x3 + 2 packages + blog = 12 "n/a" cells.
    assert report.count("n/a") == 12
    assert "| GitHub stars — OpenAdaptAI/OpenAdapt | n/a |" in report
    assert "| PyPI downloads last 7d — openadapt | n/a |" in report
    assert "| Blog posts (sitemap) | n/a |" in report


def test_collect_metrics_uses_expected_endpoints(mocker):
    seen_urls = []
    http_get_urls = []

    def fake_get_json(url, params=None):
        seen_urls.append(url)
        if "/repos/" in url:
            return {"stargazers_count": 7, "forks_count": 2}
        if "hn.algolia" in url:
            return {
                "nbHits": 3,
                "hits": [{"points": 10, "num_comments": 4},
                         {"points": 1, "num_comments": 0}],
            }
        if "pypistats" in url:
            return {"data": {"last_day": 1, "last_week": 99, "last_month": 5}}
        raise AssertionError(f"unexpected endpoint: {url}")

    def fake_httpx_get(url, **kwargs):
        http_get_urls.append(url)
        return mocker.Mock(status_code=200, text=SAMPLE_SITEMAP)

    mocker.patch("metrics_weekly._get_json", side_effect=fake_get_json)
    mocker.patch.object(httpx, "get", side_effect=fake_httpx_get)

    metrics = collect_metrics()

    assert sum(1 for url in seen_urls
               if url.endswith("/repos/OpenAdaptAI/OpenAdapt")) == 1
    assert any(url.endswith("/repos/OpenAdaptAI/openadapt-capture")
               for url in seen_urls)
    assert any("hn.algolia" in url for url in seen_urls)
    assert http_get_urls == [BLOG_SITEMAP]
    assert metrics["github:OpenAdaptAI/OpenAdapt"] == {"stars": 7, "forks": 2}
    assert metrics["hn"] == {"hits": 3, "points": 11, "comments": 4}
    assert metrics["pypi:openadapt"] == 99
    assert metrics["pypi:openadapt-flow"] == 99
    assert metrics["blog_posts"] == 2


def test_collect_metrics_survives_http_errors(mocker):
    def raise_http_error(*args, **kwargs):
        raise httpx.ConnectError("offline")

    mocker.patch("metrics_weekly._get_json", side_effect=raise_http_error)
    mocker.patch.object(
        httpx, "get",
        side_effect=httpx.ConnectError("offline"),
    )
    metrics = collect_metrics()
    assert metrics["hn"] is None
    assert metrics["pypi:openadapt"] is None
    assert metrics["blog_posts"] is None
