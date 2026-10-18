"""The `openadapt flow` CLI reference must cover the shipped verbs.

`FLOW_VERBS` is the top-level subcommand list of the pinned openadapt-flow
release, read from `tests/fixtures/flow_cli.json`, which
`scripts/generate_cli_reference.py` writes from that release's parser. When
the pin moves, document the added and removed verbs in docs/reference/cli.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI_REFERENCE = ROOT / "docs/reference/cli.md"
FLOW_FIXTURE = ROOT / "tests/fixtures/flow_cli.json"

FLOW_VERBS = tuple(
    name
    for name in json.loads(FLOW_FIXTURE.read_text(encoding="utf-8"))["commands"]
    if " " not in name
)


def _text() -> str:
    return CLI_REFERENCE.read_text(encoding="utf-8")


def _verbs_table() -> str:
    text = _text()
    start = text.index("## Verbs at a glance")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def _table_verbs() -> set[str]:
    verbs: set[str] = set()
    for line in _verbs_table().splitlines():
        if line.startswith("| ") and not line.startswith("| Verb") and "---" not in line:
            first_cell = line.split("|")[1]
            verbs.update(re.findall(r"`([a-z][a-z-]*)`", first_cell))
    return verbs


def test_verbs_table_lists_every_shipped_verb() -> None:
    missing = [verb for verb in FLOW_VERBS if verb not in _table_verbs()]
    assert missing == [], f"verbs missing from the CLI reference table: {missing}"


def test_verbs_table_lists_no_verb_the_cli_lacks() -> None:
    extra = sorted(_table_verbs() - set(FLOW_VERBS))
    assert extra == [], f"the CLI reference table lists unknown verbs: {extra}"


def test_verbs_table_links_resolve_to_sections() -> None:
    text = _text()
    anchors = set(re.findall(r"\{#([a-z0-9-]+)\}", text))
    for heading in re.findall(r"^#{2,3} (.+?)\s*(?:\{#[a-z0-9-]+\})?$", text, re.MULTILINE):
        anchors.add(re.sub(r"[^a-z0-9]+", "-", heading.lower().replace("`", "")).strip("-"))
    links = set(re.findall(r"\]\(#([a-z0-9-]+)\)", _verbs_table()))
    assert sorted(links - anchors) == []


def test_reference_has_no_universal_web_default() -> None:
    text = " ".join(_text().split())
    assert not re.search(r"default is `?web`?", text)
    assert "`--backend web` (the default)" not in text
    assert "`--backend web`** (the default)" not in text
    assert "captures on this OS" in text


# Verbs that accept `--config deployment.yaml` in openadapt-flow 2.1.0.
# `record` and `compile` don't.
CONFIG_VERBS = ("certify", "replay", "run", "resume")


def test_docs_name_only_the_verbs_that_accept_config() -> None:
    listed = ", ".join(f"`{verb}`" for verb in CONFIG_VERBS[:-1])
    expected = f"{listed}, and `{CONFIG_VERBS[-1]}` all"
    for page in (CLI_REFERENCE, ROOT / "docs/reference/configuration.md"):
        text = " ".join(page.read_text(encoding="utf-8").split())
        assert "`record`, `compile`, `certify`" not in text, page.name
        assert expected in text, page.name
