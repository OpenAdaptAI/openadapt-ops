# Documentation source of truth

This repository is the source of truth for the public product documentation at
`docs.openadapt.ai`.

## Ownership and deployment

- Curated product pages live under `docs/` in this repository.
- `mkdocs.yml` owns the public navigation.
- `.github/workflows/sync.yml` validates, builds, and deploys the site to GitHub
  Pages on repository dispatch, the weekly schedule, or a manual run.
- Synchronization may update the changelog and What's New pages. It must not
  replace the curated product journey with repository README mirrors.

## Noncanonical documentation trees

The following workspace trees are historical and **must not deploy to
`docs.openadapt.ai`**:

- `OpenAdapt/docs` and `OpenAdapt/mkdocs.yml`: an older package-first site.
- `openadapt-gitbook`: a legacy GitBook/API-reference tree.

Their deployment configuration should be disabled or redirected before any
future docs rollout. Content changes there do not update the current public
site.

## Content contract

Public docs must:

1. Name `openadapt-flow` as the canonical engine and `openadapt flow` as the
   unified command surface.
2. Separate shipped behavior from experimental, prototype, and research-spike
   work.
3. Keep the hosted browser launch candidate distinct from experimental desktop
   and remote-display execution.
4. Put product journeys before package topology.
5. Link claims to the engine's benchmarks and limits rather than silently
   expanding them.
6. Keep generated repository material out of top-level navigation; package and
   research topology belongs under Ecosystem or Reference.
