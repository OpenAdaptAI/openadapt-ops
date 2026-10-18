"""Generate the Flow command reference from the released PyPI package.

The command reference must describe the Flow release that users install, not
OpenAdapt `main`. This script reads the argparse parser of an exact
`openadapt-flow` release from PyPI and keeps two files in step with it:

- `tests/fixtures/flow_cli_<version>.json`: every command and subcommand, its
  one-line help, and its long options. Tests and `validate_docs.py` read it.
- `docs/reference/flow-commands.md`: the generated page, rendered from that
  snapshot.

Commands:

    # Install the pinned release from PyPI in a throwaway environment and
    # rewrite the snapshot and the page. Needs network access and `uv`.
    python scripts/flow_cli_reference.py snapshot

    # Online check, run in CI: the committed snapshot matches the release.
    python scripts/flow_cli_reference.py check-pypi

    # Offline check: the committed page matches the committed snapshot.
    python scripts/flow_cli_reference.py check

To move the docs to a new Flow release, change `FLOW_VERSION`, run `snapshot`,
document any new command in `docs/reference/cli.md`, and commit the result.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The released openadapt-flow the docs describe.
FLOW_VERSION = "2.2.0"
#: Until FLOW_VERSION is on PyPI, build it from this OpenAdapt commit instead,
#: which holds everything the release ships. Set it to None on release day and
#: rerun `snapshot`; the snapshot must not change.
FLOW_SOURCE: str | None = (
    "openadapt-flow @ git+https://github.com/OpenAdaptAI/OpenAdapt"
    "@9104577e603e030f89318ead9cd9d586d439aefe#subdirectory=packages/flow"
)
SNAPSHOT = ROOT / "tests" / "fixtures" / f"flow_cli_{FLOW_VERSION}.json"
PAGE = ROOT / "docs" / "reference" / "flow-commands.md"
CURATED_PAGE = ROOT / "docs" / "reference" / "cli.md"

# Runs inside the throwaway environment that has the release installed. It
# prints the parser as JSON and imports nothing from this repository.
_INTROSPECT = r"""
import argparse, json, sys
from importlib.metadata import version
from openadapt_flow.__main__ import build_parser

def long_options(parser):
    found = set()
    for action in parser._actions:
        found.update(o for o in action.option_strings if o.startswith("--"))
    return sorted(found)

def subparsers(parser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            helps = {a.dest: (a.help or "") for a in action._choices_actions}
            for name, child in action.choices.items():
                if child.prog.split()[-1] != name:
                    continue  # an alias; the canonical name is listed
                yield name, helps.get(name, ""), child

def walk(parser, path, commands, helps):
    for name, help_text, child in subparsers(parser):
        key = " ".join(path + [name])
        commands[key] = long_options(child)
        helps[key] = " ".join(help_text.split())
        walk(child, path + [name], commands, helps)

root = build_parser()
commands, helps = {}, {}
walk(root, [], commands, helps)
json.dump({
    "flow_version": version("openadapt-flow"),
    "global_options": long_options(root),
    "commands": commands,
    "help": helps,
}, sys.stdout)
"""


def read_snapshot(path: pathlib.Path = SNAPSHOT) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def command_paths(snapshot: dict) -> list[str]:
    """Every command, top-level verbs and subcommands, in sorted order."""
    return sorted(snapshot["commands"])


def top_level_verbs(snapshot: dict) -> list[str]:
    return [path for path in command_paths(snapshot) if " " not in path]


def fetch_released_snapshot(version: str = FLOW_VERSION) -> dict:
    """Install `openadapt-flow==version` from PyPI and read its parser."""
    with tempfile.TemporaryDirectory(prefix="flow-cli-") as tmp:
        venv = pathlib.Path(tmp) / "venv"
        subprocess.run(
            ["uv", "venv", "--quiet", "--python", "3.12", str(venv)], check=True
        )
        python = venv / ("Scripts" if sys.platform == "win32" else "bin") / "python"
        subprocess.run(
            [
                "uv", "pip", "install", "--quiet", "--python", str(python),
                "--index-url", "https://pypi.org/simple",
                FLOW_SOURCE or f"openadapt-flow=={version}",
            ],
            check=True,
        )
        result = subprocess.run(
            [str(python), "-c", _INTROSPECT],
            check=True, capture_output=True, text=True,
        )
    data = json.loads(result.stdout)
    if FLOW_SOURCE is None and data["flow_version"] != version:
        raise SystemExit(
            f"PyPI installed openadapt-flow {data['flow_version']}, not {version}"
        )
    return {
        "flow_version": version,
        "source": (
            f"argparse parser of openadapt-flow {version} from "
            + ("OpenAdapt main, before the release, " if FLOW_SOURCE else "PyPI ")
            + "(openadapt_flow.__main__.build_parser), long options only. "
            "Written by scripts/flow_cli_reference.py snapshot."
        ),
        "global_options": data["global_options"],
        "commands": dict(sorted(data["commands"].items())),
        "help": dict(sorted(data["help"].items())),
    }


def _cell(text: str) -> str:
    return text.replace("|", "\\|") or " "


def render(snapshot: dict) -> str:
    version = snapshot["flow_version"]
    lines = [
        "---",
        "description: >-",
        f"  Every openadapt-flow {version} command and subcommand with its long",
        "  options, generated from the released package.",
        "---",
        "",
        "# All Flow commands",
        "",
        "<!-- Generated by scripts/flow_cli_reference.py. Do not edit. -->",
        "",
        f"This page lists every command in `openadapt-flow` {version}, the release",
        "on PyPI, read from its argument parser. `openadapt flow COMMAND` and",
        "`openadapt-flow COMMAND` are the same command. Run any command with",
        "`--help` for its arguments. For what the commands do and how they fit",
        "together, see the [command reference](cli.md).",
        "",
    ]
    helps = snapshot.get("help", {})
    for verb in top_level_verbs(snapshot):
        lines += [f"## `{verb}`", ""]
        if helps.get(verb):
            lines += [helps[verb], ""]
        family = [verb] + [
            path for path in command_paths(snapshot) if path.startswith(verb + " ")
        ]
        lines += ["| Command | Long options |", "|---|---|"]
        for path in family:
            options = ", ".join(
                f"`{o}`" for o in snapshot["commands"][path] if o != "--help"
            )
            lines.append(f"| `openadapt flow {path}` | {_cell(options)} |")
        subcommands = [path for path in family if path != verb and helps.get(path)]
        if subcommands:
            lines.append("")
            for path in subcommands:
                lines.append(f"- `{path}`: {helps[path]}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def missing_from_reference(snapshot: dict, *pages: pathlib.Path) -> list[str]:
    """Commands whose full path appears on none of the reference pages."""
    text = " ".join(
        " ".join(page.read_text(encoding="utf-8").split()) for page in pages
    )
    return [
        path for path in command_paths(snapshot)
        if f"openadapt flow {path}" not in text
        and f"openadapt-flow {path}" not in text
    ]


def check_page(snapshot: dict | None = None, page: pathlib.Path = PAGE) -> list[str]:
    """Problems with the generated page, for validate_docs.py."""
    snapshot = snapshot or read_snapshot()
    problems = []
    if snapshot["flow_version"] != FLOW_VERSION:
        problems.append(
            f"{SNAPSHOT.name} is for openadapt-flow {snapshot['flow_version']}, "
            f"not the pinned {FLOW_VERSION}"
        )
    if not page.is_file() or page.read_text(encoding="utf-8") != render(snapshot):
        name = page.relative_to(ROOT) if page.is_relative_to(ROOT) else page
        problems.append(
            f"{name} doesn't match the {FLOW_VERSION} snapshot; "
            "run `python scripts/flow_cli_reference.py render`"
        )
    for path in missing_from_reference(snapshot, page):
        problems.append(f"released Flow command missing from the reference: {path}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "action", choices=("snapshot", "render", "check", "check-pypi")
    )
    args = parser.parse_args(argv)

    if args.action == "snapshot":
        snapshot = fetch_released_snapshot()
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        PAGE.write_text(render(snapshot), encoding="utf-8")
        print(f"Wrote {SNAPSHOT.relative_to(ROOT)} and {PAGE.relative_to(ROOT)}")
        return 0
    if args.action == "render":
        PAGE.write_text(render(read_snapshot()), encoding="utf-8")
        print(f"Wrote {PAGE.relative_to(ROOT)}")
        return 0
    if args.action == "check":
        problems = check_page()
        for problem in problems:
            print(f"::error::{problem}")
        return 1 if problems else 0

    released = fetch_released_snapshot()
    committed = read_snapshot()
    problems = []
    for field in ("global_options", "commands", "help"):
        if released[field] != committed.get(field):
            problems.append(
                f"{SNAPSHOT.relative_to(ROOT)} `{field}` differs from openadapt-flow "
                f"{FLOW_VERSION} on PyPI; run `python scripts/flow_cli_reference.py snapshot`"
            )
    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print(f"Snapshot matches openadapt-flow {FLOW_VERSION} on PyPI.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
