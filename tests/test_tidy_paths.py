"""Tests for confidential names in historical file paths."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from tidy._config import Pattern
from tidy._core import _build_filename_callback, scan_file_paths


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )


def _create_path_only_history(repo: Path) -> None:
    _run(repo, "git", "init", "-b", "main")
    _run(repo, "git", "config", "user.name", "Tidy Test")
    _run(repo, "git", "config", "user.email", "tidy@example.invalid")
    private_dir = repo / "pages" / "Acme.Co"
    private_dir.mkdir(parents=True)
    (private_dir / "route.js").write_text("export default true;\n", encoding="utf-8")
    _run(repo, "git", "add", ".")
    _run(repo, "git", "commit", "-m", "add customer route")
    private_dir.rename(repo / "pages" / "customer")
    _run(repo, "git", "add", "-A")
    _run(repo, "git", "commit", "-m", "rename route")


def test_scan_file_paths_finds_removed_case_insensitive_name(tmp_path: Path) -> None:
    _create_path_only_history(tmp_path)

    matches = scan_file_paths(
        [Pattern(text="acme.co", case_sensitive=False)],
        cwd=str(tmp_path),
    )

    assert matches
    assert {match.path for match in matches} == {"pages/Acme.Co/route.js"}


def test_filename_callback_treats_pattern_as_literal() -> None:
    callback = _build_filename_callback(
        [Pattern(text="acme.co", case_sensitive=False)],
        "customer",
    )
    namespace: dict[str, object] = {}
    exec("def callback(filename):\n" + textwrap.indent(callback, "    "), namespace)

    result = namespace["callback"](b"pages/Acme.Co/route.js")

    assert result == b"pages/customer/route.js"


@pytest.mark.skipif(shutil.which("git-filter-repo") is None, reason="git-filter-repo is unavailable")
def test_filter_repo_rewrites_historical_file_paths(tmp_path: Path) -> None:
    _create_path_only_history(tmp_path)
    patterns = [Pattern(text="acme.co", case_sensitive=False)]
    callback = _build_filename_callback(patterns, "customer")

    _run(
        tmp_path,
        "git",
        "filter-repo",
        "--filename-callback",
        callback,
        "--force",
    )

    assert scan_file_paths(patterns, cwd=str(tmp_path)) == []
    names = _run(tmp_path, "git", "log", "--all", "--name-only", "--format=").stdout
    assert "acme.co" not in names.lower()
