# Changelog

> Release history across the OpenAdapt product repositories.


## OpenAdapt

- **[openadapt-types-v0.23.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/openadapt-types-v0.23.0)** (2026-10-18)
  First release from the [OpenAdapt monorepo](https://github.com/OpenAdaptAI/OpenAdapt) (`packages/types`). The models now live in `openadapt_flow.contracts`; this package re-exports them, so `import openadapt_types` keeps working. It requires `openadapt-flow>=2.2.0,<3`.
- **[openadapt-flow-v2.2.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/openadapt-flow-v2.2.0)** (2026-10-18)
  First release from the [OpenAdapt monorepo](https://github.com/OpenAdaptAI/OpenAdapt) (`packages/flow`). The shared contracts (`openadapt_flow.contracts`) and the MCP agent server (`openadapt_flow.agent`) now ship inside this package; `openadapt-types` and `openadapt-agent` are thin compatibility packages over them.
- **[openadapt-agent-v2.2.1](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/openadapt-agent-v2.2.1)** (2026-10-18)
  First release from the [OpenAdapt monorepo](https://github.com/OpenAdaptAI/OpenAdapt) (`packages/agent`). The MCP agent server now lives in `openadapt_flow.agent`; this package is a compatibility package over it, so `openadapt-agent` and `import openadapt_agent` keep working. It requires `openadapt-flow>=2.2.0,<3`.
- **[v1.17.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/v1.17.0)** (2026-10-16)
  Breaking Changes
- **[v1.16.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/v1.16.0)** (2026-08-26)
  Bug Fixes

## openadapt-flow

- **[v2.2.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v220-2026-10-18)** (2026-10-18)
  First release from the [OpenAdapt monorepo](https://github.com/OpenAdaptAI/OpenAdapt) (`packages/flow`). The shared contracts (`openadapt_flow.contracts`) and the MCP agent server (`openadapt_flow.agent`) now ship inside this package; `openadapt-types` and `openadapt-agent` are thin compatibility packages over them.
- **[v2.1.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v210-2026-10-16)** (2026-10-16)
  A calling agent can demonstrate the fix for a halted run; the result is a governed repair candidate (review, replay and fault campaigns, human approval) with provenance, scrubbed-screen evidence and the screen-share mode recorded. `run --hold-on-halt` keeps a halted browser page open for that repair ([#504](https://github.com/OpenAdaptAI/openadapt-flow/pull/504)).
- **[v2.0.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v200-2026-10-15)** (2026-10-15)
  `openadapt-flow run` now uses the `each_item` approval mode unless the run names a mode ([#497](https://github.com/OpenAdaptAI/openadapt-flow/pull/497)). Before 2.0.0 only the Standard and Regulated profiles were gated by default; a Demo or profile-less run saved without asking.
- **[v1.35.1](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v1351-2026-09-08)** (2026-09-08)
  Repeat secret-boundary checks before and after each screenshot attempt while login frames change.
- **[v1.35.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v1350-2026-09-02)** (2026-09-02)
  Bind updated process graph schema ([#444](https://github.com/OpenAdaptAI/openadapt-flow/pull/444),

## openadapt-desktop

- **[v0.20.0](https://github.com/OpenAdaptAI/openadapt-desktop/releases/tag/v0.20.0)** (2026-10-18)
  Documentation
- **[v0.19.0](https://github.com/OpenAdaptAI/openadapt-desktop/releases/tag/v0.19.0)** (2026-10-17)
  Features
- **[v0.18.0](https://github.com/OpenAdaptAI/openadapt-desktop/releases/tag/v0.18.0)** (2026-10-17)
  Build System
- **[v0.17.1](https://github.com/OpenAdaptAI/openadapt-desktop/releases/tag/v0.17.1)** (2026-10-17)
  Bug Fixes
- **[v0.17.0](https://github.com/OpenAdaptAI/openadapt-desktop/releases/tag/v0.17.0)** (2026-10-16)
  Bug Fixes

## openadapt-ml

- **[v0.17.0](https://github.com/OpenAdaptAI/openadapt-ml/releases/tag/v0.17.0)** (2026-10-17)
  Chores
- **[v0.16.3](https://github.com/OpenAdaptAI/openadapt-ml/releases/tag/v0.16.3)** (2026-07-28)
  Bug Fixes
- **[v0.16.2](https://github.com/OpenAdaptAI/openadapt-ml/releases/tag/v0.16.2)** (2026-07-28)
  Bug Fixes
- **[v0.16.1](https://github.com/OpenAdaptAI/openadapt-ml/releases/tag/v0.16.1)** (2026-06-12)
  Bug Fixes
- **[v0.16.0](https://github.com/OpenAdaptAI/openadapt-ml/releases/tag/v0.16.0)** (2026-06-12)
  Bug Fixes

## openadapt-evals

- **[v0.98.0](https://github.com/OpenAdaptAI/openadapt-evals/releases/tag/v0.98.0)** (2026-10-17)
  What's Changed
- **[v0.97.1](https://github.com/OpenAdaptAI/openadapt-evals/releases/tag/v0.97.1)** (2026-09-03)
  What's Changed
- **[v0.97.0](https://github.com/OpenAdaptAI/openadapt-evals/releases/tag/v0.97.0)** (2026-09-03)
  What's Changed
- **[v0.96.1](https://github.com/OpenAdaptAI/openadapt-evals/releases/tag/v0.96.1)** (2026-09-02)
  What's Changed
- **[v0.96.0](https://github.com/OpenAdaptAI/openadapt-evals/releases/tag/v0.96.0)** (2026-09-01)
  What's Changed

## openadapt-capture

- **[v1.3.0](https://github.com/OpenAdaptAI/openadapt-capture/releases/tag/v1.3.0)** (2026-10-18)
  _This release uses the MIT License._
- **[v1.2.2](https://github.com/OpenAdaptAI/openadapt-capture/releases/tag/v1.2.2)** (2026-07-28)
  Bug Fixes
- **[v1.2.1](https://github.com/OpenAdaptAI/openadapt-capture/releases/tag/v1.2.1)** (2026-07-27)
  Bug Fixes
- **[v1.2.0](https://github.com/OpenAdaptAI/openadapt-capture/releases/tag/v1.2.0)** (2026-07-26)
  Bug Fixes
- **[v1.1.1](https://github.com/OpenAdaptAI/openadapt-capture/releases/tag/v1.1.1)** (2026-07-25)
  Bug Fixes

## openadapt-privacy

- **[v1.1.3](https://github.com/OpenAdaptAI/openadapt-privacy/releases/tag/v1.1.3)** (2026-10-18)
  Bug Fixes
- **[v1.1.2](https://github.com/OpenAdaptAI/openadapt-privacy/releases/tag/v1.1.2)** (2026-10-14)
  Bug Fixes
- **[v1.1.1](https://github.com/OpenAdaptAI/openadapt-privacy/releases/tag/v1.1.1)** (2026-10-14)
  Bug Fixes
- **[v1.1.0](https://github.com/OpenAdaptAI/openadapt-privacy/releases/tag/v1.1.0)** (2026-09-01)
  Features
- **[v1.0.4](https://github.com/OpenAdaptAI/openadapt-privacy/releases/tag/v1.0.4)** (2026-08-28)
  Bug Fixes

## openadapt-types

- **[v0.23.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0230-2026-10-18)** (2026-10-18)
  First release from the [OpenAdapt monorepo](https://github.com/OpenAdaptAI/OpenAdapt) (`packages/types`). The models now live in `openadapt_flow.contracts`; this package re-exports them, so `import openadapt_types` keeps working. It requires `openadapt-flow>=2.2.0,<3`.
- **[v0.22.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0220-2026-10-17)** (2026-10-17)
  **readme**: A person or an agent shows the task; drop 'once'
- **[v0.21.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0210-2026-10-15)** (2026-10-15)
  **execute**: Opt-in execution.halted webhook
- **[v0.20.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0200-2026-10-15)** (2026-10-15)
  Sync the published source policy ([#42](https://github.com/OpenAdaptAI/openadapt-types/pull/42),
- **[v0.19.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0190-2026-10-14)** (2026-10-14)
  Add plain run results and a shared vocabulary lint

## openadapt-grounding

- **[v0.1.2](https://github.com/OpenAdaptAI/openadapt-grounding/releases/tag/v0.1.2)** (2026-01-29)
  Bug Fixes
- **[v0.1.1](https://github.com/OpenAdaptAI/openadapt-grounding/releases/tag/v0.1.1)** (2026-01-29)
  Bug Fixes
- **[v0.1.0](https://github.com/OpenAdaptAI/openadapt-grounding/releases/tag/v0.1.0)** (2026-01-17)
  **Full Changelog**: https://github.com/OpenAdaptAI/openadapt-grounding/commits/v0.1.0

## openadapt-retrieval

- **[v0.1.2](https://github.com/OpenAdaptAI/openadapt-retrieval/releases/tag/v0.1.2)** (2026-01-29)
  Bug Fixes
- **[v0.1.1](https://github.com/OpenAdaptAI/openadapt-retrieval/releases/tag/v0.1.1)** (2026-01-29)
  Bug Fixes
- **[v0.1.0](https://github.com/OpenAdaptAI/openadapt-retrieval/releases/tag/v0.1.0)** (2026-01-17)
  **Full Changelog**: https://github.com/OpenAdaptAI/openadapt-retrieval/commits/v0.1.0
