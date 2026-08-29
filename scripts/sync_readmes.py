"""Fetch READMEs from GitHub and render per-package doc pages."""

import datetime
import pathlib
import re

import yaml
import requests
from jinja2 import Environment, FileSystemLoader

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS_YML = ROOT / "repos.yml"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"

GITHUB_API = "https://api.github.com"


def load_repos(path=REPOS_YML):
    with open(path) as f:
        return yaml.safe_load(f)["repos"]


def fetch_readme(github_slug):
    """Fetch raw README.md content from a GitHub repo."""
    url = f"{GITHUB_API}/repos/{github_slug}/readme"
    headers = {"Accept": "application/vnd.github.raw+json"}
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code == 200:
        return resp.text
    print(f"  Warning: could not fetch README for {github_slug} ({resp.status_code})")
    return f"*README not available for {github_slug}.*"


def sync(repos=None, docs_dir=None, templates_dir=None):
    repos = repos or load_repos()
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)
    templates_dir = pathlib.Path(templates_dir or TEMPLATES_DIR)

    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("package_page.md.j2")

    synced_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    results = []

    for repo in repos:
        name = repo["name"]
        github = repo["github"]
        doc_page = repo.get("doc_page")
        if not doc_page:
            # Repos without a doc_page still feed the changelog and What's New
            # aggregation, but their README is not mirrored as a published
            # page. The docs site presents a single curated Ecosystem page
            # instead of drifting README mirrors.
            print(f"Skipping {name} (no doc_page; changelog/what's-new only)")
            continue
        print(f"Syncing {name}...")

        readme = fetch_readme(github)
        rendered = template.render(
            name=name, github=github, readme_content=readme, synced_at=synced_at,
        )

        out_path = docs_dir / doc_page
        if out_path.exists() and re.search(
            r"^redirect_to:\s+", out_path.read_text(), flags=re.MULTILINE
        ):
            # Curated Flow-first redirects own these URLs. A README mirror
            # would republish capture-then-train copy as current product.
            print(f"Skipping {name} (canonical redirect stub at {out_path})")
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered)
        results.append({"name": name, "path": str(out_path), "size": len(readme)})
        print(f"  -> {out_path} ({len(readme)} chars)")

    return results


if __name__ == "__main__":
    sync()
