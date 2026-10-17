"""Every documented `openadapt-flow` command must parse in the pinned release.

The docs once told readers to run `openadapt-flow replay bundle --seal`, a
planned flag that no Flow release has. Following that proof step ended in
`unrecognized arguments: --seal`. This check reads every `openadapt-flow ...`
and `openadapt flow ...` command written as code (fenced blocks and inline
code spans) and checks its subcommand and long options against the argparse
parser of the pinned Flow release.

`tests/fixtures/flow_cli_2.1.0.json` holds that parser's subcommands and long
options. When the docs move to a newer Flow release, regenerate the fixture
from that release's `openadapt_flow.__main__.build_parser()`: for each
subparser, record the sorted `option_strings` that start with `--`, keyed by
the space-joined subcommand path (for example `qualify propose`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FIXTURE = ROOT / "tests/fixtures/flow_cli_2.1.0.json"

# Options that exist on OpenAdapt `main` but not in the pinned release. A page
# may show them only where it labels them as unreleased; each entry names the
# page that does. Remove an entry when the release that ships it is pinned.
UNRELEASED_OPTIONS = {
    # docs/how-to/certify-and-qualify.md: the one-command qualification campaign.
    "qualify": {"--verify", "--out", "--certify"},
}
# Regenerated from other repositories' release notes; they quote history.
GENERATED_PAGES = {DOCS / "changelog.md", DOCS / "whats-new.md"}

_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE = re.compile(r"`([^`\n]+)`")
# A Flow invocation at command position: the start of the code, or after a
# shell separator, a prompt, or `uv run`.
_COMMAND = re.compile(
    r"(?:^|[;&|(]\s*|\$\s+|\buv run\s+)(?:openadapt-flow|openadapt flow)\s+(.*)$"
)
_END_OF_COMMAND = re.compile(r"\s(?:\||&&|;|#|>)\s")
_SUBCOMMAND = re.compile(r"^[a-z][a-z-]*$")


def _cli() -> tuple[set[str], dict[str, set[str]]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    commands = {name: set(options) for name, options in data["commands"].items()}
    return set(data["global_options"]), commands


def _doc_pages() -> list[Path]:
    return sorted(
        path
        for path in DOCS.rglob("*")
        if path.suffix in {".md", ".txt"} and path.is_file() and path not in GENERATED_PAGES
    )


def _code_snippets(text: str) -> list[tuple[int, str]]:
    """Return (line number, code) for fenced lines and inline code spans."""
    snippets: list[tuple[int, str]] = []
    in_fence = False
    pending = ""
    pending_line = 0
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            pending = ""
            continue
        if in_fence:
            if not pending:
                pending_line = number
            if line.rstrip().endswith("\\"):
                pending += line.rstrip()[:-1] + " "
                continue
            snippets.append((pending_line, pending + line))
            pending = ""
            continue
        snippets.extend((number, span) for span in _INLINE.findall(line))
    return snippets


def _flow_commands(text: str) -> list[tuple[int, str, list[str]]]:
    """Return (line number, code, tokens after the program name) per command."""
    found = []
    for number, code in _code_snippets(text):
        match = _COMMAND.search(code.strip())
        if not match:
            continue
        tokens = _END_OF_COMMAND.split(f" {match.group(1)} ", maxsplit=1)[0].split()
        # A version range (`openadapt-flow >=1.29`), a placeholder
        # (`openadapt flow …`), or a bare option is not a subcommand.
        if tokens and _SUBCOMMAND.match(tokens[0]):
            found.append((number, code.strip(), tokens))
    return found


def _problems(text: str, global_options: set[str], commands: dict[str, set[str]]) -> list[str]:
    problems = []
    for number, code, tokens in _flow_commands(text):
        command = tokens[0]
        if command not in commands:
            problems.append(f"line {number}: unknown subcommand `{command}` in `{code}`")
            continue
        for token in tokens[1:]:
            if f"{command} {token}" in commands:
                command = f"{command} {token}"
                continue
            if not token.startswith("--"):
                continue
            option = token.split("=", 1)[0].rstrip(".,;:)")
            if option not in commands[command] | global_options | UNRELEASED_OPTIONS.get(command, set()):
                problems.append(f"line {number}: `{command}` has no `{option}` option in `{code}`")
    return problems


def test_fixture_matches_the_pinned_verb_list() -> None:
    from tests.test_cli_reference import FLOW_VERBS

    _, commands = _cli()
    assert sorted(name for name in commands if " " not in name) == sorted(FLOW_VERBS)


def test_the_check_catches_a_planned_flag_and_accepts_real_ones() -> None:
    global_options, commands = _cli()
    sample = "\n".join(
        [
            "```bash",
            "openadapt-flow replay bundle --seal",
            "openadapt-flow seal -o out bundle",
            "openadapt-flow qualify propose bundle \\",
            "  --break-it",
            "```",
            "Run `openadapt flow replay bundle --url http://localhost:8080`.",
            "Then `openadapt flow notaverb`.",
            "Install with `pip install openadapt-flow` first.",
            "The launcher needs `openadapt-flow >=1.29,<2` and runs `openadapt flow …`.",
        ]
    )
    problems = _problems(sample, global_options, commands)
    assert len(problems) == 3, problems
    assert "`replay` has no `--seal` option" in problems[0]
    assert "`qualify propose` has no `--break-it` option" in problems[1]
    assert "unknown subcommand `notaverb`" in problems[2]


def test_documented_flow_commands_use_only_shipped_options() -> None:
    global_options, commands = _cli()
    pages = _doc_pages()
    # The docs show a couple of hundred Flow commands; a scan that finds only
    # a handful has stopped matching them.
    assert sum(len(_flow_commands(page.read_text(encoding="utf-8"))) for page in pages) > 100
    problems = []
    for page in pages:
        for problem in _problems(page.read_text(encoding="utf-8"), global_options, commands):
            problems.append(f"{page.relative_to(ROOT)} {problem}")
    assert problems == [], "\n".join(problems)
