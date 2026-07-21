# Analytics on docs.openadapt.ai

This documentation site uses privacy-safe, build-time analytics. This file lives
at the repository root (not under `docs/`) so it does not affect the published
site or `mkdocs build --strict` navigation.

## What is tracked

The site reports into two destinations that share one event taxonomy across all
OpenAdapt web properties:

- **PostHog** (product analytics), and
- **Google Analytics 4** (Material's native integration).

Tracked events:

| Event | Properties | Notes |
| --- | --- | --- |
| `$pageview` | (automatic) | PostHog fires this via Material's `location$` observable so it works under `navigation.instant`. GA pageviews are handled natively by Material. |
| `docs_search` | `query_length` | Only the LENGTH of the search query is captured, never the raw text. Debounced by ~800ms. |
| `outbound_click` | `destination`, `href` | `destination` is one of `app`, `download`, or `github`. `href` is host + path only, with the query string stripped. |

Search and pageview events are also emitted to Google Analytics where Material's
native integration does not already cover them.

## Shared project

Both destinations are shared with the marketing site. PostHog reuses the same
project (via the same env var names below), so all OpenAdapt properties report
together.

## Environment variables (set at BUILD time)

Analytics is a static build, so keys are read when `mkdocs build` runs, not at
page-serve time. Set these in the docs deploy/CI environment:

- `NEXT_PUBLIC_POSTHOG_KEY`: PostHog project key. Reuse the SAME key as the
  marketing site so everything lands in one PostHog project. When this is unset,
  no PostHog script is emitted into the built HTML at all (a hard no-op).
- `NEXT_PUBLIC_POSTHOG_HOST`: PostHog API host. Defaults to
  `https://us.i.posthog.com`.
- `GOOGLE_ANALYTICS_KEY`: GA4 measurement ID. Optional; defaults to the existing
  `G-CJ01Y19XJN`. GA measurement IDs are public (non-secret).

## Privacy properties

- **No PHI or PII.** These are public documentation pages only.
- **Do-Not-Track is respected.** When the browser sends a Do-Not-Track signal,
  PostHog is never loaded or initialized.
- **Conservative capture.** Search records only `query_length` (never the raw
  query), and outbound links record only host + path (never the query string).
- **PostHog `person_profiles: 'identified_only'`** so anonymous visitors do not
  create person profiles.
- **No secrets committed.** Keys are provided only through build-time env vars.
