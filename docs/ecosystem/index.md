# Package and repository lifecycle

OpenAdapt the product (the [demonstration compiler](../concepts/demonstration-compiler.md))
is what most people need. Underneath it sits a set of open-source libraries and
infrastructure that the compiler and its research build on. This section is for
contributors and integrators who want to use those pieces directly.

!!! note "Product first"
    If you want to compile and run a workflow, start with
    [Get started](../get-started/index.md). The libraries below are the building
    blocks behind OpenAdapt, not the way most users interact with it. Each links
    to its source repository, where its own README is the source of truth.

The end-user identity is deliberately singular: install `openadapt` and run
`openadapt flow …`. The `openadapt-flow` repository is where contributors
inspect and change the engine. See [Versions and compatibility](../reference/compatibility.md)
for the tested package ranges.

## Lifecycle labels

These labels describe the public role of a repository, not the quality of every
module inside it:

- **Beta**: current product surface; validate per workflow.
- **Experimental**: implemented but not a supported production contract.
- **Research**: evidence or model work, not required by deterministic replay.
- **Deprecated**: retained for history or migration; no new integrations.

## Product and optional components

| Repository | Lifecycle | Public role |
|---|---|---|
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | **Beta** | Installer/meta-package and unified `openadapt flow` dispatcher. |
| [openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) | **Beta** | Canonical compiler and governed runtime. Browser is the reference path; other backends have separate maturity labels. |
| [openadapt-cloud](https://github.com/OpenAdaptAI/openadapt-cloud) | **Beta** | Live control plane for the public managed-browser subscription: organizations, exact-hash admission, runner orchestration, reports, billing, and usage. |
| [openadapt-desktop](https://github.com/OpenAdaptAI/openadapt-desktop) | **Experimental** | The current `desktop-v0.5.1` prerelease provides six install/uninstall-smoke-tested installers for Windows, macOS, and Linux, plus exact checksums, platform metadata, and build attestations. |
| [openadapt-agent](https://github.com/OpenAdaptAI/openadapt-agent) | **Experimental** | Active v2 bridge that exposes governed Flow bundles to MCP clients and Agent Skills. The pre-v2 model-driven execution wrapper is the deprecated line; the repository itself is active. |
| [openadapt-capture](https://github.com/OpenAdaptAI/openadapt-capture) | **Experimental** | Optional native mouse, keyboard, and screen recorder behind Flow's Windows and RDP recording path. Browser recording remains inside Flow's Playwright listener. |
| [openadapt-privacy](https://github.com/OpenAdaptAI/openadapt-privacy) | **Experimental** | Optional PII/PHI scrubbing used on configured persist, log, and upload paths. |
| [openadapt-types](https://github.com/OpenAdaptAI/openadapt-types) | **Experimental** | Shared interoperability schemas; contributor-facing, not an end-user product. |

## Research components

| Repository | Lifecycle | Public role |
|---|---|---|
| [openadapt-ml](https://github.com/OpenAdaptAI/openadapt-ml) | **Research** | VLM training, inference, and demonstration-conditioning work. Not required by the healthy compiler path. |
| [openadapt-evals](https://github.com/OpenAdaptAI/openadapt-evals) | **Research** | GUI-agent and demonstration-conditioning evaluation infrastructure. |
| [openadapt-grounding](https://github.com/OpenAdaptAI/openadapt-grounding) | **Research** | UI grounding experiments and model adapters. |
| [openadapt-retrieval](https://github.com/OpenAdaptAI/openadapt-retrieval) | **Research** | Demonstration retrieval experiments. |

## How the pieces fit

```mermaid
flowchart LR
    C[openadapt-capture<br/>optional recording] --> F[[openadapt-flow<br/>canonical compiler]]
    F --> R[Deterministic<br/>replay bundle]
    A[openadapt-agent<br/>MCP + Agent Skills bridge] --> F
    ML[openadapt-ml<br/>grounding / identity models] -.optional on-prem appliance.-> F
    E[openadapt-evals<br/>benchmarks] -.measures.-> F
```

The compiler is the product. Capture can feed it demonstrations, the ML layer
can supply optional on-prem models, Agent gives MCP clients and Agent Skills a
governed route into Flow bundles, and evals measures adjacent research. This page
intentionally does not expose internal developer tools as product components.
See [Qualification evidence](../get-started/what-works-today.md) for integrated
feature and backend maturity.
