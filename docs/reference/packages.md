---
description: >-
  Every OpenAdapt package, what it is for, where its source lives, and
  whether you need it.
---

# Packages

You need one package: `pip install openadapt`. It installs the engine and
the MCP server. Install the others only for the reasons in the last column.

OpenAdapt is moving its product packages into one repository,
[OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt), under `packages/`.
File issues and pull requests there.

| Package | What it is | Source | Do you need it? |
|---|---|---|---|
| `openadapt` | The `openadapt` command: `quickstart`, `doctor`, `deploy`, `connect`, `seal`, and the `flow` and `agent` command groups | [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | Yes. Start here. |
| `openadapt-flow` | The engine: recording, compiling, checks, qualification, runs, repair | [`packages/flow`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow) | Installed by `openadapt` |
| `openadapt-agent` | The MCP server and Agent Skills for AI agents | [`packages/agent`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/agent) | Installed by `openadapt` |
| `openadapt-types` | Shared data models: screen state, actions, Execute contracts | [`packages/types`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/types) | Installed by `openadapt-flow` |
| `openadapt-capture` | The desktop recorder | Moving into `packages/capture` | For recording desktop apps: `openadapt[capture]` |
| `openadapt-privacy` | Scrubbing and redaction of identifiers in text and images | Moving into `packages/` | For scrubbing: `openadapt[privacy]` |
| `openadapt-desktop` | The OpenAdapt Desktop app | Moving into `packages/` | For the desktop app; installers at [openadapt.ai/download](https://openadapt.ai/download) |

OpenAdapt Cloud, the hosted workspace at `app.openadapt.ai`, isn't open
source.

## How the engine packages fit together

On the `main` branch, the agent and types code is part of `openadapt-flow`
(as `openadapt_flow.agent` and `openadapt_flow.contracts`). The
`openadapt-agent` and `openadapt-types` packages keep their names, imports,
and commands working. The released versions on PyPI, `openadapt-flow` 2.1.0
and `openadapt-agent` 2.2.0, are still separate packages and install
`openadapt-types` separately.

## Research

Recording, compiling, and running a workflow don't use these. They stay in
their own repositories:

| Package | What it is | Source |
|---|---|---|
| `openadapt-evals` | Benchmark harnesses for GUI agents | [openadapt-evals](https://github.com/OpenAdaptAI/openadapt-evals) |
| `openadapt-ml` | Model training and inference for GUI automation agents | [openadapt-ml](https://github.com/OpenAdaptAI/openadapt-ml) |
| `openadapt-viewer` | HTML viewers for training dashboards and benchmark results | [openadapt-viewer](https://github.com/OpenAdaptAI/openadapt-viewer) |

## Extras of `openadapt`

For a surface, combine `capture` with that surface, for example
`"openadapt[capture,windows]"`. The surface extras are `[browser]`,
`[windows]`, `[macos]`, `[linux]`, and `[rdp]`. The others are `[capture]`,
`[privacy]`, `[flow]`, `[agent]`, `[core]`, `[all]`, `[dev]`, and the
research extras `[ml]`, `[evals]`, `[viewer]`, `[grounding]`, and
`[retrieval]`.
