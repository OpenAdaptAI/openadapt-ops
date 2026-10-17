"""Tests for validate_docs.py"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from validate_docs import (
    check_empty_pages,
    check_product_docs_contract,
    check_retired_public_claims,
    check_retired_redirects,
    check_train_path_not_current_product,
    redirect_map,
)


def test_release_status_binds_all_admitted_targets_to_live_state():
    root = pathlib.Path(__file__).resolve().parent.parent
    content = (root / "docs" / "security" / "release-integrity.md").read_text()

    for target in ("agent", "capture", "cloud", "desktop", "docs", "flow", "openadapt"):
        assert f'data-openadapt-production-target="{target}"' in content
    assert content.count("data-openadapt-production-target=") == 7


def test_check_empty_pages_finds_issues(tmp_path):
    """Should flag pages with less than 20 chars."""
    (tmp_path / "short.md").write_text("# Hi")
    (tmp_path / "ok.md").write_text("# This is a proper page\n\nWith enough content to pass.")

    issues = check_empty_pages(docs_dir=tmp_path)
    assert len(issues) == 1
    assert "short.md" in issues[0]


def test_check_empty_pages_no_issues(tmp_path):
    """Should return empty list when all pages are adequate."""
    (tmp_path / "good.md").write_text("# Good Page\n\nThis has enough content to be useful.")
    issues = check_empty_pages(docs_dir=tmp_path)
    assert len(issues) == 0


def test_check_empty_pages_nested(tmp_path):
    """Should recurse into subdirectories."""
    sub = tmp_path / "packages"
    sub.mkdir()
    (sub / "tiny.md").write_text("")
    (sub / "fine.md").write_text("# Fine package\n\nLots of good documentation here.")

    issues = check_empty_pages(docs_dir=tmp_path)
    assert len(issues) == 1
    assert "tiny.md" in issues[0]


TARGETS = ("agent", "capture", "cloud", "desktop", "docs", "flow", "openadapt")


def _write_contract_docs(root):
    pages = {
        "index.md": (
            "# OpenAdapt\n\nOne or more demonstrations: one or more demonstrations. "
            "[Quickstart](tutorials/quickstart.md), "
            "[an agent](how-to/connect-an-agent.md), "
            "[release status](security/release-integrity.md), "
            "[limits](explanation/limits.md)."
        ),
        "tutorials/quickstart.md": (
            "# Quickstart\n\n`pip install openadapt`, then "
            "`openadapt quickstart --break-it`. The halted rerun reads "
            "`RECONCILIATION_REQUIRED`."
        ),
        "tutorials/first-workflow.md": (
            "---\n"
            "first_workflow_scope: read_only\n"
            "first_write_admission: qualification_required\n"
            "---\n\n"
            "# Your first workflow\n\nInstall with `pip install openadapt` and "
            "record a bounded workflow."
        ),
        "how-to/connect-an-agent.md": (
            "# Connect an agent\n\n`claude mcp add openadapt`. Never summarize "
            "a halt as success. Never retry `not_sure_if_saved`."
        ),
        "security/index.md": "# Security\n\n## Attestation status\n\nNo SOC 2 report.",
        "security/data-handling.md": (
            "# Data handling\n\nA person reviews the sanitized copy in a viewer "
            "that listens only on this computer. Cloud checks the SHA-256. Files it "
            "can't handle refuse the whole copy."
        ),
        "security/release-integrity.md": (
            "# Release integrity\n\n"
            + "\n".join(
                f'<span data-openadapt-production-target="{target}">'
                "No current verified Production admission.</span>"
                for target in TARGETS
            )
            + "\n\nEvidence needs at least three trials per task per\ncondition, "
            "silent-incorrect-success and over-halt counts, and uncertain-delivery "
            "trials that end RECONCILIATION_REQUIRED without a blind retry. A run "
            "needs an active signed admission. Tutorial rows are 0.0.0-synthetic."
        ),
        "reference/compatibility.md": (
            "# Versions and compatibility\n\n`pip install openadapt`\n\n"
            "## Current compatibility contract\n\n"
            "Pin the exact versions a workflow was qualified on."
        ),
        "reference/outcomes.md": (
            "# Run outcomes\n\nStopped before saving is HALTED_BEFORE_EFFECT. "
            "Check the record is RECONCILIATION_REQUIRED. Didn't finish is "
            "FAILED_PLATFORM."
        ),
        "reference/packages.md": "# Packages\n\n`pip install openadapt`",
    }
    for relative_path, content in pages.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return pages


def _write_nav(tmp_path, pages, packages_section="Reference"):
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Developers:\n      - Guides:\n"
        + "".join(
            f"          - {path}\n" for path in pages if path != "reference/packages.md"
        )
        + f"      - {packages_section}:\n"
        + "          - Packages: reference/packages.md\n"
    )
    return mkdocs_file


def test_product_docs_contract_passes_for_product_first_nav(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    mkdocs_file = _write_nav(tmp_path, pages)

    assert check_product_docs_contract(docs_dir, mkdocs_file) == []


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("first_workflow_scope", "read_write"),
        ("first_write_admission", "replay_allowed"),
    ),
)
def test_product_docs_contract_rejects_wrong_first_workflow_contract(
    tmp_path, field, bad_value
):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    first_workflow = docs_dir / "tutorials/first-workflow.md"
    content = first_workflow.read_text()
    expected = {
        "first_workflow_scope": "read_only",
        "first_write_admission": "qualification_required",
    }[field]
    first_workflow.write_text(
        content.replace(f"{field}: {expected}", f"{field}: {bad_value}")
    )
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any(
        "First-workflow safety contract requires" in issue and field in issue
        for issue in issues
    )


@pytest.mark.parametrize(
    "flag",
    ("--break-it", "--simulate-rejected-write"),
)
def test_product_docs_contract_rejects_failure_demo_in_first_workflow(
    tmp_path, flag
):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    first_workflow = docs_dir / "tutorials/first-workflow.md"
    first_workflow.write_text(
        first_workflow.read_text() + f"\n`openadapt quickstart {flag}`\n"
    )
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any(
        "Failure-demo flag is forbidden in first-workflow onboarding" in issue
        and flag in issue
        for issue in issues
    )


def test_product_docs_contract_rejects_missing_page_and_package_first_nav(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    (docs_dir / "security/index.md").unlink()
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Packages:\n"
        + "".join(f"    - {path}\n" for path in pages)
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)
    assert any("Missing required product page" in issue for issue in issues)
    assert any("Package-first top-level navigation" in issue for issue in issues)
    assert any("must remain under a Reference section" in issue for issue in issues)


def test_product_docs_contract_rejects_stale_prelaunch_copy(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    hosted = docs_dir / "security/data-handling.md"
    hosted.write_text(hosted.read_text() + "\nBeta launch candidate\n")
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Stale prelaunch copy" in issue for issue in issues)


def test_product_docs_contract_rejects_not_actively_admitted_label(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    hosted = docs_dir / "security/data-handling.md"
    hosted.write_text(hosted.read_text() + "\nNot actively admitted\n")
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Stale prelaunch copy" in issue for issue in issues)


def test_product_docs_contract_rejects_static_maturity_copy(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    hosted = docs_dir / "security/data-handling.md"
    hosted.write_text(hosted.read_text() + "\nThe recorder is Experimental.\n")
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Static product-target maturity label" in issue for issue in issues)


def test_product_docs_contract_rejects_static_target_state_on_status_page(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    status = docs_dir / "security/release-integrity.md"
    status.write_text(
        status.read_text().replace(
            '<span data-openadapt-production-target="agent">',
            '**Beta** <span data-openadapt-production-target="agent">',
        )
    )
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any(
        "Static product-target maturity label in security/release-integrity.md" in issue
        for issue in issues
    )


def test_product_docs_contract_requires_all_seven_targets(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    status = docs_dir / "security/release-integrity.md"
    status.write_text(status.read_text().replace('data-openadapt-production-target="docs"', ""))
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("seven targets" in issue for issue in issues)


def test_product_docs_contract_rejects_competing_install_identity(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    first_workflow = docs_dir / "tutorials/first-workflow.md"
    first_workflow.write_text(
        first_workflow.read_text()
        + "\nPackage names during the transition: pip install openadapt-flow\n"
    )
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Competing end-user install identity" in issue for issue in issues)


def test_train_path_copy_is_rejected(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "get-started").mkdir()
    (docs_dir / "get-started" / "index.md").write_text(
        "# Get started\n\nopenadapt train start --capture my-task\n"
    )

    issues = check_train_path_not_current_product(docs_dir)

    assert any(
        "Retired capture-then-train copy" in issue
        and "openadapt train" in issue
        for issue in issues
    )


def test_train_path_allowlist_skips_changelog(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "changelog.md").write_text(
        "# Changelog\n\n- restore openadapt train for a historical note\n"
    )

    assert check_train_path_not_current_product(docs_dir) == []


def test_real_docs_have_no_train_path_copy():
    root = pathlib.Path(__file__).resolve().parent.parent
    assert check_train_path_not_current_product(root / "docs") == []


def test_real_docs_keep_retired_flow_redirects():
    root = pathlib.Path(__file__).resolve().parent.parent
    assert check_retired_redirects(root / "docs", root / "mkdocs.yml") == []


def test_real_redirect_map_covers_every_retired_route():
    root = pathlib.Path(__file__).resolve().parent.parent
    assert len(redirect_map(root / "mkdocs.yml")) >= 100


def test_retired_redirect_missing_entry_is_an_issue(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text("plugins:\n  - search\n")

    issues = check_retired_redirects(docs_dir, mkdocs_file)

    assert any(
        "Missing redirect for retired route: getting-started/quickstart.md" in issue
        for issue in issues
    )


def test_redirect_to_a_missing_page_is_an_issue(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "old.md").write_text("# Old page still here")
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "plugins:\n  - redirects:\n      redirect_maps:\n        old.md: new.md\n"
    )

    issues = check_retired_redirects(docs_dir, mkdocs_file)

    assert any("Redirect source is also a page: old.md" in issue for issue in issues)
    assert any("points at a missing page: new.md" in issue for issue in issues)


def test_retired_public_claims_are_flagged(tmp_path):
    """A corrected price, anchor, or statistic must not come back."""
    (tmp_path / "commercial").mkdir()
    (tmp_path / "commercial" / "index.md").write_text(
        "# Offers\n\nEvery price and claim matches the pricing page. "
        "OpenAdapt Cloud is $500.00/month."
    )
    (tmp_path / "index.md").write_text(
        "# Home\n\n[Demo](https://openadapt.ai/#demo). "
        "A screen check accepted 54 of 90 wrong results."
    )
    (tmp_path / "llms.txt").write_text("Hosted: $500/month")
    (tmp_path / "evaluate").mkdir()
    (tmp_path / "evaluate" / "example.md").write_text(
        "# Example\n\n[Case](https://openadapt.ai/customers/example)."
    )

    issues = check_retired_public_claims(docs_dir=tmp_path)

    joined = "\n".join(issues)
    assert "commercial/index.md: 'Every price and claim matches'" in joined
    assert "commercial/index.md: '$500.00/month'" in joined
    assert "index.md: 'openadapt.ai/#demo'" in joined
    assert "index.md: '54 of 90 wrong'" in joined
    assert "llms.txt: '$500/month'" in joined
    assert "evaluate/example.md: 'openadapt.ai/customers/'" in joined


def test_retired_public_claims_allow_generated_history(tmp_path):
    """Generated history pages may quote a retired claim."""
    (tmp_path / "changelog.md").write_text("# Changelog\n\nCloud moved off $500/month.")
    (tmp_path / "whats-new.md").write_text("# What's new\n\nWas $500.00/month.")
    (tmp_path / "index.md").write_text("# Home\n\nSee the pricing page.")

    assert check_retired_public_claims(docs_dir=tmp_path) == []


def test_live_docs_carry_no_retired_public_claim():
    assert check_retired_public_claims() == []


def test_product_docs_contract_requires_outcome_derived_results(tmp_path):
    """The outcomes page must keep its transaction-outcome mapping."""
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    (docs_dir / "reference/outcomes.md").write_text(
        "# Run outcomes\n\nStopped for review is HALTED."
    )
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("RECONCILIATION_REQUIRED" in issue for issue in issues)
    assert any("HALTED_BEFORE_EFFECT" in issue for issue in issues)


def test_product_docs_contract_rejects_packages_map_outside_reference(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    mkdocs_file = _write_nav(tmp_path, pages, packages_section="Guides 2")

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("must remain under a Reference section" in issue for issue in issues)


def test_product_docs_contract_rejects_mcp_track_without_halt_rule(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    (docs_dir / "how-to/connect-an-agent.md").write_text("# Connect an agent\n")
    mkdocs_file = _write_nav(tmp_path, pages)

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Never summarize a halt as success" in issue for issue in issues)
