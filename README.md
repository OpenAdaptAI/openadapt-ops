# openadapt-ops

Documentation source and ops automation for the OpenAdapt ecosystem. This
repository is the source of truth for the public product documentation at
[docs.openadapt.ai](https://docs.openadapt.ai), and it holds the tooling that
builds, validates, and publishes that site.

> **Lifecycle: Internal.** This repository is publishing and operations
> infrastructure, not an end-user package. It was formerly named
> `openadapt-maintenance` and is now `OpenAdaptAI/openadapt-ops`.

> **Source of truth:** This repository's `docs/` tree and `mkdocs.yml` own
> `docs.openadapt.ai`. `OpenAdapt/docs`, `OpenAdapt/mkdocs.yml`, and
> `openadapt-gitbook` are noncanonical historical trees and must not deploy to
> the production docs domain. See
> [`docs/reference/documentation-governance.md`](docs/reference/documentation-governance.md).

## About OpenAdapt

OpenAdapt provides verified automation from demonstration. It compiles repeated
GUI work into deterministic programs for browser, Windows, macOS, Linux, RDP,
and Citrix/VDI. Healthy runs make no model calls. OpenAdapt checks the declared
result before it reports `VERIFIED` and stops when the required evidence is
missing. The local runtime is MIT licensed; managed Cloud is optional. The
flagship code lives at
[github.com/OpenAdaptAI/openadapt](https://github.com/OpenAdaptAI/openadapt).

## What is in this repository

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
- **Synthetic Production acceptance publisher**: a public, fail-closed workflow
  that verifies every qualified campaign row and the private Cloud workflow's
  Sigstore proof, creates GitHub provenance for every asset, and publishes a
  content-addressed immutable release. See
  [`docs/reference/synthetic-acceptance-proof.md`](docs/reference/synthetic-acceptance-proof.md).
- **`repos.yml`**: the list of ecosystem repositories the pipeline reads from.

## Build the docs locally

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

## Continuous integration and publishing

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

## Adding a new repository

Add an entry to `repos.yml`. No code changes are needed.

## Links

- Live documentation: [docs.openadapt.ai](https://docs.openadapt.ai)
- Flagship repository:
  [github.com/OpenAdaptAI/openadapt](https://github.com/OpenAdaptAI/openadapt)
- Documentation governance:
  [`docs/reference/documentation-governance.md`](docs/reference/documentation-governance.md)
