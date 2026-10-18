"""Fail the docs build if a customer or prospect name appears in public docs.

The names themselves are private, so this public repository holds no list.
The check reads one at run time from either:

- `DOCS_PRIVATE_NAME_PATTERNS`: the patterns, one per line; or
- `DOCS_PRIVATE_NAME_PATTERNS_FILE`: a path to a file in that format, such as
  one checked out from a private repository.

Each non-blank line that doesn't start with `#` is a case-insensitive Python
regular expression, for example `acme[ _-]*clinic`.

When neither variable is set, the check reports that it was skipped and
passes, because a fork's pull request and a local build can't read the list.
`--require` makes a missing list fail instead. When a list is set, it fails
closed: a hit fails, and so does a list that is empty or has an invalid
pattern.

A hit is reported by file, line, and pattern number. The matched text and the
pattern are never printed, so CI logs don't repeat the name.

    DOCS_PRIVATE_NAME_PATTERNS_FILE=~/private/names.txt \\
        python scripts/check_private_names.py [--site site] [PATH ...]
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_PATTERNS = "DOCS_PRIVATE_NAME_PATTERNS"
ENV_PATTERNS_FILE = "DOCS_PRIVATE_NAME_PATTERNS_FILE"
#: What the public docs build reads or publishes.
DEFAULT_PATHS = ("docs", "mkdocs.yml", "overrides", "templates", "prompts", "README.md")
TEXT_SUFFIXES = {
    ".md", ".txt", ".yml", ".yaml", ".json", ".html", ".htm", ".xml", ".js",
    ".css", ".j2", ".svg", ".py", ".toml",
}


class PatternListError(Exception):
    """The list is set but can't be used. Callers must fail closed."""


@dataclass(frozen=True)
class Hit:
    location: str
    line: int
    pattern_number: int

    def __str__(self) -> str:
        return (
            f"{self.location}:{self.line}: matches private name pattern "
            f"#{self.pattern_number}"
        )


def load_patterns(environ: dict[str, str] | None = None) -> list[re.Pattern[str]] | None:
    """The compiled list, or None when no list is configured."""
    environ = os.environ if environ is None else environ
    raw = environ.get(ENV_PATTERNS, "")
    path = environ.get(ENV_PATTERNS_FILE, "").strip()
    if not raw.strip() and not path:
        return None
    if path:
        try:
            raw = raw + "\n" + pathlib.Path(path).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise PatternListError(f"{ENV_PATTERNS_FILE} can't be read: {exc.strerror}") from None
    patterns = []
    for number, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(line, re.IGNORECASE))
        except re.error:
            raise PatternListError(f"private name pattern on line {number} is invalid") from None
    if not patterns:
        raise PatternListError("the private name list is set but has no patterns")
    return patterns


def find_in_text(text: str, patterns: list[re.Pattern[str]], location: str) -> list[Hit]:
    hits = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for pattern_number, pattern in enumerate(patterns, 1):
            if pattern.search(line):
                hits.append(Hit(location, line_number, pattern_number))
    return hits


def _files(path: pathlib.Path):
    if path.is_file():
        yield path
    elif path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in TEXT_SUFFIXES:
                yield child


def find_in_paths(paths, patterns: list[re.Pattern[str]], root: pathlib.Path = ROOT) -> list[Hit]:
    hits = []
    for base in paths:
        base = pathlib.Path(base)
        base = base if base.is_absolute() else root / base
        for file in _files(base):
            try:
                text = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            try:
                location = file.relative_to(root).as_posix()
            except ValueError:
                location = file.as_posix()
            hits.extend(find_in_text(text, patterns, location))
            # A file name can carry a name too.
            hits.extend(find_in_text(file.name, patterns, location + " (file name)"))
    return hits


def check(paths=DEFAULT_PATHS, *, environ=None, require=False) -> tuple[str, list[str]]:
    """Return (status, problems). Status is `skipped`, `clean`, or `failed`."""
    try:
        patterns = load_patterns(environ)
    except PatternListError as exc:
        return "failed", [str(exc)]
    if patterns is None:
        if require:
            return "failed", [f"no private name list: set {ENV_PATTERNS} or {ENV_PATTERNS_FILE}"]
        return "skipped", []
    hits = find_in_paths(paths, patterns)
    return ("failed" if hits else "clean"), [str(hit) for hit in hits]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail on customer or prospect names in public docs.")
    parser.add_argument("paths", nargs="*", help=f"files or directories (default: {', '.join(DEFAULT_PATHS)})")
    parser.add_argument("--site", help="also scan this built site directory")
    parser.add_argument("--require", action="store_true", help="fail when no list is configured")
    args = parser.parse_args(argv)
    paths = list(args.paths or DEFAULT_PATHS)
    if args.site:
        paths.append(args.site)
    status, problems = check(paths, require=args.require)
    if status == "skipped":
        print(
            f"::notice::Private name check skipped: {ENV_PATTERNS} and "
            f"{ENV_PATTERNS_FILE} are not set."
        )
        return 0
    for problem in problems:
        print(f"::error::{problem}")
    if status == "clean":
        print("Private name check passed.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
