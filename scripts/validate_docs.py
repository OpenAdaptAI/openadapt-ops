"""Validate the generated docs site."""

import pathlib
import re
import subprocess
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_private_names  # noqa: E402
import flow_cli_reference  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
MKDOCS_FILE = ROOT / "mkdocs.yml"

REQUIRED_PUBLIC_PAGES = {
    # The home page routes developers and reviewers, states the demonstration
    # model plainly, and points at the live release status and the limits.
    "index.md": (
        "one or more demonstrations",
        "tutorials/quickstart.md",
        "how-to/connect-an-agent.md",
        "security/release-integrity.md",
        "explanation/limits.md",
    ),
    # Fault-first onboarding: the first run shows a refused false success.
    "tutorials/quickstart.md": (
        "pip install",
        "--break-it",
        "RECONCILIATION_REQUIRED",
    ),
    "how-to/connect-an-agent.md": (
        "claude mcp add --scope user openadapt",
        "Never summarize a halt as success",
        "not_sure_if_saved",
    ),
    "security/index.md": ("Attestation status", "SOC 2"),
    # Nothing raw is uploaded: a person reviews a sanitized copy, the upload is
    # bound to its hash, and content the sanitizer can't handle is refused.
    "security/data-handling.md": (
        "sanitized copy",
        "viewer that listens only on this computer",
        "SHA-256",
        "refuse the whole copy",
    ),
    # Release admission evidence and the live per-target state.
    "security/release-integrity.md": (
        "data-openadapt-production-target",
        "at least three trials per task per condition",
        "silent-incorrect-success",
        "over-halt",
        "active signed admission",
        "RECONCILIATION_REQUIRED",
        "without a blind",
        "0.0.0-synthetic",
    ),
    # The ranges themselves are compared with the released package metadata
    # by scripts/check_published_version_claims.py, so only structure is
    # required here.
    "reference/compatibility.md": (
        "pip install openadapt",
        "## Current compatibility contract",
        "Pin the exact versions",
    ),
    # Run results stay derived from the transaction outcome: only a proven
    # no-effect outcome may say nothing was written.
    "reference/outcomes.md": (
        "HALTED_BEFORE_EFFECT",
        "RECONCILIATION_REQUIRED",
        "FAILED_PLATFORM",
    ),
}

REQUIRED_NAV_PAGES = set(REQUIRED_PUBLIC_PAGES)

FIRST_WORKFLOW_PAGE = "tutorials/first-workflow.md"
INSTALL_IDENTITY_PAGES = ("tutorials/quickstart.md", "tutorials/first-workflow.md")
PACKAGES_PAGE = "reference/packages.md"
RELEASE_STATUS_PAGE = "security/release-integrity.md"

FIRST_WORKFLOW_CONTRACT = {
    "first_workflow_scope": "read_only",
    "first_write_admission": "qualification_required",
}
FIRST_WORKFLOW_FORBIDDEN_FLAGS = (
    "--break-it",
    "--simulate-rejected-write",
)

# Public claims that were corrected and must not return. Each one was live on
# docs.openadapt.ai and contradicted the public site or its own evidence.
# Generated history pages may quote the old text.
RETIRED_PUBLIC_CLAIMS = {
    "$500/month": "retired Cloud price; link openadapt.ai/pricing instead",
    "$500.00/month": "retired Cloud price; link openadapt.ai/pricing instead",
    "Every price and claim matches": "false claim; link the pricing page instead",
    "openadapt.ai/#demo": "the home page has no #demo anchor; use app.openadapt.ai/demo",
    "pricing#cloud-preview": "the pricing page has no #cloud-preview anchor; use #hosted",
    "54 of 90 wrong": "misstated base; the fault test's screen check passed 54 of 72 wrong runs",
    "openadapt.ai/customers/": "withdrawn customer case page; the docs publish no customer results",
}
RETIRED_CLAIM_ALLOWLIST = {
    "changelog.md",
    "whats-new.md",
    "reference/cli-help.md",
}

STALE_PRELAUNCH_MARKERS = {
    "Available for qualification",
    "Beta launch candidate",
    "full paid production lifecycle remains pending",
    "not a public availability statement",
    "not actively admitted",
    "Not actively admitted",
}

STATIC_MATURITY_PATTERN = re.compile(
    r"\b(?:beta|experimental|early access|exploratory)\b"
    r"|\breference path\b|\bbrowser-only\b",
    re.IGNORECASE,
)
TARGET_STATE_DOC_PATHS = {
    "index.md",
    "how-to/deploy.md",
    "how-to/desktop.md",
    "security/data-handling.md",
    "security/deployment-boundaries.md",
    "security/evidence.md",
    "security/index.md",
    "security/release-integrity.md",
}
PRODUCTION_TARGET_IDS = {
    "agent",
    "capture",
    "cloud",
    "desktop",
    "docs",
    "flow",
    "openadapt",
}

# Old docs.openadapt.ai URLs that taught capture-then-train, mirrored a
# research README as if it were the product, or were guessed paths. Each must
# keep redirecting, through the mkdocs-redirects map in mkdocs.yml, to the
# current page, so a crawler that still holds the URL drops the old snippet.
RETIRED_REDIRECTS = {
    "architecture.md": "explanation/how-it-works.md",
    "cli.md": "reference/cli.md",
    "getting-started/index.md": "tutorials/quickstart.md",
    "getting-started/installation.md": "tutorials/quickstart.md",
    "getting-started/permissions.md": "how-to/desktop.md",
    "getting-started/quickstart.md": "tutorials/quickstart.md",
    "start/index.md": "tutorials/quickstart.md",
    "LEGACY_FREEZE.md": "index.md",
    "legacy/freeze.md": "index.md",
    "packages/capture.md": "reference/packages.md",
    "packages/evals.md": "reference/packages.md",
    "packages/grounding.md": "reference/packages.md",
    "packages/index.md": "reference/packages.md",
    "packages/ml.md": "reference/packages.md",
    "packages/openadapt-bootstrap.md": "reference/packages.md",
    "packages/openadapt-evals.md": "reference/packages.md",
    "packages/openadapt-grounding.md": "reference/packages.md",
    "packages/openadapt-ml.md": "reference/packages.md",
    "packages/openadapt-retrieval.md": "reference/packages.md",
    "packages/openadapt-viewer.md": "reference/packages.md",
    "packages/privacy.md": "reference/packages.md",
    "packages/retrieval.md": "reference/packages.md",
    "packages/viewer.md": "reference/packages.md",
}

# Phrases that describe the retired train-a-VLM happy path as current product.
# Auto-generated changelog pages may quote a historical PR title; everything
# else must not.
FORBIDDEN_TRAIN_PATH_PHRASES = (
    "openadapt train",
    "openadapt capture start",
    "openadapt capture stop",
    "openadapt capture view",
    "qwen3vl",
    "training_output/",
    "pip install openadapt-ml",
    "from openadapt_ml",
    "AgentPolicy",
    "Learn a Policy",
    "Learn an agent policy",
    "Collect a Demonstration",
    "generative RPA",
    "Generative RPA",
    "LMM-on-the-desktop",
    "LMM on the desktop",
    "demo-conditioned AI agents",
    "legacy model-training path",
)

TRAIN_PATH_ALLOWLIST = {
    "changelog.md",
    "whats-new.md",
    "reference/cli-help.md",
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


def _frontmatter(content):
    """Return a page's YAML frontmatter, or an empty mapping when invalid."""
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        metadata = yaml.safe_load(content[4:end]) or {}
    except yaml.YAMLError:
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _flat(text):
    return " ".join(text.split())


def _nav_sections(entries, trail=()):
    """Yield (section names, page path) for every page in a nav tree."""
    for entry in entries or []:
        if isinstance(entry, str):
            yield trail, entry
        elif isinstance(entry, dict):
            for name, value in entry.items():
                if isinstance(value, list):
                    yield from _nav_sections(value, trail + (name,))
                elif isinstance(value, str):
                    yield trail, value


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
        content = _flat(page.read_text())
        for marker in markers:
            if _flat(marker) not in content:
                issues.append(f"Missing product marker in {relative_path}: {marker}")

    first_workflow = docs_dir / FIRST_WORKFLOW_PAGE
    if not first_workflow.is_file():
        issues.append(f"Missing required product page: {FIRST_WORKFLOW_PAGE}")
    else:
        first_workflow_text = first_workflow.read_text()
        first_workflow_metadata = _frontmatter(first_workflow_text)
        for field, expected in FIRST_WORKFLOW_CONTRACT.items():
            actual = first_workflow_metadata.get(field)
            if actual != expected:
                issues.append(
                    "First-workflow safety contract requires "
                    f"{field}: {expected}; found: {actual}"
                )
        for flag in FIRST_WORKFLOW_FORBIDDEN_FLAGS:
            if flag in first_workflow_text:
                issues.append(
                    "Failure-demo flag is forbidden in first-workflow "
                    f"onboarding: {flag}"
                )

    if not mkdocs_file.exists():
        issues.append(f"Missing MkDocs config: {mkdocs_file}")
        return issues

    nav = mkdocs_file.read_text()
    if "\n  - Packages:" in nav:
        issues.append("Package-first top-level navigation is forbidden; use Reference")
    # MkDocs permits Python-specific YAML tags in extension configuration.
    # Parse only the final nav section with the safe loader.
    nav_section = nav[nav.index("\nnav:") + 1 :] if "\nnav:" in nav else nav
    nav_config = yaml.safe_load(nav_section) or {}
    nav_pages = dict(
        (page, trail) for trail, page in _nav_sections(nav_config.get("nav", []))
    )
    for relative_path in sorted(REQUIRED_NAV_PAGES | {FIRST_WORKFLOW_PAGE}):
        if relative_path not in nav_pages:
            issues.append(f"Required product page missing from navigation: {relative_path}")
    # The package map is reference material: it must stay inside a Reference
    # section, never promoted to its own top-level tab.
    if "Reference" not in nav_pages.get(PACKAGES_PAGE, ()):
        issues.append(
            f"The packages map ({PACKAGES_PAGE}) must remain under a Reference section"
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
        for relative_path in INSTALL_IDENTITY_PAGES:
            page = docs_dir / relative_path
            if page.exists() and marker in page.read_text():
                issues.append(
                    f"Competing end-user install identity in {relative_path}: {marker}"
                )
    for marker in STALE_PRELAUNCH_MARKERS:
        if marker in public_text:
            issues.append(f"Stale prelaunch copy: {marker}")

    # The seven product targets derive their state at read time, so pages
    # that describe them carry no static maturity word.
    for relative in sorted(TARGET_STATE_DOC_PATHS):
        path = docs_dir / relative
        if not path.is_file():
            continue
        match = STATIC_MATURITY_PATTERN.search(path.read_text())
        if match:
            issues.append(
                f"Static product-target maturity label in {relative}: {match.group(0)}"
            )

    status_page = docs_dir / RELEASE_STATUS_PAGE
    if status_page.is_file():
        status_text = status_page.read_text()
        target_ids = re.findall(
            r'data-openadapt-production-target="([a-z-]+)"',
            status_text,
        )
        if len(target_ids) != len(PRODUCTION_TARGET_IDS) or set(target_ids) != (
            PRODUCTION_TARGET_IDS
        ):
            issues.append(
                "Product component table must bind each of the seven targets "
                "to one admission-derived state cell"
            )

    return issues


def check_train_path_not_current_product(docs_dir=None):
    """Fail if current-product pages still teach capture-then-train."""
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)
    issues = []
    for md_file in sorted(docs_dir.rglob("*.md")):
        if not md_file.is_file():
            continue
        relative = md_file.relative_to(docs_dir).as_posix()
        if relative in TRAIN_PATH_ALLOWLIST:
            continue
        text = md_file.read_text()
        for phrase in FORBIDDEN_TRAIN_PATH_PHRASES:
            if phrase in text:
                issues.append(
                    f"Retired capture-then-train copy in {relative}: {phrase!r}"
                )
    return issues


def check_retired_public_claims(docs_dir=None):
    """Fail if a corrected public claim (price, anchor, statistic) returns."""
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)
    issues = []
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".txt"}:
            continue
        relative = path.relative_to(docs_dir).as_posix()
        if relative in RETIRED_CLAIM_ALLOWLIST:
            continue
        text = path.read_text()
        for claim, reason in RETIRED_PUBLIC_CLAIMS.items():
            if claim in text:
                issues.append(f"Retired public claim in {relative}: {claim!r} ({reason})")
    return issues


def redirect_map(mkdocs_file=None):
    """Return the mkdocs-redirects ``redirect_maps`` from mkdocs.yml."""
    mkdocs_file = pathlib.Path(mkdocs_file or MKDOCS_FILE)
    if not mkdocs_file.is_file():
        return {}
    config = yaml.load(mkdocs_file.read_text(), Loader=yaml.BaseLoader) or {}
    for plugin in config.get("plugins", []) or []:
        if isinstance(plugin, dict) and "redirects" in plugin:
            return dict((plugin["redirects"] or {}).get("redirect_maps") or {})
    return {}


def check_retired_redirects(docs_dir=None, mkdocs_file=None):
    """Keep retired and moved URLs redirecting to a page that exists."""
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)
    redirects = redirect_map(mkdocs_file)
    issues = []
    for relative, dest in sorted(RETIRED_REDIRECTS.items()):
        actual = redirects.get(relative)
        if actual is None:
            issues.append(f"Missing redirect for retired route: {relative}")
        elif actual.split("#", 1)[0] != dest:
            issues.append(
                f"Retired route {relative} must redirect to {dest}; found: {actual!r}"
            )
    for relative, dest in sorted(redirects.items()):
        if (docs_dir / relative).exists():
            issues.append(f"Redirect source is also a page: {relative}")
        if not (docs_dir / dest.split("#", 1)[0]).is_file():
            issues.append(f"Redirect {relative} points at a missing page: {dest}")
    return issues


def check_private_name_list():
    """No customer or prospect name in the public docs.

    The list comes from a CI secret or a private file, never this repository.
    Without it the check is skipped; with it, a hit or a bad list fails.
    """
    status, problems = check_private_names.check()
    if status == "skipped":
        print(
            "Private name check skipped: no list in "
            f"{check_private_names.ENV_PATTERNS} or "
            f"{check_private_names.ENV_PATTERNS_FILE}."
        )
    return [f"Private name check: {problem}" for problem in problems]


def check_flow_cli_reference():
    """The command reference covers every command of the released Flow."""
    return [
        f"Flow command reference: {problem}"
        for problem in flow_cli_reference.check_page()
    ]


def run_mkdocs_build(strict=False):
    """Run mkdocs build and return (success, output).

    Curated product docs should pass strict mode. The caller may opt out only
    for a local diagnostic build.
    """
    cmd = ["mkdocs", "build"]
    if strict:
        cmd.append("--strict")
    cmd.extend(["--site-dir", str(ROOT / "_site_check")])
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(ROOT), check=False
    )
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

    issues.extend(check_train_path_not_current_product())
    issues.extend(check_retired_public_claims())
    issues.extend(check_retired_redirects())
    issues.extend(check_flow_cli_reference())
    issues.extend(check_private_name_list())

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
