"""The Flow command reference is generated from the released package."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import flow_cli_reference as ref  # noqa: E402


def test_snapshot_is_for_the_pinned_release() -> None:
    snapshot = ref.read_snapshot()
    assert snapshot["flow_version"] == ref.FLOW_VERSION
    assert ref.SNAPSHOT.name == f"flow_cli_{ref.FLOW_VERSION}.json"
    assert set(snapshot["help"]) == set(snapshot["commands"])


def test_generated_page_matches_the_snapshot() -> None:
    assert ref.check_page() == []


def test_every_released_command_is_on_the_generated_page() -> None:
    assert ref.missing_from_reference(ref.read_snapshot(), ref.PAGE) == []


def test_check_catches_a_stale_page_and_a_missing_command(tmp_path) -> None:
    snapshot = ref.read_snapshot()
    page = tmp_path / "flow-commands.md"
    page.write_text(ref.render(snapshot).replace("`openadapt flow qualify run-case`", "`x`"))
    problems = ref.check_page(snapshot, page)
    assert any("doesn't match" in problem for problem in problems)
    assert "released Flow command missing from the reference: qualify run-case" in problems


def test_render_is_deterministic_and_lists_subcommands() -> None:
    snapshot = ref.read_snapshot()
    text = ref.render(snapshot)
    assert text == ref.render(snapshot)
    assert "| `openadapt flow item-approval decline` |" in text
    assert f"`openadapt-flow` {ref.FLOW_VERSION}" in text


def test_introspection_reads_nested_subparsers() -> None:
    import json
    import subprocess

    # Run the introspection code against a stand-in parser.
    code = ref._INTROSPECT.replace(
        "from importlib.metadata import version\nfrom openadapt_flow.__main__ import build_parser",
        "version = lambda name: '9.9.9'\n"
        "def build_parser():\n"
        "    p = argparse.ArgumentParser(); p.add_argument('--version')\n"
        "    sub = p.add_subparsers()\n"
        "    q = sub.add_parser('qualify', help='Run   qualification')\n"
        "    qs = q.add_subparsers()\n"
        "    r = qs.add_parser('run', help='Run cases', aliases=['go'])\n"
        "    r.add_argument('--out'); r.add_argument('-v', '--verbose')\n"
        "    return p",
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    assert data["flow_version"] == "9.9.9"
    assert data["commands"] == {"qualify": ["--help"], "qualify run": ["--help", "--out", "--verbose"]}
    assert data["help"] == {"qualify": "Run qualification", "qualify run": "Run cases"}
