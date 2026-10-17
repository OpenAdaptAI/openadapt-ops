---
description: >-
  The OpenAdapt packages: what each one does, where its code lives, its PyPI
  name, and whether `pip install openadapt` installs it.
---

# Packages

Most people need one command:

```bash
python -m pip install --upgrade openadapt
```

That installs the launcher, the engine (`openadapt-flow`), and the agent bridge
(`openadapt-agent`). It needs Python 3.10 to 3.12. The other packages are
optional, and each one installs with an extra or on its own.

| Package | What it does | Where the code is | PyPI name | How you get it |
|---|---|---|---|---|
| OpenAdapt | The launcher and the `openadapt` command, including `openadapt flow …` | [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt), repository root | [`openadapt`](https://pypi.org/project/openadapt/) | `pip install openadapt` |
| Flow | The engine: records, compiles, qualifies, and runs workflows, and checks each run | [OpenAdapt `packages/flow`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow) | [`openadapt-flow`](https://pypi.org/project/openadapt-flow/) | Installed by `openadapt` |
| Agent | The MCP server and Agent Skills that let an AI agent run a compiled program | [OpenAdapt `packages/agent`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/agent) | [`openadapt-agent`](https://pypi.org/project/openadapt-agent/) | Installed by `openadapt` |
| Types | Shared request, result, and receipt models for integrators | [OpenAdapt `packages/types`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/types) | [`openadapt-types`](https://pypi.org/project/openadapt-types/) | `pip install openadapt-types`, for code that imports `openadapt_types` |
| Desktop | The app for Windows, macOS, and Linux: record, check, and run tasks, and answer stopped runs | [openadapt-desktop](https://github.com/OpenAdaptAI/openadapt-desktop), its own repository | [`openadapt-desktop`](https://pypi.org/project/openadapt-desktop/) | Installer from [openadapt.ai/download](https://openadapt.ai/download); see [Desktop app](../desktop/install.md) |
| Capture | Native recording of screen, mouse, keyboard, timing, and window scope | [openadapt-capture](https://github.com/OpenAdaptAI/openadapt-capture), its own repository | [`openadapt-capture`](https://pypi.org/project/openadapt-capture/) | `pip install "openadapt[capture]"` |
| Privacy | Finds and redacts personal and health data in recordings, logs, and screenshots | [openadapt-privacy](https://github.com/OpenAdaptAI/openadapt-privacy), its own repository | [`openadapt-privacy`](https://pypi.org/project/openadapt-privacy/) | `pip install "openadapt[privacy]"` |
| Evals | Research: benchmark evaluation for GUI agents. Recording, compiling, and running a workflow don't use it. | [openadapt-evals](https://github.com/OpenAdaptAI/openadapt-evals), its own repository | [`openadapt-evals`](https://pypi.org/project/openadapt-evals/) | `pip install "openadapt[evals]"` |

On `main`, the Agent and Types code lives inside Flow, as
`openadapt_flow.agent` and `openadapt_flow.contracts`. The `openadapt-agent`
and `openadapt-types` packages keep the old imports and commands working. The
standalone `openadapt-flow`, `openadapt-agent`, and `openadapt-types`
repositories are frozen; open new issues and pull requests in
[OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt).

[Product components and release admission](../ecosystem/index.md) shows the
release status of each component and lists the research repositories.
