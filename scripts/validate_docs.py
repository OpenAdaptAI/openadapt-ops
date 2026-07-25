"""Validate the generated docs site."""

import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
MKDOCS_FILE = ROOT / "mkdocs.yml"

REQUIRED_PUBLIC_PAGES = {
    "get-started/what-works-today.md": (
        "Qualification evidence",
        "Integrated product matrix",
        "Hosted execution",
        "$500/month",
        "Supported / public offer",
        "Hosted browser recorder",
        "`openadapt-flow` 1.8.0",
        "Authenticated live health",
        "production pre-payment trials",
        "first genuine customer",
    ),
    "guides/hosted.md": (
        "sanitized derivative",
        "local viewer",
        "cryptographic derivative hash",
        "Unknown or unresolved content",
        "Destination-aware decisions",
        "production fails closed instead of silently using mock mode",
    ),
    "guides/security-review.md": ("Data-boundary answers", "Updates and rollback"),
    "reference/documentation-governance.md": (
        "source of truth",
        "Noncanonical documentation trees",
    ),
    "reference/compatibility.md": (
        "pip install openadapt",
        "`openadapt-flow >=1.7,<2`",
        "`openadapt-flow >=1.22,<2` + `openadapt-capture >=1.1.0`",
        "`openadapt-capture >=1.1.0`",
        "Production deployments should pin the exact versions",
    ),
    "packages/openadapt.md": (
        'content="0; url=/ecosystem/"',
        "pip install openadapt",
    ),
}

REQUIRED_NAV_PAGES = set(REQUIRED_PUBLIC_PAGES) - {"packages/openadapt.md"}

STALE_PRELAUNCH_MARKERS = {
    "Beta launch candidate",
    "full paid production lifecycle remains pending",
    "not a public availability statement",
}


def check_empty_pages(docs_dir=None):
    """Check for empty or stub-only doc pages."""
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)
    issues = []
    for md_file in docs_dir.rglob("*.md"):
        content = md_file.read_text().strip()
        if len(content) < 20:
            issues.append(f"Nearly empty page: {md_file.relative_to(docs_dir)}")
    return issues


def check_product_docs_contract(docs_dir=None, mkdocs_file=None):
    """Keep sync/deploy from erasing product truth or restoring package-first IA."""
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)
    mkdocs_file = pathlib.Path(mkdocs_file or MKDOCS_FILE)
    issues = []

    for relative_path, markers in REQUIRED_PUBLIC_PAGES.items():
        page = docs_dir / relative_path
        if not page.exists():
            issues.append(f"Missing required product page: {relative_path}")
            continue
        content = page.read_text()
        for marker in markers:
            if marker not in content:
                issues.append(f"Missing product marker in {relative_path}: {marker}")

    if not mkdocs_file.exists():
        issues.append(f"Missing MkDocs config: {mkdocs_file}")
        return issues

    nav = mkdocs_file.read_text()
    for relative_path in REQUIRED_NAV_PAGES:
        if relative_path not in nav:
            issues.append(f"Required product page missing from navigation: {relative_path}")
    if "\n  - Packages:" in nav:
        issues.append("Package-first top-level navigation is forbidden; use Ecosystem/Reference")
    # MkDocs permits Python-specific YAML tags in extension configuration.
    # Parse only the final nav section with the safe loader.
    nav_section = nav[nav.index("\nnav:") + 1 :] if "\nnav:" in nav else nav
    nav_config = yaml.safe_load(nav_section) or {}
    # The package/repository catalog must stay nested under the reference-style
    # engineering section rather than promoted to a package-first top level. The
    # five-section IA renamed that section "Internals"; accept either name so the
    # guard tracks intent, not a specific label.
    catalog_section_names = {"Reference", "Internals"}
    reference_entries = [
        item
        for entry in nav_config.get("nav", [])
        if isinstance(entry, dict)
        for name, items in entry.items()
        if name in catalog_section_names and isinstance(items, list)
        for item in items
    ]
    catalog_is_under_reference = any(
        item == "ecosystem/index.md"
        or (isinstance(item, dict) and "ecosystem/index.md" in item.values())
        for item in reference_entries
    )
    if not catalog_is_under_reference:
        issues.append(
            "Package and repository lifecycle catalog must remain under the "
            "Reference/Internals section"
        )

    public_text = "\n".join(
        path.read_text() for path in docs_dir.rglob("*.md") if path.is_file()
    )
    home_page = docs_dir / "index.md"
    if home_page.exists():
        home_text = home_page.read_text()
        for marker in ("Show it any task", "replays exactly"):
            if marker in home_text:
                issues.append(f"Overbroad documentation homepage copy: {marker}")
    else:
        issues.append("Missing documentation homepage: index.md")
    for marker in (
        "Package names during the transition",
        "pip install openadapt-flow",
    ):
        for relative_path in (
            "get-started/index.md",
            "get-started/first-workflow.md",
        ):
            page = docs_dir / relative_path
            if page.exists() and marker in page.read_text():
                issues.append(
                    f"Competing end-user install identity in {relative_path}: {marker}"
                )
    for marker in STALE_PRELAUNCH_MARKERS:
        if marker in public_text:
            issues.append(f"Stale prelaunch copy: {marker}")

    return issues


def run_mkdocs_build(strict=False):
    """Run mkdocs build and return (success, output).

    Curated product docs should pass strict mode. The caller may opt out only
    for a local diagnostic build.
    """
    cmd = ["mkdocs", "build"]
    if strict:
        cmd.append("--strict")
    cmd.extend(["--site-dir", str(ROOT / "_site_check")])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    # Clean up
    site_dir = ROOT / "_site_check"
    if site_dir.exists():
        import shutil
        shutil.rmtree(site_dir)
    return result.returncode == 0, result.stdout + result.stderr


def validate():
    """Run all validation checks. Returns list of issues."""
    issues = []

    # Check for empty pages
    empty_issues = check_empty_pages()
    issues.extend(empty_issues)

    contract_issues = check_product_docs_contract()
    issues.extend(contract_issues)

    # Run mkdocs build
    success, output = run_mkdocs_build(strict=True)
    if not success:
        issues.append(f"mkdocs build --strict failed:\n{output}")

    if issues:
        print(f"Validation found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Validation passed!")

    return issues


if __name__ == "__main__":
    issues = validate()
    sys.exit(1 if issues else 0)
