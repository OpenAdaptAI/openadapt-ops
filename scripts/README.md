# Operational scripts

Standalone maintenance and growth scripts for the docs repository. Unless a
script says otherwise, install the dev environment first:

```bash
uv sync --locked --extra dev
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

## Guard and generator scripts

The remaining scripts validate or generate the published site:
`validate_docs.py` (product-doc contract plus strict build), `sync_readmes.py`
and `aggregate_changelog.py` / `generate_whats_new.py` (content sync feeding
`docs/packages/`, `docs/changelog.md`, and `docs/whats-new.md`),
`check_published_version_claims.py` (release-claim registry),
`check_production_readiness.py` and the `database_backup_*` /
`sweep_*` scripts (production operations). Each carries its own usage docstring.
