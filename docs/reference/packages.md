---
description: >-
  Every OpenAdapt package and repository, what it is for, where its source
  lives, and whether you need it.
---

# Packages

You need one package: `pip install openadapt`. It installs the engine and
the MCP server. Install the others only for the reasons in the last column.

| Package | What it is | Source | Do you need it? |
|---|---|---|---|
| `openadapt` | The `openadapt` command: `quickstart`, `doctor`, `deploy`, `connect`, `seal`, and the `flow` and `agent` command groups | [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | Yes. Start here. |
| `openadapt-flow` | The engine: recording, compiling, checks, qualification, runs, repair | [OpenAdapt/packages/flow](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow) | Installed by `openadapt` |
| `openadapt-agent` | The MCP server and Agent Skills for AI agents | [OpenAdapt/packages/agent](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/agent) | Installed by `openadapt` |
| `openadapt-types` | Shared data models: screen state, actions, Execute contracts | [OpenAdapt/packages/types](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/types) | Installed by `openadapt-flow` |
| `openadapt-capture` | The desktop recorder | [openadapt-capture](https://github.com/OpenAdaptAI/openadapt-capture) | For recording desktop apps: `openadapt[capture]` |
| `openadapt-privacy` | Scrubbing and redaction of identifiers in text and images | [openadapt-privacy](https://github.com/OpenAdaptAI/openadapt-privacy) | For scrubbing: `openadapt[privacy]` |
| `openadapt-desktop` | The OpenAdapt Desktop app | [openadapt-desktop](https://github.com/OpenAdaptAI/openadapt-desktop) | For the desktop app; installers at [openadapt.ai/download](https://openadapt.ai/download) |
| `openadapt-viewer` | HTML viewers for training dashboards and benchmark results | [openadapt-viewer](https://github.com/OpenAdaptAI/openadapt-viewer) | Rarely |
| `openadapt-evals` | Benchmark harnesses for GUI agents | [openadapt-evals](https://github.com/OpenAdaptAI/openadapt-evals) | Research |
| `openadapt-ml` | Model training and inference for GUI automation agents | [openadapt-ml](https://github.com/OpenAdaptAI/openadapt-ml) | Research |
| `openadapt-grounding` | UI element location from screenshots | [openadapt-grounding](https://github.com/OpenAdaptAI/openadapt-grounding) (archived) | Research |
| `openadapt-retrieval` | Finding similar past demonstrations with vision-model embeddings | [openadapt-retrieval](https://github.com/OpenAdaptAI/openadapt-retrieval) (archived) | Research |

OpenAdapt Cloud, the hosted workspace at `app.openadapt.ai`, isn't open
source.

## How the engine packages fit together

`openadapt-flow`, `openadapt-agent`, and `openadapt-types` are developed in
one repository, [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt), under
`packages/`. The former `openadapt-agent` and `openadapt-types` repositories
are archived, and the former `openadapt-flow` repository is frozen. File issues
and pull requests in OpenAdapt.

On the `main` branch, the agent and types code has moved into
`openadapt-flow` (as `openadapt_flow.agent` and `openadapt_flow.contracts`).
The `openadapt-agent` and `openadapt-types` packages keep their names, imports,
and commands working. The released versions on PyPI, `openadapt-flow` 2.1.0 and
`openadapt-agent` 2.2.0, are still separate packages and install
`openadapt-types` separately.

## Extras of `openadapt`

`openadapt[capture]`, `[browser]`, `[windows]`, `[macos]`, `[linux]`,
`[rdp]`, `[privacy]`, `[flow]`, `[agent]`, `[ml]`, `[evals]`, `[viewer]`,
`[grounding]`, `[retrieval]`, `[core]`, `[all]`, and `[dev]`. For a surface, combine `capture` with that surface,
for example `"openadapt[capture,windows]"`.
