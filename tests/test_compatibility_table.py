"""The compatibility table must state the ranges the released packages require.

docs/reference/compatibility.md said `openadapt-flow >=1.7,<2`,
`openadapt-capture >=1.1.0`, and two different `openadapt-types` ranges (0.7
and 0.9) while the newest releases required Flow >=1.29, Capture >=1.2.0, and
types 0.17. An adopter who pinned the documented types 0.9 range next to Flow
got a resolver conflict. The page called the package metadata the source of
truth, but nothing compared the two.

`tests/fixtures/pypi_compatibility_metadata.json` is the PyPI metadata of the
newest `openadapt` and `openadapt-flow` releases on 2026-10-16. The daily run
of scripts/check_published_version_claims.py compares the table with live PyPI
instead; when it reports drift, correct the table and refresh the fixture.
"""

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_published_version_claims import (  # noqa: E402
    COMPATIBILITY_PATH,
    Report,
    check_compatibility_structure,
    check_compatibility_table,
)

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "pypi_compatibility_metadata.json"


def _metadata() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {name: info for name, info in data.items() if not name.startswith("$")}


def _table(*rows: str) -> str:
    header = "| Component | Compatible range | Role |\n|---|---|---|\n"
    return "## Current compatibility contract\n\n" + header + "\n".join(rows) + "\n"


CURRENT_ROWS = (
    "| `openadapt` 1.x | `openadapt-flow >=2.0.0,<3` | Installer |",
    "| Native capture | `openadapt-capture >=1.2.0,<2` | Recording |",
    "| Privacy extra | `openadapt-privacy[presidio] >=1.0` | Redaction |",
    "| Flow base install and extras | `openadapt-types >=0.18,<0.19` | Contracts |",
    "| Python | 3.10-3.12 | Runtime |",
)


def _errors(text: str, metadata: dict | None = None) -> list[str]:
    report = Report()
    check_compatibility_structure(text, report)
    check_compatibility_table(text, metadata or _metadata(), report)
    return report.errors


def test_the_committed_table_matches_the_released_metadata():
    assert _errors(COMPATIBILITY_PATH.read_text(encoding="utf-8")) == []


def test_a_current_table_passes():
    assert _errors(_table(*CURRENT_ROWS)) == []


def test_ranges_compare_by_meaning_not_spelling():
    rows = list(CURRENT_ROWS)
    rows[0] = "| `openadapt` 1.x | `openadapt-flow <3.0.0,>=2.0.0` | Installer |"
    assert _errors(_table(*rows)) == []


def test_the_stale_ranges_that_shipped_fail():
    rows = list(CURRENT_ROWS)
    rows[0] = "| `openadapt` 1.x | `openadapt-flow >=1.7,<2` | Installer |"
    rows[1] = "| Native capture | `openadapt-capture >=1.1.0` | Recording |"
    rows[3] = "| Execute clients | `openadapt-types >=0.9,<0.10` | Contracts |"
    errors = _errors(_table(*rows))
    assert len(errors) == 3, errors
    assert any("openadapt-flow >=1.7,<2" in error and ">=2.0.0" in error for error in errors)
    assert any("openadapt-capture >=1.1.0" in error for error in errors)
    assert any("openadapt-types >=0.9,<0.10" in error for error in errors)


def test_every_row_naming_a_package_is_checked():
    rows = [*CURRENT_ROWS, "| UIA handoff | `openadapt-flow >=1.22,<2` | Windows |"]
    errors = _errors(_table(*rows))
    assert len(errors) == 1 and "openadapt-flow >=1.22,<2" in errors[0], errors


def test_a_wrong_python_range_fails():
    rows = list(CURRENT_ROWS)
    rows[4] = "| Python | 3.10-3.13 | Runtime |"
    errors = _errors(_table(*rows))
    assert len(errors) == 1 and "3.10-3.12" in errors[0], errors


def test_one_types_row_fails_when_flow_pins_different_ranges_per_extra():
    metadata = _metadata()
    flow = dict(metadata["openadapt-flow"])
    flow["requires_dist"] = [
        'openadapt-types<0.10.0,>=0.9.0; extra == "execute"'
        if 'extra == "execute"' in line and line.startswith("openadapt-types")
        else line
        for line in flow["requires_dist"]
    ]
    metadata["openadapt-flow"] = flow
    errors = _errors(_table(*CURRENT_ROWS), metadata)
    assert len(errors) == 1 and "different openadapt-types ranges" in errors[0], errors


def test_a_table_missing_a_tracked_package_fails():
    errors = _errors(_table(*CURRENT_ROWS[:3], CURRENT_ROWS[4]))
    assert len(errors) == 1 and "openadapt-types" in errors[0], errors


def test_a_page_without_the_table_fails():
    report = Report()
    check_compatibility_structure("# Versions and compatibility\n", report)
    assert report.errors and "Current compatibility contract" in report.errors[0]
