#!/usr/bin/env python3
"""Keep the vendored design tokens in step with OpenAdaptAI/openadapt-web.

    --check  (default) fetch the canonical files and fail on any difference
    --write            fetch the canonical files, rewrite the vendored copies
                       and provenance.json

--check is the mechanism that keeps docs.openadapt.ai on the same palette as
openadapt.ai, app.openadapt.ai, and the Desktop application. A value that
changes upstream, or a vendored copy edited by hand, both surface here as a
failed build rather than as a documentation site that no longer looks like the
product it documents.

The offline half is tests/test_design_tokens.py, which needs no network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENDOR_DIR = REPO / "docs" / "stylesheets" / "vendor" / "openadapt-web"
PROVENANCE_PATH = VENDOR_DIR / "provenance.json"

TIMEOUT_SECONDS = 30
USER_AGENT = "openadapt-ops-vendor-design-tokens"
API_ROOT = "https://api.github.com"


class FetchError(RuntimeError):
    """A canonical-file fetch failed. --check must not treat this as a match."""


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def contents_url(repository: str, path: str, ref: str) -> str:
    return (
        f"{API_ROOT}/repos/{repository}/contents/{path}"
        f"?ref={urllib.parse.quote(ref, safe='')}"
    )


def fetch(url: str, accept: str) -> bytes:
    headers = {"Accept": accept, "User-Agent": USER_AGENT}
    request = urllib.request.Request(url, headers=headers)
    token = github_token()
    if token and url.startswith(f"{API_ROOT}/"):
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise FetchError(f"GET {url} -> HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"GET {url} -> {exc.reason}") from exc
    except TimeoutError as exc:
        raise FetchError(f"GET {url} -> timed out") from exc


def fetch_canonical(provenance: dict, entry: dict) -> bytes:
    # openadapt-web is private, so raw.githubusercontent.com 404s in Actions.
    # A repo-scoped GITHUB_TOKEN cannot authenticate that host. Use the
    # Contents API the same way openadapt-desktop does (PR 154).
    token = github_token()
    if token:
        url = contents_url(
            provenance["canonical_repository"],
            entry["canonical_path"],
            provenance["canonical_branch"],
        )
        return fetch(url, "application/vnd.github.raw")
    return fetch(entry["raw_url"], "text/plain")


def canonical_commit(provenance: dict) -> str:
    url = (
        f"{API_ROOT}/repos/{provenance['canonical_repository']}"
        f"/commits/{provenance['canonical_branch']}"
    )
    return json.loads(fetch(url, "application/vnd.github+json"))["sha"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite the copies")
    parser.add_argument("--check", action="store_true", help="the default")
    arguments = parser.parse_args()

    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for name, entry in provenance["files"].items():
        vendored_path = VENDOR_DIR / name
        vendored = vendored_path.read_bytes()
        vendored_digest = sha256(vendored)

        if vendored_digest != entry["sha256"] and not arguments.write:
            failures.append(
                f"{name}: the vendored copy was edited by hand.\n"
                f"    provenance.json pins {entry['sha256']}\n"
                f"    the file on disk is  {vendored_digest}\n"
                f"    Vendored tokens are byte-identical copies. Change the "
                f"value in {provenance['canonical_repository']}:"
                f"{entry['canonical_path']} instead."
            )

        try:
            canonical = fetch_canonical(provenance, entry)
        except FetchError as exc:
            print(f"{name}: {exc}", file=sys.stderr)
            return 1
        canonical_digest = sha256(canonical)

        if arguments.write:
            vendored_path.write_bytes(canonical)
            entry["sha256"] = canonical_digest
            print(f"wrote {name} ({canonical_digest})")
            continue

        if canonical_digest != vendored_digest:
            failures.append(
                f"{name}: drifted from {provenance['canonical_repository']}@"
                f"{provenance['canonical_branch']}.\n"
                f"    canonical {entry['canonical_path']} is {canonical_digest}\n"
                f"    the vendored copy is      {vendored_digest}\n"
                f"    Run: python scripts/vendor_design_tokens.py --write"
            )
        else:
            print(f"{name}: matches canonical ({canonical_digest})")

    if arguments.write:
        provenance["vendored_at_commit"] = canonical_commit(provenance)
        PROVENANCE_PATH.write_text(
            json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"wrote provenance.json at {provenance['canonical_repository']}@"
            f"{provenance['vendored_at_commit']}"
        )
        return 0

    if failures:
        print(
            f"\nVendored design tokens are out of step with "
            f"{provenance['canonical_repository']}:\n",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  - {failure}\n", file=sys.stderr)
        return 1

    print(
        f"\nVendored design tokens match "
        f"{provenance['canonical_repository']}@{provenance['canonical_branch']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
