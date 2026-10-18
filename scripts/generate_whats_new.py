"""Generate the What's New digest from recently merged PRs, grouped by release.

A merged pull request is not the same as a shipped feature. Each PR is placed
under the first published release whose tag contains its merge commit, or under
"Merged, not released yet" when no release contains it. The grouping is decided
here, in code; the optional LLM pass only rewrites the one-line description of
each PR and cannot move a PR between sections.

Release tags come from `releases` in repos.yml:

    releases:
      tag_prefix: v                 # default for the repository
      paths:                        # monorepo packages released on their own tag
        - path: packages/flow/
          package: openadapt-flow
          tag_prefix: openadapt-flow-v

A repository without `releases` uses `v<version>` tags.
"""

import datetime
import json
import os
import pathlib
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import yaml
from jinja2 import Environment, FileSystemLoader

import check_private_names

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS_YML = ROOT / "repos.yml"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"
PROMPTS_DIR = ROOT / "prompts"

PR_LIMIT = 20
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
CONTAINED = {"behind", "identical"}


def load_repos(path=REPOS_YML):
    with open(path) as f:
        return [
            repo
            for repo in yaml.safe_load(f)["repos"]
            if repo.get("public_updates", True)
        ]


def _gh(args, what, timeout=30):
    """Run gh and parse its JSON output. Any failure keeps the old digest."""
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise RuntimeError(
            f"GitHub request failed for {what}. "
            "Refusing to replace the digest with an incomplete page."
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"GitHub request failed for {what}: exit {result.returncode}. "
            "Refusing to replace the digest with an incomplete page."
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GitHub response was invalid for {what}.") from exc


def fetch_merged_prs(github_slug, days=7):
    """Merged PRs from the last N days, with merge commit and changed files."""
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
    prs = _gh(
        [
            "pr", "list", "--repo", github_slug, "--state", "merged",
            "--json", "title,url,number,mergedAt,mergeCommit,files",
            "--limit", str(PR_LIMIT), "--search", f"merged:>={since[:10]}",
        ],
        f"{github_slug} pull requests",
    )
    if not isinstance(prs, list):
        raise RuntimeError(f"GitHub PR response was not a list for {github_slug}.")
    return prs


def fetch_release_tags(github_slug, prefix):
    """Release tags with this prefix, newest version first: [(tag, version)]."""
    refs = _gh(
        ["api", "--paginate", f"repos/{github_slug}/git/matching-refs/tags/{prefix}"],
        f"{github_slug} tags",
    )
    if not isinstance(refs, list):
        raise RuntimeError(f"GitHub tag response was not a list for {github_slug}.")
    tags = []
    for ref in refs:
        name = str(ref.get("ref", "")).removeprefix("refs/tags/")
        match = VERSION_RE.match(name[len(prefix):]) if name.startswith(prefix) else None
        if match:
            tags.append((name, tuple(int(part) for part in match.groups())))
    return sorted(tags, key=lambda tag: tag[1], reverse=True)


def tag_contains(github_slug, tag, sha):
    """True when the merge commit is an ancestor of (or equal to) the tag."""
    comparison = _gh(
        ["api", f"repos/{github_slug}/compare/{tag}...{sha}", "--jq", "{status: .status}"],
        f"{github_slug} {tag}",
    )
    return isinstance(comparison, dict) and comparison.get("status") in CONTAINED


def release_lines(repo):
    """The repository's default tag prefix and its per-path package lines."""
    config = repo.get("releases") or {}
    default = {"package": repo["name"], "tag_prefix": config.get("tag_prefix", "v")}
    return default, list(config.get("paths") or [])


def line_for(pr, repo):
    """The release line a PR ships in: the package path with the most changed files."""
    default, paths = release_lines(repo)
    counts = Counter()
    for changed in pr.get("files") or []:
        for index, line in enumerate(paths):
            if str(changed.get("path", "")).startswith(line["path"]):
                counts[index] += 1
                break
    if not counts:
        return default
    best = max(counts.values())
    return paths[min(index for index, count in counts.items() if count == best)]


def first_release(github_slug, sha, tags):
    """The oldest tag that contains sha, or None. `tags` is newest first."""
    if not sha or not tags or not tag_contains(github_slug, tags[0][0], sha):
        return None
    found = tags[0]
    for tag in tags[1:]:
        if not tag_contains(github_slug, tag[0], sha):
            break
        found = tag
    return found


def release_label(line, tag):
    version = ".".join(str(part) for part in tag[1])
    return f"{line['package']} {version}"


def group_by_release(repo, prs):
    """Split a repository's PRs into release sections and an unreleased list."""
    slug = repo["github"]
    lines = [line_for(pr, repo) for pr in prs]
    tags_by_prefix = {}
    for line in lines:
        if line["tag_prefix"] not in tags_by_prefix:
            tags_by_prefix[line["tag_prefix"]] = fetch_release_tags(slug, line["tag_prefix"])

    def lookup(index):
        sha = (prs[index].get("mergeCommit") or {}).get("oid")
        return first_release(slug, sha, tags_by_prefix[lines[index]["tag_prefix"]])

    with ThreadPoolExecutor(max_workers=8) as pool:
        found = list(pool.map(lookup, range(len(prs))))

    released = {}
    unreleased = []
    for pr, line, tag in zip(prs, lines, found):
        entry = dict(pr, package=line["package"])
        if tag is None:
            unreleased.append(entry)
        else:
            key = (line["package"], tag[1])
            released.setdefault(key, {"label": release_label(line, tag), "tag": tag[0], "prs": []})
            released[key]["prs"].append(entry)
    releases = [released[key] for key in sorted(released, key=lambda key: (key[0], key[1]), reverse=True)]
    return {"releases": releases, "unreleased": unreleased}


def llm_sentences(prs):
    """Ask the LLM for one plain sentence per PR, keyed by PR URL.

    Returns {} without an API key or on any bad response; the page then uses
    the PR titles. The LLM never sees or decides the release grouping.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not prs:
        if not api_key:
            print("  No ANTHROPIC_API_KEY set, using PR titles")
        return {}
    try:
        import anthropic
    except ImportError:
        print("  anthropic package not installed, using PR titles")
        return {}

    listing = "\n".join(f"{pr['url']}\t{pr['title']}" for pr in prs)
    prompt = (PROMPTS_DIR / "whats_new.txt").read_text().format(prs_text=listing)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        sentences = json.loads(response.content[0].text)
    except Exception as exc:  # noqa: BLE001 - any failure falls back to titles
        print(f"  LLM rewrite unavailable ({type(exc).__name__}), using PR titles")
        return {}
    urls = {pr["url"] for pr in prs}
    if not isinstance(sentences, dict):
        return {}
    return {
        url: " ".join(text.split())
        for url, text in sentences.items()
        if url in urls and isinstance(text, str) and text.strip()
    }


def _refuse_private_names(rendered):
    """Keep the published digest when a PR title or summary names a customer.

    PR titles come from other repositories, so this is the last point before
    one reaches the public page. The list is read the same way as in
    scripts/check_private_names.py; without one, nothing is checked here.
    """
    try:
        patterns = check_private_names.load_patterns()
    except check_private_names.PatternListError as exc:
        raise RuntimeError(f"Private name list unusable: {exc}. Keeping the existing digest.") from None
    if patterns is None:
        return
    hits = check_private_names.find_in_text(rendered, patterns, "whats-new.md")
    if hits:
        raise RuntimeError(
            "The generated What's New matches the private name list "
            f"({'; '.join(str(hit) for hit in hits)}). Keeping the existing digest."
        )


def generate(repos=None, docs_dir=None, days=7):
    repos = repos or load_repos()
    docs_dir = pathlib.Path(docs_dir or DOCS_DIR)

    sections = {}
    every_pr = []
    for repo in repos:
        prs = fetch_merged_prs(repo["github"], days=days)
        if prs:
            sections[repo["name"]] = group_by_release(repo, prs)
            every_pr.extend(prs)
        print(f"  {repo['name']}: {len(prs)} merged PRs")

    sentences = llm_sentences(every_pr)
    for section in sections.values():
        for pr in section["unreleased"] + [pr for release in section["releases"] for pr in release["prs"]]:
            pr["text"] = sentences.get(pr["url"], pr["title"])

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("whats_new.md.j2")
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rendered = template.render(repos=sections, days=days, generated_at=generated_at)
    _refuse_private_names(rendered)
    out_path = docs_dir / "whats-new.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered)
    print(f"Wrote {out_path}")
    return str(out_path)


if __name__ == "__main__":
    generate()
