"""Tests for validate_docs.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from validate_docs import check_empty_pages, check_product_docs_contract


def test_openadapt_agent_catalog_describes_active_v2_bridge():
    root = pathlib.Path(__file__).resolve().parent.parent
    content = (root / "docs" / "ecosystem" / "index.md").read_text()

    assert "openadapt-agent](https://github.com/OpenAdaptAI/openadapt-agent)" in content
    assert "Active v2 bridge" in content
    assert "repository itself is active" in content
    assert "Superseded execution direction being folded into `openadapt-flow`" not in content


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
            "# OpenAdapt\n\nShow it a repeated workflow. OpenAdapt compiles it "
            "into governed, deterministic replay."
        ),
        "get-started/index.md": (
            "# Get started\n\nInstall with `pip install openadapt` and use "
            "`openadapt flow`."
        ),
        "get-started/first-workflow.md": (
            "# Your first workflow\n\nInstall with `pip install openadapt` and "
            "record a bounded workflow."
        ),
        "get-started/what-works-today.md": (
            "# Qualification evidence\n\n## Integrated product matrix\n\n"
            "Hosted execution is a Beta / public offer at $500/month. "
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
            "`openadapt-flow >=1.7,<2`\n\n`openadapt-capture >=0.6`\n\n"
            "Production deployments should pin the exact versions."
        ),
        "packages/openadapt.md": (
            "# OpenAdapt package documentation moved\n\n"
            '<meta http-equiv="refresh" content="0; url=/ecosystem/">\n\n'
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
