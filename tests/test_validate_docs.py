"""Tests for validate_docs.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from validate_docs import check_empty_pages, check_product_docs_contract


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
        "get-started/what-works-today.md": (
            "# Integrated product matrix\n\nHosted execution is a Beta launch candidate. "
            "Hosted browser recorder evidence is bounded on `openadapt-flow` 1.8.0. "
            "Authenticated live health proves service identity. The full paid "
            "production lifecycle remains pending."
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


def test_product_docs_contract_rejects_unqualified_hosted_availability(tmp_path):
    docs_dir = tmp_path / "docs"
    pages = _write_contract_docs(docs_dir)
    hosted = docs_dir / "guides/hosted.md"
    hosted.write_text(hosted.read_text() + "\nStart hosted checkout\n")
    mkdocs_file = tmp_path / "mkdocs.yml"
    mkdocs_file.write_text(
        "nav:\n  - Reference:\n"
        + "".join(f"    - {path}\n" for path in pages)
        + "    - Package and repository lifecycle: ecosystem/index.md\n"
    )

    issues = check_product_docs_contract(docs_dir, mkdocs_file)

    assert any("Unqualified hosted-availability claim" in issue for issue in issues)
