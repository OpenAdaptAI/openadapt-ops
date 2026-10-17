---
description: >-
  Which OpenAdapt releases are admitted for production use, how the public
  record works, and how to check a download.
---

# Release integrity

## Which releases are admitted for production

The public production record covers seven Production targets: the
launcher, Flow, Agent, Capture, Desktop, Cloud, and this documentation.
These are the parts OpenAdapt releases, not the
[surfaces](../explanation/surfaces.md) it drives. A
release of each one is admitted for production use only by a signed
admission in that record. The product as a whole is in production only when
all seven hold an active admission. The record's policy sets a 30-day
maximum for an admission (`maximum_admission_days`), but the current
admissions carry no expiry date (`expires_at` is empty), so they stay active
until revoked. When the newest admission for a component has expired or been
revoked, that component has no production release; the record never falls
back to an older one.

The admitted release can be older than the newest one on PyPI. On
17 October 2026 the record admitted launcher 1.16.0 and Flow 1.35.1, while
PyPI had `openadapt` 1.17.0 and `openadapt-flow` 2.1.0. A newer release isn't
admitted until it gets its own signed admission, so these docs describe the
newest release and this page shows which one is admitted.

The table reads the record live:

| Production target | Production status | What it is |
|---|---|---|
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | <span data-openadapt-production-target="openadapt" aria-live="polite">No current verified Production admission.</span> | The `openadapt` command and installer |
| [OpenAdapt Flow](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow) | <span data-openadapt-production-target="flow" aria-live="polite">No current verified Production admission.</span> | The compiler and runtime |
| [OpenAdapt Agent](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/agent) | <span data-openadapt-production-target="agent" aria-live="polite">No current verified Production admission.</span> | The MCP server and Agent Skills |
| [OpenAdapt Capture](https://github.com/OpenAdaptAI/openadapt-capture) | <span data-openadapt-production-target="capture" aria-live="polite">No current verified Production admission.</span> | The desktop recorder |
| [OpenAdapt Desktop](https://github.com/OpenAdaptAI/openadapt-desktop) | <span data-openadapt-production-target="desktop" aria-live="polite">No current verified Production admission.</span> | The desktop app |
| [OpenAdapt Cloud](https://app.openadapt.ai/) | <span data-openadapt-production-target="cloud" aria-live="polite">No current verified Production admission.</span> | The hosted workspace |
| OpenAdapt documentation | <span data-openadapt-production-target="docs" aria-live="polite">No current verified Production admission.</span> | This site |

The record itself is
[production-lifecycle.json](https://docs.openadapt.ai/production-lifecycle.json),
with its verification results in
[production-lifecycle-verifications.json](https://docs.openadapt.ai/production-lifecycle-verifications.json).
From the command line:

```bash
openadapt flow admit status
```

`admit status` reads the public record and prints which Flow releases are
admitted. It never signs anything. Add `--check` to exit 1 unless Flow holds a
live admission.

## What a release admission requires

Each component's admission needs evidence that names the task, environment,
condition, record check, and failure categories, with at least three trials
per task per condition. It must report the silent-incorrect-success and
over-halt counts, including zeros, and include at least three trials where
delivery is deliberately made uncertain. Each of those must end
`RECONCILIATION_REQUIRED` without a blind retry. Model calls on healthy runs,
silent wrong successes, wrong-record saves, and duplicate saves must all be
zero. Evidence for one component can't admit another.

## Workflow admissions

A release admission says a component passed. It doesn't qualify your
workflow. A production run also needs an active signed admission for the
exact bundle; the run refuses one that is missing, expired, revoked, or for
a different bundle. Changing the bundle or anything it is bound to, such as
the input schema, needs a new qualification. See
[Certify and qualify a workflow](../how-to/certify-and-qualify.md#admission).

The public list of workflow admissions is
[production-workflow-admissions.json](https://docs.openadapt.ai/production-workflow-admissions.json).
Every entry today is `remote-safe-synthetic`: tutorial bundles with
`bundle_version` `0.0.0-synthetic` and one reference bundle. A retained row
doesn't establish current qualification; check the exact workflow, runtime,
and current authority before a run. Synthetic evidence does not qualify a
customer workflow.

## Check a download

**Python packages** install from PyPI. Pin the exact versions a workflow was
qualified on.

**OpenAdapt Desktop** installers are GitHub pre-releases. The current one,
`desktop-v0.15.0`, includes:

- `SHA256SUMS` for every installer;
- a CycloneDX software bill of materials;
- metadata for each platform's build.

The Windows and Linux installers are unsigned, and the macOS installers are
ad-hoc signed. Before you override a first-launch warning, put
`SHA256SUMS` in the same folder as the installer and check it. On macOS:

```bash
shasum -a 256 -c SHA256SUMS --ignore-missing
```

On Linux, use `sha256sum -c SHA256SUMS --ignore-missing`. Each file you
downloaded should print `OK`.

## Source and build controls

- The engine, agent, and launcher are MIT-licensed and public in
  [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt).
- GitHub Actions are pinned by commit SHA, and dependencies are updated
  through Dependabot.
- Report a pinning gap or other supply-chain finding as described in
  [Vulnerability disclosure](vulnerability-disclosure.md).
