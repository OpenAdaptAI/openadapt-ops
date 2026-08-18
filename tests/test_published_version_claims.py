"""The published-version guard must FAIL when the docs advertise a stale release.

docs.openadapt.ai is a public surface. On 2026-07-27 ``openadapt-flow`` 1.24.0
published and four sentences here -- one of them on the security-review page --
still asserted that the live runner reported "the published Flow 1.23.0
identity". Nothing detected it.

Proving the guard passes today is worthless on its own; these tests prove it
FAILS on the exact conditions it exists to catch, including a simulated future
release, and that it does not fail on the transient conditions that would make
it noise.
"""

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_published_version_claims import (  # noqa: E402
    Report,
    check_changelog_structure,
    check_claim_locations,
    compare_claim_to_pypi,
    load_registry,
    newest_semver_tag,
    parse_changelog,
    scan_for_unregistered_claims,
)
from render_published_version_claims import render_version_claims  # noqa: E402

CHANGELOG = REPO_ROOT / "docs" / "changelog.md"


@pytest.fixture()
def registry():
    return load_registry()


def _tree(root: pathlib.Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# The guard must fail on a simulated future release
# --------------------------------------------------------------------------


def test_fails_when_a_future_release_supersedes_the_docs():
    """The exact 2026-07-27 bug, simulated forward.

    The docs advertise the release they were written for; PyPI has moved on.
    """
    report = Report()
    compare_claim_to_pypi(
        "docs/changelog.md", "openadapt-flow", "1.24.0", "1.25.0", report
    )

    assert report.errors, "a superseded docs version must fail"
    assert any("superseded release" in error for error in report.errors)
    assert any("1.25.0" in error for error in report.errors)


def test_fails_when_docs_are_many_releases_behind():
    """The realistic shape: docs left on an old minor for weeks."""
    report = Report()
    compare_claim_to_pypi(
        "docs/changelog.md", "openadapt-flow", "1.23.0", "1.24.0", report
    )

    assert any("1.23.0" in error and "1.24.0" in error for error in report.errors)


def test_release_not_yet_on_pypi_warns_instead_of_failing():
    """A GitHub release whose PyPI upload has not landed is not stale docs.

    Failing here would make the guard red at every release, and a guard that
    goes red for reasons unrelated to its subject stops being read -- which is
    precisely how the sibling launcher repository's manifest drift survived.
    """
    report = Report()
    compare_claim_to_pypi(
        "docs/changelog.md", "openadapt-flow", "1.25.0", "1.24.0", report
    )

    assert report.errors == []
    assert any("not yet on" in warning for warning in report.warnings)


def test_matching_version_is_silent():
    report = Report()
    compare_claim_to_pypi(
        "docs/changelog.md", "openadapt-flow", "1.24.0", "1.24.0", report
    )

    assert report.errors == []
    assert report.warnings == []


# --------------------------------------------------------------------------
# The guard must fail on the stale prose that actually shipped
# --------------------------------------------------------------------------


def test_the_exact_sentence_that_shipped_is_rejected(tmp_path, registry):
    """Restoring the pre-fix wording must fail the scan.

    This is the sentence that was live on docs.openadapt.ai/guides/security-review
    while it was false.
    """
    _tree(
        tmp_path,
        {
            "docs/guides/security-review.md": (
                "The retained non-simulated hosted-recorder qualification was "
                "run on Flow 1.8.0; the live runner and compiler now report "
                "the published Flow 1.23.0 identity.\n"
            )
        },
    )
    report = Report()
    scan_for_unregistered_claims(registry, report, root=tmp_path)

    assert report.errors, "the wording that actually shipped must be rejected"
    assert any("unregistered publication claim" in e for e in report.errors)
    assert any("security-review.md" in e for e in report.errors)


@pytest.mark.parametrize(
    "sentence",
    [
        "The live runner reports the published Flow 9.9.9 identity.",
        "Health reports the current published 9.9.9 runner identity.",
        "The latest published openadapt-flow is 9.9.9.",
        "9.9.9 is the current published release.",
    ],
)
def test_publication_claim_shapes_are_caught(tmp_path, registry, sentence):
    _tree(tmp_path, {"docs/guides/anything.md": sentence + "\n"})
    report = Report()
    scan_for_unregistered_claims(registry, report, root=tmp_path)

    assert report.errors, f"not caught: {sentence!r}"


def test_pinned_and_historical_wording_is_accepted(tmp_path, registry):
    """The corrected wording must pass; the guard must not ban version numbers.

    A deployment pin and a retained measurement are legitimate, frozen numbers.
    """
    _tree(
        tmp_path,
        {
            "docs/guides/hosted.md": (
                "That retained qualification used an `openadapt-flow` 1.8.0 "
                "worker. The live runner and compiler report the pinned "
                "managed-runtime 1.23.0 identity.\n"
            )
        },
    )
    report = Report()
    scan_for_unregistered_claims(registry, report, root=tmp_path)

    assert report.errors == []


def test_registered_pypi_latest_claim_is_allowed_through(tmp_path):
    """A publication claim IS allowed once it is registered to track PyPI."""
    registry = {
        "generated_pages": [],
        "claims": [
            {
                "id": "example",
                "kind": "pypi-latest",
                "package": "openadapt-flow",
                "version": "9.9.9",
                "locations": [],
            }
        ],
    }
    _tree(
        tmp_path,
        {"docs/x.md": "The current published openadapt-flow is 9.9.9.\n"},
    )
    report = Report()
    scan_for_unregistered_claims(registry, report, root=tmp_path)

    assert report.errors == []


def test_generated_pages_are_exempt_from_the_phrase_scan(tmp_path, registry):
    """Aggregated release notes are historical records, not authored claims."""
    _tree(
        tmp_path,
        {"docs/whats-new.md": "Realigned published evidence to Flow 9.9.9.\n"},
    )
    report = Report()
    scan_for_unregistered_claims(registry, report, root=tmp_path)

    assert report.errors == []


# --------------------------------------------------------------------------
# The registry cannot silently detach from the docs
# --------------------------------------------------------------------------


def test_reworded_claim_location_fails(tmp_path):
    """If the docs stop saying what the registry recorded, the guard fails."""
    registry = {
        "claims": [
            {
                "id": "pin",
                "kind": "pinned-deployment",
                "package": "openadapt-flow",
                "version": "1.23.0",
                "locations": [
                    {"file": "docs/a.md", "context": "pinned managed-runtime 1.23.0"}
                ],
            }
        ]
    }
    _tree(tmp_path, {"docs/a.md": "the published Flow 1.23.0 identity\n"})
    report = Report()
    check_claim_locations(registry, report, root=tmp_path)

    assert any("no longer contains its registered context" in e for e in report.errors)


def test_missing_claim_file_fails(tmp_path):
    registry = {
        "claims": [
            {
                "id": "pin",
                "kind": "pinned-deployment",
                "locations": [{"file": "docs/gone.md", "context": "anything"}],
            }
        ]
    }
    report = Report()
    check_claim_locations(registry, report, root=tmp_path)

    assert any("does not exist" in error for error in report.errors)


# --------------------------------------------------------------------------
# One source renders every active managed-runtime version
# --------------------------------------------------------------------------


def _rendered_registry(version="1.31.0"):
    return {
        "claims": [
            {
                "id": "managed-runtime",
                "kind": "pinned-deployment",
                "package": "openadapt-flow",
                "version": version,
                "rendered_locations": [
                    {"file": "docs/a.md", "count": 1},
                    {"file": "docs/b.md", "count": 2},
                ],
            }
        ]
    }


def _marked(claim_id="managed-runtime", version="1.31.0"):
    return (
        f"<!-- version-claim:{claim_id} -->{version}"
        f"<!-- /version-claim:{claim_id} -->"
    )


def test_one_registry_version_renders_every_registered_location(tmp_path):
    registry = _rendered_registry(version="1.32.0")
    _tree(
        tmp_path,
        {
            "docs/a.md": f"Flow {_marked()} artifact\n",
            "docs/b.md": f"runner {_marked()} and compiler {_marked()}\n",
        },
    )

    errors, changed = render_version_claims(registry, root=tmp_path)

    assert errors == []
    assert {path.name for path in changed} == {"a.md", "b.md"}
    assert "1.31.0" not in (tmp_path / "docs/a.md").read_text()
    assert (tmp_path / "docs/a.md").read_text().count("1.32.0") == 1
    assert (tmp_path / "docs/b.md").read_text().count("1.32.0") == 2


def test_render_check_fails_when_a_generated_value_is_stale(tmp_path):
    registry = _rendered_registry(version="1.32.0")
    _tree(
        tmp_path,
        {
            "docs/a.md": f"Flow {_marked()} artifact\n",
            "docs/b.md": f"runner {_marked()} and compiler {_marked()}\n",
        },
    )

    errors, changed = render_version_claims(registry, root=tmp_path, check=True)

    assert changed == []
    assert any("rendered version claims are stale" in error for error in errors)
    assert "1.31.0" in (tmp_path / "docs/a.md").read_text()


def test_render_check_fails_for_missing_or_extra_marker(tmp_path):
    registry = _rendered_registry()
    _tree(
        tmp_path,
        {
            "docs/a.md": f"Flow {_marked()} artifact\n",
            "docs/b.md": f"runner {_marked()}\n",
            "docs/unregistered.md": f"Flow {_marked('other')}\n",
        },
    )

    errors, _ = render_version_claims(registry, root=tmp_path, check=True)

    assert any("docs/b.md has 1 rendered marker" in error for error in errors)
    assert any("claim 'other'" in error for error in errors)


def test_render_refuses_malformed_marker_without_partial_writes(tmp_path):
    registry = _rendered_registry(version="1.32.0")
    malformed = "<!-- version-claim:managed-runtime -->1.31.0"
    _tree(
        tmp_path,
        {
            "docs/a.md": f"Flow {_marked()} artifact\n",
            "docs/b.md": f"runner {_marked()} and compiler {malformed}\n",
        },
    )

    errors, changed = render_version_claims(registry, root=tmp_path)

    assert changed == []
    assert any("incomplete or malformed" in error for error in errors)
    assert "1.31.0" in (tmp_path / "docs/a.md").read_text()


# --------------------------------------------------------------------------
# Changelog structure
# --------------------------------------------------------------------------


def test_changelog_newest_tag_ignores_installer_prereleases():
    """openadapt-desktop ships an engine vX.Y.Z and a desktop-vX.Y.Z installer.

    Only the engine tag corresponds to a PyPI distribution.
    """
    assert newest_semver_tag(["desktop-v0.14.0", "v0.14.0", "v0.13.1"]) == "0.14.0"
    assert newest_semver_tag(["desktop-v0.14.0"]) is None


def test_changelog_sections_parse():
    sections = parse_changelog(CHANGELOG.read_text(encoding="utf-8"))
    assert "openadapt-flow" in sections
    assert sections["openadapt-flow"], "flow section lists no releases"


def test_missing_changelog_section_fails(tmp_path):
    registry = {"changelog_tracks_pypi": {"openadapt-flow": "openadapt-flow"}}
    changelog = tmp_path / "changelog.md"
    changelog.write_text("# Changelog\n\n## OpenAdapt\n\n- **[v1.9.0](u)** (d)\n")
    report = Report()

    check_changelog_structure(registry, report, changelog_path=changelog)

    assert any("no '## openadapt-flow' section" in e for e in report.errors)


# --------------------------------------------------------------------------
# Today's tree
# --------------------------------------------------------------------------


def test_committed_docs_pass_the_offline_checks(registry):
    """Whatever else changes, the committed tree must be self-consistent."""
    report = Report()
    check_claim_locations(registry, report)
    render_errors, _ = render_version_claims(registry, check=True)
    report.errors.extend(render_errors)
    scan_for_unregistered_claims(registry, report)
    check_changelog_structure(registry, report)

    assert report.errors == []


def test_registry_is_well_formed(registry):
    """Every claim must declare what kind of claim it is, and why."""
    valid_kinds = {"pypi-latest", "pinned-deployment", "historical"}
    assert registry["claims"], "an empty registry guards nothing"
    for claim in registry["claims"]:
        assert claim["kind"] in valid_kinds, claim
        for field in ("id", "package", "version", "evidence", "verified_on"):
            assert claim.get(field), f"{claim.get('id')} missing {field}"
    ids = [claim["id"] for claim in registry["claims"]]
    assert len(ids) == len(set(ids)), "duplicate claim ids"
    assert json.dumps(registry), "registry must be JSON-serialisable"
