"""Fail-closed fetch for the online half of the design-token guard.

``tests/test_design_tokens.py`` is the offline half. This file covers
``scripts/vendor_design_tokens.py`` without hitting the network: a mocked
HTTP 404 must exit non-zero, and a token must send the request to the
GitHub Contents API rather than raw.githubusercontent.com.
"""

from __future__ import annotations

import io
import sys
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import vendor_design_tokens as vendor  # noqa: E402


CI_WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
VENDOR_DIR = ROOT / "docs" / "stylesheets" / "vendor" / "openadapt-web"


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url, code, "Not Found", Message(), io.BytesIO(b"")
    )


def test_fetch_raises_on_http_404(mocker) -> None:
    url = (
        "https://api.github.com/repos/OpenAdaptAI/openadapt-web"
        "/contents/styles/tokens.json?ref=main"
    )
    mocker.patch.object(
        vendor.urllib.request,
        "urlopen",
        side_effect=_http_error(url, 404),
    )
    with pytest.raises(vendor.FetchError, match="HTTP 404"):
        vendor.fetch(url, "application/vnd.github.raw")


def test_check_returns_nonzero_when_canonical_fetch_404s(
    monkeypatch, mocker, capsys
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(sys, "argv", ["vendor_design_tokens.py", "--check"])

    def fake_urlopen(request, timeout=None):
        raise _http_error(request.full_url, 404)

    mocker.patch.object(vendor.urllib.request, "urlopen", side_effect=fake_urlopen)

    assert vendor.main() == 1
    captured = capsys.readouterr()
    assert "HTTP 404" in captured.err
    assert "Vendored design tokens match" not in captured.out
    assert "/contents/styles/tokens.json" in captured.err


def test_check_uses_contents_api_when_token_is_set(monkeypatch, mocker) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(sys, "argv", ["vendor_design_tokens.py", "--check"])
    requested: list[str] = []
    authed: list[bool] = []

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        requested.append(url)
        authed.append(request.has_header("Authorization"))
        if "raw.githubusercontent.com" in url:
            raise _http_error(url, 404)
        if "/contents/styles/tokens.json" in url:
            return FakeResponse((VENDOR_DIR / "tokens.json").read_bytes())
        if "/contents/styles/tokens.css" in url:
            return FakeResponse((VENDOR_DIR / "tokens.css").read_bytes())
        raise _http_error(url, 404)

    mocker.patch.object(vendor.urllib.request, "urlopen", side_effect=fake_urlopen)

    assert vendor.main() == 0
    assert any("/contents/styles/tokens.json" in url for url in requested)
    assert any("/contents/styles/tokens.css" in url for url in requested)
    assert not any("raw.githubusercontent.com" in url for url in requested)
    assert all(authed)


def test_ci_job_still_runs_check_and_reads_private_web_with_admin_token() -> None:
    assert "python scripts/vendor_design_tokens.py --check" in CI_WORKFLOW
    assert "secrets.ADMIN_TOKEN || github.token" in CI_WORKFLOW
