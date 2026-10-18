# Operational scripts

Standalone maintenance and growth scripts for the docs repository. Unless a
script says otherwise, install the dev environment first:

```bash
uv sync --locked --extra dev
```

## Docs build checks

### `flow_cli_reference.py`: the command reference follows the Flow release

`docs/reference/flow-commands.md` is generated from the argparse parser of the
`openadapt-flow` release on PyPI named by `FLOW_VERSION` (now 2.1.0), never
from OpenAdapt `main`. The parser is saved as
`tests/fixtures/flow_cli_<version>.json`, and the tests that check documented
commands and options read the same file.

```bash
python scripts/flow_cli_reference.py snapshot    # install the release from PyPI, rewrite snapshot + page
python scripts/flow_cli_reference.py render      # rewrite the page from the committed snapshot
python scripts/flow_cli_reference.py check       # offline: page matches snapshot, every command listed
python scripts/flow_cli_reference.py check-pypi  # online: snapshot matches the release on PyPI
```

`validate_docs.py` runs `check`, and fails when a released command or
subcommand is missing from the reference. The `flow-cli-release` CI job runs
`check-pypi`. The tests also require every top-level verb in the table on
`docs/reference/cli.md`.

To move to a new Flow release: set `FLOW_VERSION`, run `snapshot`, describe
new commands in `cli.md`, and commit.

### `generate_cli_reference.py`: launcher and agent help follow their releases

`generate_cli_reference.py` writes `docs/reference/cli-help.md` and
`tests/fixtures/agent_cli.json` from the launcher and agent parsers of the
versions pinned in `cli-reference/requirements.txt`. The Flow pin there must
equal `FLOW_VERSION` in `flow_cli_reference.py`. It runs in its own environment, not the dev
one:

```bash
uv venv --python 3.12 /tmp/cli-ref
uv pip install --python /tmp/cli-ref/bin/python -r cli-reference/requirements.txt
/tmp/cli-ref/bin/python scripts/generate_cli_reference.py
```

The `cli-reference` CI job reruns it and fails when the committed files
differ. To move the docs to a new release, change the pin, rerun it, and
update `docs/reference/cli.md` for the commands that changed.

### `check_private_names.py`: no customer or prospect names

Customer and prospect names must never appear in the public docs, and the list
of those names must not be in this public repository either. The check reads
the list at run time from:

- `DOCS_PRIVATE_NAME_PATTERNS`: one case-insensitive regular expression per
  line; blank lines and lines starting with `#` are ignored; or
- `DOCS_PRIVATE_NAME_PATTERNS_FILE`: a path to a file in that format, for
  example one in a private repository checkout.

In CI, the list is the `DOCS_PRIVATE_NAME_PATTERNS` repository secret. It is
passed to `validate_docs.py`, to the built-site scan in `ci.yml` and
`sync.yml`, and to `generate_whats_new.py`, which keeps the existing digest
instead of publishing a PR title that matches. To set or update the secret
from the private list (keep the file outside this checkout):

```bash
gh secret set DOCS_PRIVATE_NAME_PATTERNS -R OpenAdaptAI/openadapt-ops < /path/to/private-names.txt
```

Behavior:

- No list (a fork's pull request, or a local build without the variables): the
  check prints a notice and passes. `--require` makes it fail instead.
- A list: any match in `docs/`, `mkdocs.yml`, `overrides/`, `templates/`,
  `prompts/`, `README.md`, or the built `site/` fails. So does a list that is
  empty, unreadable, or has an invalid pattern.
- A hit prints the file, line, and pattern number only. The matched text and
  the pattern never reach the log.

Run it locally before a push:

```bash
DOCS_PRIVATE_NAME_PATTERNS_FILE=/path/to/private-names.txt \
  uv run python scripts/check_private_names.py --site site
```

## Assistant visibility

`assistant_visibility.py` scores an exported assistant-response grid for OpenAdapt mentions, citations, recommendation position, missing trials, and stale product claims. The prompt set and response schema are in [`assistant-visibility/README.md`](../assistant-visibility/README.md).

## Growth scripts

### `crosspost_devto.py` — mirror blog posts to dev.to

Reads the blog RSS feed (`https://blog.openadapt.ai/index.xml`; the Hugo
config points its RSS entry there) and creates one dev.to article per post
that is not on the account yet. Every article sets `canonical_url` to the
original blog URL so search engines keep ranking the blog first.

- Dry-run is ON by default and prints exactly what would be posted.
- Idempotent: it lists existing articles via `GET /api/articles/me/all` and
  skips any post whose canonical URL already exists.
- The API key comes from the `DEVTO_API_KEY` environment variable and is
  never written to disk or logs.

```bash
# Preview against the live feed (no key needed):
uv run python scripts/crosspost_devto.py

# Preview against a local fixture:
uv run python scripts/crosspost_devto.py --feed tests/fixtures/sample_feed.xml

# Post for real:
DEVTO_API_KEY=<key> uv run python scripts/crosspost_devto.py --apply

# Post at most one article per run:
DEVTO_API_KEY=<key> uv run python scripts/crosspost_devto.py --apply --limit 1
```

Run it after publishing a blog post, or as part of the weekly routine below.

### `metrics_weekly.py` — weekly growth report

Collects one week's growth snapshot and writes
`reports/growth-metrics-YYYY-WW.md`:

| Source | Metrics |
|---|---|
| GitHub API | stars and forks for `OpenAdaptAI/OpenAdapt`, `openadapt-flow`, `openadapt-capture` |
| HN Algolia | story hits mentioning "OpenAdapt", summed points and comments |
| pypistats.org | downloads over the last 7 days for `openadapt` and `openadapt-flow` |
| Blog sitemap | number of individual blog posts |

The table layout is deterministic (fixed row and column order, no timestamps),
so consecutive weeks diff cleanly. Failed sources render as `n/a` instead of
stopping the run. `reports/` is gitignored; keep the files wherever you archive
weekly numbers.

```bash
uv run python scripts/metrics_weekly.py                 # current ISO week
uv run python scripts/metrics_weekly.py --week 2026-W34 # specific week
uv run python scripts/metrics_weekly.py --stdout        # print, do not write
```

No API key is required. Setting `GH_TOKEN` raises the GitHub rate limit only;
it is never logged.

**Weekly cadence:** run both scripts once per week, e.g. Monday 09:00 UTC,
right before the Monday docs sync:

```cron
0 9 * * 1 cd /path/to/openadapt-ops && uv sync --locked --extra dev --quiet && uv run python scripts/metrics_weekly.py >> reports/cron.log 2>&1 && DEVTO_API_KEY=<key> uv run python scripts/crosspost_devto.py --apply >> reports/cron.log 2>&1
```

This repository intentionally ships no cron workflow for these scripts; wire
the schedule in your own runner when the weekly review owns one.

## Action pin sweep

`sweep_action_pins.py` reads every workflow in every repository we own and
reports each `uses:` reference that is not a full 40-character commit SHA. A tag
is mutable by the upstream owner and a major tag moves by design; a branch ref
tracks another project's HEAD continuously. `pypa/gh-action-pypi-publish`
v1.14.0 rejects `Metadata-Version: 2.5` and broke the openadapt-evals 0.91.0
release *after* its tag, version commit and GitHub release had landed.

It uses the live organisation listing rather than `repos.yml`, for the reason
`sweep_default_branch_ci.py` gives: `repos.yml` omits internal tooling, and a
sweep built on it would miss exactly the repositories nothing else covers.

```bash
# Report (what the weekly job runs):
python scripts/sweep_action_pins.py
```

### The reviewed backlog

About 112 references are unpinned today. Alerting on all of them weekly is how
an alert gets muted, so the accepted backlog lives in `action-pin-baseline.json`
and the sweep alerts **only** on a reference that is new or worse than what was
accepted. The backlog is counted in the report but never raises the alarm.

Validation never regenerates the baseline — that is deliberate, so a person
reviews the change. Accept a reference explicitly, then review the diff:

```bash
python scripts/sweep_action_pins.py --write-baseline
```

Shrinking the backlog is the point: pin a reference properly and drop its row.
`.github/workflows/action-pin-sweep.yml` runs the report weekly and keeps one
issue up to date, the same pattern as `default-branch-sweep.yml`.

## What's New grouped by release

`generate_whats_new.py` lists the PRs merged in the last 7 days and places each
under the first release whose tag contains its merge commit (GitHub compare
API), or under **Merged, not released yet**. A merged PR is not a shipped
feature, so the page never lists one as released before a tag includes it.

Tags come from `releases` in `repos.yml`. A repository without it uses
`v<version>`. In the OpenAdapt monorepo the launcher uses `v<version>`, and
`packages/flow/`, `packages/agent/`, and `packages/types/` use the
`<pypi-project>-v<version>` tags that `release-package.yml` creates. A PR
belongs to the package path where it changes the most files.

With `ANTHROPIC_API_KEY`, the LLM rewrites each PR title as one sentence. It
returns a JSON map keyed by PR URL and has no say in the grouping. Without the
key, or on any bad response, the page uses the titles. A failed GitHub request
keeps the existing page.

## Guard and generator scripts

The remaining scripts validate or generate the published site:
`validate_docs.py` (product-doc contract plus strict build), `sync_readmes.py`
and `aggregate_changelog.py` / `generate_whats_new.py` (content sync feeding
`docs/packages/`, `docs/changelog.md`, and `docs/whats-new.md`),
`check_published_version_claims.py` (release-claim registry),
`check_production_readiness.py` and the `database_backup_*` /
`sweep_*` scripts (production operations). Each carries its own usage docstring.
