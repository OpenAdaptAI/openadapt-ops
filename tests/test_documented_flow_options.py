"""Every documented Flow and agent command must parse in the pinned release.

The docs once told readers to run `openadapt-flow replay bundle --seal`, a
planned flag that no Flow release has. Following that proof step ended in
`unrecognized arguments: --seal`. This check reads every `openadapt-flow ...`
and `openadapt flow ...` command written as code (fenced blocks and inline
code spans) and checks its subcommand and long options against the argparse
parser of the pinned Flow release.

`tests/fixtures/flow_cli_<version>.json` holds that parser's subcommands and
long options, keyed by the space-joined subcommand path (for example
`qualify propose`). `scripts/flow_cli_reference.py snapshot` writes it from the
release on PyPI.

The same check covers `openadapt-agent ...` and `openadapt agent ...` against
`tests/fixtures/agent_cli.json`, which `scripts/generate_cli_reference.py`
writes from the version pinned in `cli-reference/requirements.txt`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

sys.path.insert(0, str(ROOT / "scripts"))

from flow_cli_reference import FLOW_VERSION, SNAPSHOT as FIXTURE  # noqa: E402

AGENT_FIXTURE = ROOT / "tests/fixtures/agent_cli.json"
REQUIREMENTS = ROOT / "cli-reference/requirements.txt"

# Options that exist on OpenAdapt `main` but not in the pinned release. A page
# may show them only where it labels them as unreleased; each entry names the
# page that does. Remove an entry when the release that ships it is pinned.
UNRELEASED_OPTIONS: dict[str, set[str]] = {}
# Flow rewrites `qualify <bundle> ...` to `qualify campaign <bundle> ...`
# (`_qualify_default_form`), so that form takes the campaign's options.
DEFAULT_SUBCOMMANDS = {"qualify": "qualify campaign"}
# Regenerated from other repositories' release notes; they quote history.
# The command help page is generated from the pinned parsers themselves.
GENERATED_PAGES = {
    DOCS / "changelog.md",
    DOCS / "whats-new.md",
    DOCS / "reference/cli-help.md",
}

_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE = re.compile(r"`([^`\n]+)`")
# A Flow invocation at command position: the start of the code, or after a
# shell separator, a prompt, or `uv run`.
_COMMAND = re.compile(
    r"(?:^|[;&|(]\s*|\$\s+|\buv run\s+)(?:openadapt-flow|openadapt flow)\s+(.*)$"
)
_AGENT_COMMAND = re.compile(
    r"(?:^|[;&|(]\s*|\$\s+|\buv run\s+)(?:openadapt-agent|openadapt agent)\s+(.*)$"
)
_END_OF_COMMAND = re.compile(r"\s(?:\||&&|;|#|>)\s")
_SUBCOMMAND = re.compile(r"^[a-z][a-z-]*$")


def _cli(fixture: Path = FIXTURE) -> tuple[set[str], dict[str, set[str]]]:
    data = json.loads(fixture.read_text(encoding="utf-8"))
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


def _flow_commands(text: str, pattern: re.Pattern = _COMMAND) -> list[tuple[int, str, list[str]]]:
    """Return (line number, code, tokens after the program name) per command."""
    found = []
    for number, code in _code_snippets(text):
        match = pattern.search(code.strip())
        if not match:
            continue
        tokens = _END_OF_COMMAND.split(f" {match.group(1)} ", maxsplit=1)[0].split()
        # A version range (`openadapt-flow >=1.29`), a placeholder
        # (`openadapt flow …`), or a bare option is not a subcommand.
        if tokens and _SUBCOMMAND.match(tokens[0]):
            found.append((number, code.strip(), tokens))
    return found


def _problems(
    text: str,
    global_options: set[str],
    commands: dict[str, set[str]],
    pattern: re.Pattern = _COMMAND,
    unreleased: dict[str, set[str]] = UNRELEASED_OPTIONS,
) -> list[str]:
    problems = []
    for number, code, tokens in _flow_commands(text, pattern):
        command = tokens[0]
        if command not in commands:
            problems.append(f"line {number}: unknown subcommand `{command}` in `{code}`")
            continue
        default = DEFAULT_SUBCOMMANDS.get(command)
        if (
            default in commands
            and len(tokens) > 1
            and not tokens[1].startswith("-")
            and f"{command} {tokens[1]}" not in commands
        ):
            command = default
        for token in tokens[1:]:
            if f"{command} {token}" in commands:
                command = f"{command} {token}"
                continue
            if not token.startswith("--"):
                continue
            option = token.split("=", 1)[0].rstrip(".,;:)")
            if option not in commands[command] | global_options | unreleased.get(command, set()):
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


def _pins() -> dict[str, str]:
    """{name: version} for `name==version` and `name @ URL  # release VERSION` lines."""
    pins = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        if " @ " in line:
            pins[line.split(" @ ", 1)[0].strip()] = line.rsplit("  # release ", 1)[1].strip()
            continue
        line = line.split("#", 1)[0].strip()
        if line:
            name, _, version = line.partition("==")
            pins[name.strip()] = version.strip()
    return pins


def test_agent_fixture_and_flow_pin_match_the_pinned_versions() -> None:
    pins = _pins()
    data = json.loads(AGENT_FIXTURE.read_text(encoding="utf-8"))
    assert data["program"] == "openadapt-agent"
    assert data["version"] == pins["openadapt-agent"], f"regenerate {AGENT_FIXTURE.name}"
    # The agent help is generated with the Flow release the Flow reference describes.
    assert pins["openadapt-flow"] == FLOW_VERSION


def test_documented_agent_commands_use_only_shipped_options() -> None:
    global_options, commands = _cli(AGENT_FIXTURE)
    pages = _doc_pages()
    assert sum(
        len(_flow_commands(page.read_text(encoding="utf-8"), _AGENT_COMMAND)) for page in pages
    ) > 5
    problems = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for problem in _problems(text, global_options, commands, _AGENT_COMMAND, {}):
            problems.append(f"{page.relative_to(ROOT)} {problem}")
    assert problems == [], "\n".join(problems)
