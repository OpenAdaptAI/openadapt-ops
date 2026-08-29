"""Tests for validate_docs.py"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from validate_docs import (
    check_empty_pages,
    check_product_docs_contract,
    check_retired_redirects,
    check_train_path_not_current_product,
)


def test_product_catalog_binds_all_admitted_targets_to_live_state():
    root = pathlib.Path(__file__).resolve().parent.parent
    content = (root / "docs" / "ecosystem" / "index.md").read_text()

    for target in ("agent", "capture", "cloud", "desktop", "docs", "flow", "openadapt"):
        assert f'data-openadapt-production-target="{target}"' in content
    assert content.count("data-openadapt-production-target=") == 7
    assert "**Experimental**" in content
    assert "**Research**" in content


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


def _write_contract_docs(root):
    pages = {
        "index.md": (
            "# Verified last-mile execution for agents\n\nThe default reader "
            "is the calling agent. "
            "[Production status](reference/production-lifecycle.md)"
        ),
        "ecosystem/index.md": (
            "# Product components and release admission\n\n"
            + "\n".join(
                f'<span data-openadapt-production-target="{target}">'
                "No current verified Production admission.</span>"
                for target in (
                    "agent",
                    "capture",
                    "cloud",
                    "desktop",
                    "docs",
                    "flow",
                    "openadapt",
                )
            )
            + "\n\nopenadapt-privacy is **Experimental**. "
            "openadapt-evals is **Research**."
        ),
        "get-started/index.md": (
            "# Get started\n\nInstall with `pip install openadapt`, then "
            "`openadapt quickstart` and `openadapt quickstart --break-it`. "
            "`claude mcp add openadapt`. Never summarize halt as success. "
            "The bundled workflow is a tutorial. Continue in "
            "[Your first workflow](first-workflow.md)."
        ),
        "get-started/first-workflow.md": (
            "---\n"
            "first_workflow_scope: read_only\n"
            "first_write_admission: qualification_required\n"
            "---\n\n"
            "# Your first workflow\n\nInstall with `pip install openadapt` and "
            "record a bounded workflow."
        ),
        "get-started/what-works-today.md": (
            "# Qualification evidence\n\n## Integrated product matrix\n\n"
            "Hosted execution is a Supported / public offer at $500/month. "
            "Hosted browser recorder evidence is bounded on `openadapt-flow` 1.8.0. "
            "Authenticated live health proves service identity. Three production "
            "pre-payment trials passed; the first genuine customer transaction "
            "extends the evidence."
        ),
        "guides/hosted.md": (
            "# Hosted browser execution\n\nA sanitized derivative is inspected in "
            "a local viewer and bound to a cryptographic derivative hash. "
            "Unknown or unresolved content is refused. "
            "## Destination-aware decisions\n\nProduction documentation explains why "
            "production fails closed instead of silently using mock mode."
        ),
        "guides/security-review.md": (
            "# Data-boundary answers\n\n## Updates and rollback\n"
        ),
        "reference/documentation-governance.md": (
            "# Documentation source of truth\n\n"
            "## Noncanonical documentation trees\n"
        ),
        "reference/compatibility.md": (
            "# Versions and compatibility\n\n`pip install openadapt`\n\n"
            "`openadapt-flow >=1.7,<2`\n\n"
            "`openadapt-flow >=1.22,<2` + `openadapt-capture >=1.1.0`\n\n"
            "Production deployments should pin the exact versions."
        ),
        "reference/production-lifecycle.md": (
            "# Production admission\n\nA qualified workflow requires an active signed "
            "admission and at least three trials per task per condition. Report "
            "each silent-incorrect-success and over-halt count. Expected "
            "uncertain-delivery faults return RECONCILIATION_REQUIRED without a blind "
            "retry."
        ),
        "packages/openadapt.md": (
            "---\nredirect_to: /ecosystem/\n---\n\n"
            "# OpenAdapt package documentation moved\n\n"
            "`pip install openadapt`"
        ),
    }
    for relative_path, content in pages.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return pages


def test_product_docs_contract_passes_for_product_first_nav(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

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
    first_workflow = docs_dir / "get-started/first-workflow.md"
    content = first_workflow.read_text()
    expected = {
        "first_workflow_scope": "read_only",
        "first_write_admission": "qualification_required",
    }[field]
    first_workflow.write_text(
        content.replace(f"{field}: {expected}", f"{field}: {bad_value}")
    )
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

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
    first_workflow = docs_dir / "get-started/first-workflow.md"
    first_workflow.write_text(
        first_workflow.read_text() + f"\n`openadapt quickstart {flag}`\n"
    )
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any(
        "Failure-demo flag is forbidden in first-workflow onboarding" in issue
        and flag in issue
        for issue in issues
    )


def test_product_docs_contract_rejects_missing_page_and_package_first_nav(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    (docs_dir / "guides/security-review.md").unlink()
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Packages:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "  - Reference:\n"
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)
    assert any("Missing required product page" in issue for issue in issues)
    assert any("Package-first top-level navigation" in issue for issue in issues)


def test_product_docs_contract_rejects_stale_prelaunch_copy(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    hosted = docs_dir / "guides/hosted.md"
    hosted.write_text(hosted.read_text() + "\nBeta launch candidate\n")
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Stale prelaunch copy" in issue for issue in issues)


def test_product_docs_contract_rejects_not_actively_admitted_label(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    hosted = docs_dir / "guides/hosted.md"
    hosted.write_text(hosted.read_text() + "\nNot actively admitted\n")
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Stale prelaunch copy" in issue for issue in issues)


def test_product_docs_contract_rejects_static_maturity_copy(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    hosted = docs_dir / "guides/hosted.md"
    hosted.write_text(hosted.read_text() + "\nThe recorder is Experimental.\n")
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Static product-target maturity label" in issue for issue in issues)


def test_product_docs_contract_rejects_static_target_state_in_catalog(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    ecosystem = docs_dir / "ecosystem/index.md"
    ecosystem.write_text(
        ecosystem.read_text().replace(
            '<span data-openadapt-production-target="agent">',
            '**Beta** <span data-openadapt-production-target="agent">',
        )
    )
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Product components: ecosystem/index.md\n"
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any(
        "Static product-target maturity label in ecosystem/index.md" in issue
        for issue in issues
    )


def test_product_docs_contract_rejects_competing_install_identity(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    first_workflow = docs_dir / "get-started/first-workflow.md"
    first_workflow.write_text(
        first_workflow.read_text()
        + "\nPackage names during the transition: pip install openadapt-flow\n"
    )
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

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
    assert check_retired_redirects(root / "docs") == []


def test_retired_redirect_missing_file_is_an_issue(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    issues = check_retired_redirects(docs_dir)

    assert any(
        "Missing Flow-first redirect for retired route: getting-started/quickstart.md"
        in issue
        for issue in issues
    )
