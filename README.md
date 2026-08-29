# openadapt-ops

This repository contains the public product documentation at
[docs.openadapt.ai](https://docs.openadapt.ai): authored pages under `docs/`,
the `mkdocs.yml` navigation, and the pipeline that validates and publishes the
site. It also contains operations runbooks and a history-scrubbing CLI.

> **Lifecycle: Support.** This repository contains current documentation and
> operations tooling. It isn't an end-user package. The deployed documentation
> has a separate, admission-derived Production status.

> **Source of truth:** This repository's `docs/` tree and `mkdocs.yml` own
> `docs.openadapt.ai`. `OpenAdapt/docs`, `OpenAdapt/mkdocs.yml`, and
> `openadapt-gitbook` are noncanonical historical trees and must not deploy to
> the production docs domain. See
> [`docs/reference/documentation-governance.md`](docs/reference/documentation-governance.md).

## OpenAdapt

OpenAdapt compiles demonstrated GUI workflows into deterministic, locally
executable programs. Healthy runs make no model calls. When interfaces drift,
OpenAdapt re-resolves from retained evidence or proposes a governed repair. It
halts when verification fails. The local runtime is MIT licensed; managed
Cloud is optional. The flagship code lives at
[github.com/OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt).

## Layout

- **`docs/`** and **`mkdocs.yml`**: the curated MkDocs Material site published
  to [docs.openadapt.ai](https://docs.openadapt.ai). Curated product pages own
  the navigation.
- **`scripts/`**: the documentation pipeline. Mechanical sync steps
  (`sync_readmes.py`, `aggregate_changelog.py`) are deterministic and make no
  API calls. LLM-enhanced steps (`generate_whats_new.py`,
  `build_architecture.py`) are optional and degrade gracefully without an API
  key. `validate_docs.py` gates the site.
- **`tidy/`**: a CLI for scanning and scrubbing sensitive patterns from git
  history and build artifacts (GitHub Releases, Actions, PyPI, and GHCR). See
  [`tidy/README.md`](tidy/README.md).
- **`ops/`**: production operations and recovery runbooks. Start with
  [`ops/PRODUCTION_OPERATIONS.md`](ops/PRODUCTION_OPERATIONS.md).
- **`repos.yml`**: the list of ecosystem repositories the pipeline reads from.

## Preview the docs locally

```bash
# Install dependencies
uv sync --extra dev

# Preview the site with live reload
uv run mkdocs serve

# Build the site in strict mode (the same gate CI uses)
uv run mkdocs build --strict

# Validate the docs contract (empty-page check plus an mkdocs build)
uv run python scripts/validate_docs.py
```

## Tests

```bash
uv sync --extra dev
uv run pytest tests/ -q
```

## CI and publishing

- **`.github/workflows/ci.yml`** runs on every pull request and on push to
  `main`. It installs locked dependencies, runs the test suite, validates the
  documentation contract, and builds the site with `mkdocs build --strict`.
- **`.github/workflows/sync.yml`** builds and deploys the site to GitHub Pages,
  served at `docs.openadapt.ai`. It runs when:
  - a push to `main` touches `docs/**`, `mkdocs.yml`, or the workflow itself,
    which builds and deploys this repository's docs as-is;
  - a sub-repository's `notify-docs.yml` workflow dispatches a `repo-updated`
    event after its public README, changelog, or release changes, so those
    pages re-sync here;
  - the weekly schedule or a manual run performs a full cross-repo rebuild.

  Every path validates and builds in strict mode before deploying, so a failing
  gate blocks publication.

## Add a repository

Add an entry to `repos.yml`. No code changes are needed.

## Links

- Live documentation: [docs.openadapt.ai](https://docs.openadapt.ai)
- Flagship repository:
  [github.com/OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt)
- Documentation governance:
  [`docs/reference/documentation-governance.md`](docs/reference/documentation-governance.md)
