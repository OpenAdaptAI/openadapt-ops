# Ecosystem

OpenAdapt the product (the [demonstration compiler](../concepts/demonstration-compiler.md))
is what most people need. Underneath it sits a set of open-source libraries and
infrastructure that the compiler and its research build on. This section is for
contributors and integrators who want to use those pieces directly.

!!! note "Product first"
    If you want to compile and run a workflow, start with
    [Get started](../get-started/index.md). The libraries below are the building
    blocks behind OpenAdapt, not the way most users interact with it. Each links
    to its source repository, where its own README is the source of truth.

## The libraries and infra behind OpenAdapt

### Recording and data

| Library | What it is |
|---|---|
| [openadapt-capture](https://github.com/OpenAdaptAI/openadapt-capture) | Cross-platform desktop recording: time-aligned screenshots, mouse, keyboard, and audio, with privacy scrubbing. The demonstration capture layer. |

### Models and evaluation

| Library | What it is |
|---|---|
| [openadapt-ml](https://github.com/OpenAdaptAI/openadapt-ml) | The VLM layer: trajectory schemas, model adapters, supervised fine-tuning, grounding, and a runtime policy API. The research substrate for the optional on-prem grounding and identity models. |
| [openadapt-evals](https://github.com/OpenAdaptAI/openadapt-evals) | Evaluation infrastructure for GUI-agent benchmarks (for example Windows Agent Arena), with cloud VM orchestration and a results viewer. |
| [OpenAdapt (meta)](https://github.com/OpenAdaptAI/OpenAdapt) | The meta-package and unified `openadapt` dispatcher that mounts the compiler as `openadapt flow`. |

## How the pieces fit

```mermaid
flowchart LR
    C[openadapt-capture<br/>record demonstrations] --> F[[OpenAdapt<br/>demonstration compiler]]
    F --> R[Deterministic<br/>replay bundle]
    ML[openadapt-ml<br/>grounding / identity models] -.optional on-prem appliance.-> F
    E[openadapt-evals<br/>benchmarks] -.measures.-> F
```

The compiler is the product. Capture feeds it demonstrations, the ML layer
supplies the optional on-prem grounding and identity models, and evals measures
it. The rest are independent tools the team uses to build and ship.
