# Changelog

> Release history across the OpenAdapt product repositories.


## OpenAdapt

- **[v1.20.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/v1.20.0)** (2026-11-05)
  Requirements
- **[openadapt-flow-v2.6.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/openadapt-flow-v2.6.0)** (2026-11-04)
  Flow adds signed teach authorizations, encrypted local artifacts, durable
- **[openadapt-desktop-v0.26.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/openadapt-desktop-v0.26.0)** (2026-11-04)
  OpenAdapt Desktop 0.26.0: the PyPI package and the native installers.
- **[openadapt-desktop-v0.25.1](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/openadapt-desktop-v0.25.1)** (2026-11-04)
  OpenAdapt Desktop 0.25.1: the PyPI package and the native installers.
- **[v1.19.0](https://github.com/OpenAdaptAI/OpenAdapt/releases/tag/v1.19.0)** (2026-11-03)
  Breaking Changes

## openadapt-flow

- **[v2.6.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v260-2026-11-04)** (2026-11-04)
  Flow adds signed teach authorizations, encrypted local artifacts, durable
- **[v2.5.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v250-2026-11-02)** (2026-11-02)
  Shadow mode checks the writes of an agent you already run against the system of record without blocking any of them, the whole-database frame works on PostgreSQL, a write that lands after the verdict can be caught by a recheck, and several verifier checks that could be unreadable or pass on the wrong value now read and compare exactly.
- **[v2.4.1](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v241-2026-10-28)** (2026-10-28)
  Flow runs without its benchmark package and accepts a pinned config with Windows line endings. Several checks now halt or refute where 2.4.0 could act on the wrong row or pass a weaker check, and the frame can compare the whole database.
- **[v2.4.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v240-2026-10-25)** (2026-10-25)
  A person's approval counts only when a registered approver key signed it, and the verification, identity and recovery paths below fail closed where they used to pass.
- **[v2.3.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/CHANGELOG.md#v230-2026-10-20)** (2026-10-20)
  The shared contracts are back in `openadapt-types`, which depends only on Pydantic; this package requires `openadapt-types>=0.24.0,<0.25.0`, and `openadapt_flow.contracts` returns the same modules as `openadapt_types` ([#1270](https://github.com/OpenAdaptAI/OpenAdapt/pull/1270)).

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

- **[v0.24.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0240-2026-10-20)** (2026-10-20)
  The models live in this package again, and it depends only on `pydantic>=2.5`; the Python 3.13 cap is gone. `openadapt-flow` 2.3.0 and later depend on it, and `openadapt_flow.contracts` returns the same modules as `openadapt_types` ([#1270](https://github.com/OpenAdaptAI/OpenAdapt/pull/1270)). Upgrade `openadapt-flow` to 2.3.0 together with this package: openadapt-flow 2.2.0 carries its own copy o
- **[v0.23.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0230-2026-10-18)** (2026-10-18)
  First release from the [OpenAdapt monorepo](https://github.com/OpenAdaptAI/OpenAdapt) (`packages/types`). The models now live in `openadapt_flow.contracts`; this package re-exports them, so `import openadapt_types` keeps working. It requires `openadapt-flow>=2.2.0,<3`.
- **[v0.22.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0220-2026-10-17)** (2026-10-17)
  **readme**: A person or an agent shows the task; drop 'once'
- **[v0.21.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0210-2026-10-15)** (2026-10-15)
  **execute**: Opt-in execution.halted webhook
- **[v0.20.0](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/types/CHANGELOG.md#v0200-2026-10-15)** (2026-10-15)
  Sync the published source policy ([#42](https://github.com/OpenAdaptAI/openadapt-types/pull/42),

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
