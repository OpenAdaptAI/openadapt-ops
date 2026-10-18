"""The private name check: skipped without a list, fail-closed with one."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_private_names as names  # noqa: E402


def test_no_list_means_skipped_unless_required() -> None:
    assert names.check(["docs"], environ={}) == ("skipped", [])
    status, problems = names.check(["docs"], environ={}, require=True)
    assert status == "failed" and problems


def test_hit_is_reported_without_the_name(tmp_path) -> None:
    page = tmp_path / "page.md"
    page.write_text("intro\nWorks with Example Clinic today.\n")
    status, problems = names.check(
        [page], environ={names.ENV_PATTERNS: "# comment\n\nexample[ _-]*clinic\n"}
    )
    assert status == "failed"
    assert problems == [f"{page.as_posix()}:2: matches private name pattern #1"]
    assert "clinic" not in problems[0].lower().replace(page.as_posix().lower(), "")


def test_file_names_are_checked(tmp_path) -> None:
    (tmp_path / "example-clinic.md").write_text("nothing here\n")
    status, problems = names.check([tmp_path], environ={names.ENV_PATTERNS: "example"})
    assert status == "failed"
    assert problems[0].endswith("(file name):1: matches private name pattern #1")


def test_clean_docs_pass(tmp_path) -> None:
    (tmp_path / "page.md").write_text("OpenAdapt docs\n")
    assert names.check([tmp_path], environ={names.ENV_PATTERNS: "zzz-not-there"}) == ("clean", [])


@pytest.mark.parametrize(
    "environ",
    [
        {names.ENV_PATTERNS: "("},
        {names.ENV_PATTERNS: "# only a comment\n"},
        {names.ENV_PATTERNS_FILE: "/nonexistent/names.txt"},
    ],
)
def test_an_unusable_list_fails_closed(environ) -> None:
    status, problems = names.check(["docs"], environ=environ)
    assert status == "failed" and problems
    assert "(" not in problems[0]


def test_list_can_come_from_a_file(tmp_path) -> None:
    listing = tmp_path / "names.txt"
    listing.write_text("example clinic\n")
    page = tmp_path / "docs.md"
    page.write_text("example clinic\n")
    status, _ = names.check([page], environ={names.ENV_PATTERNS_FILE: str(listing)})
    assert status == "failed"


def test_the_public_repo_holds_no_list() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    assert not [path for path in tracked if "private-names" in path or path.endswith("names.txt")]


def test_cli_exit_codes(tmp_path, monkeypatch) -> None:
    page = tmp_path / "page.md"
    page.write_text("Example Clinic\n")
    monkeypatch.delenv(names.ENV_PATTERNS, raising=False)
    monkeypatch.delenv(names.ENV_PATTERNS_FILE, raising=False)
    assert names.main([str(page)]) == 0
    assert names.main([str(page), "--require"]) == 1
    monkeypatch.setenv(names.ENV_PATTERNS, "example clinic")
    assert names.main([str(page)]) == 1


def test_whats_new_generator_keeps_the_old_digest_on_a_hit(tmp_path, mocker, monkeypatch) -> None:
    from generate_whats_new import generate

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv(names.ENV_PATTERNS, "example clinic")
    target = tmp_path / "whats-new.md"
    target.write_text("previous digest\n")
    payload = [{"number": 7, "title": "Onboard Example Clinic", "url": "https://github.com/o/r/pull/7", "mergedAt": "2026-10-17T00:00:00Z"}]
    mocker.patch(
        "generate_whats_new.subprocess.run",
        return_value=subprocess.CompletedProcess(["gh"], 0, json.dumps(payload), ""),
    )
    with pytest.raises(RuntimeError) as exc:
        generate(repos=[{"name": "r", "github": "o/r"}], docs_dir=tmp_path)
    assert "Example Clinic" not in str(exc.value)
    assert target.read_text() == "previous digest\n"
