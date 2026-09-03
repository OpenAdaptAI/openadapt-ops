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
executable programs. Healthy runs make no generative-model API calls. When
interfaces drift, OpenAdapt re-resolves from retained evidence or proposes a
governed repair. It halts when verification fails. The local runtime is MIT
licensed; managed Cloud is optional. The flagship code lives at
[github.com/OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt).

A Seal is the signed attestation of one program run. Public examples are
synthetic. See [The Seal](docs/commercial/seal.md).

![A VERIFIED Seal, desktop](docs/assets/screenshots/seal-certificate-desktop.png)

![The same instrument, mobile](docs/assets/screenshots/seal-certificate-mobile.png)

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
  documentation contract, builds the site with `mkdocs build --strict`, and
  checks both tracked source and the complete generated site against the public
  source policy.
- **`.github/workflows/sync.yml`** keeps generated documentation reviewed and
  publishes the site to GitHub Pages. A sub-repository dispatch, the weekly
  schedule, or a manual run regenerates the cross-repository pages from current
  `main`, validates them, and opens or updates `docs/auto-sync` through a pull
  request. These events never deploy branch content. A merged push to `main`
  validates and builds that exact commit before it deploys to
  [docs.openadapt.ai](https://docs.openadapt.ai).

## Add a repository

Add an entry to `repos.yml`. No code changes are needed.

## Links

- Live documentation: [docs.openadapt.ai](https://docs.openadapt.ai)
- Flagship repository:
  [github.com/OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt)
- Documentation governance:
  [`docs/reference/documentation-governance.md`](docs/reference/documentation-governance.md)
