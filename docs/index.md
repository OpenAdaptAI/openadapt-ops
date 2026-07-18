---
title: OpenAdapt, the demonstration compiler
hide:
  - toc
---

# Show it any task, once. It replays exactly — governed and deterministic.

<p class="oa-lede">
OpenAdapt is a demonstration compiler for any repeated GUI task — in the
browser, on the native desktop, or inside Citrix and other virtual desktops.
Demonstrate the task once and OpenAdapt compiles it into a deterministic,
locally executable program that replays exactly, with zero model calls on a
healthy run. When interfaces drift, OpenAdapt re-resolves targets
deterministically or uses an explicitly configured model tier, records the
repair, and halts instead of guessing when the configured verification checks
fail.
</p>

[Get started in 5 minutes](get-started/index.md){ .md-button .md-button--primary }
[Review qualification evidence](get-started/what-works-today.md){ .md-button }
[See how it works](concepts/demonstration-compiler.md){ .md-button }

---

## Who it is for

OpenAdapt is built for **regulated, repetitive work in web, desktop, and
virtual-desktop interfaces**: the
500th patient referral this month, the daily claims batch, the mortgage file
that moves through six screens the same way every time. Work that a person has
already figured out, that runs many times, and where a wrong action has a real
cost.

A computer-use agent re-reasons through the whole task with a large model on
every run. That is the right shape for a task nobody has automated before, and
the wrong one for a workflow you run a thousand times. OpenAdapt compiles the
demonstration instead, so the model is only consulted to repair the script, not
to drive it.

OpenAdapt carries one compiled workflow and one governance model across
browser, Windows, native macOS, RDP, Citrix, and other VDI surfaces. The
substrate supplies the strongest observations and actions available; the
compiler, identity checks, effect verification, policy, repair, and audit trail
remain consistent. Teams qualify each workflow against its real application
and success oracle before production use.

---

## Three things that make it different

<div class="grid cards" markdown>

-   __Deterministic, model-free replay__

    ---

    A compiled workflow replays with **zero model calls** on the healthy path.
    Local template match, OCR, and geometry resolve each step. Self-hosted
    healthy replay has no model-API charge; hosted infrastructure and service
    pricing are separate.

    [The demonstration compiler →](concepts/demonstration-compiler.md)

-   __Effect verification__

    ---

    The screen is not the system of record. A save banner can paint over an
    empty database. OpenAdapt can verify each write against the real record
    (a FHIR or REST API, a document store) and halt on a mismatch.

    [Effect verification →](concepts/effect-verification.md)

-   __Halt, don't guess__

    ---

    When the screen stops matching expectations, the run stops with a report
    instead of clicking the wrong thing. An identity gate refuses to act when
    it cannot tell two records apart.

    [The identity gate →](concepts/identity-gate.md)

</div>

---

## The shape of it

```mermaid
flowchart LR
    A([Demonstrate<br/>once]) --> B[[compile]]
    B --> C{{Workflow<br/>bundle}}
    C --> D[[replay]]
    D -->|healthy path| E([Deterministic<br/>$0 run])
    D -->|UI drifted| F[[self-heal]]
    F -->|repair as diff| E
    D -->|cannot verify| G([Halt safely<br/>+ report])
    G -->|demonstrate the fix| H[[learn]]
    H -->|governed & gated| C
```

Each compiled step carries a template crop, an OCR label, geometry landmarks,
and postconditions derived from what the demonstration actually changed on
screen. At replay a resolution ladder tries them in order. Healthy scripts
never leave the first rung. When the UI drifts, a lower rung still finds the
target and the fix is written back to the bundle as a reviewable diff. When
nothing matches, the run halts safely rather than guess.

A halt is not a dead end. Demonstrate the fix once and `openadapt flow teach`
compiles that correction back into the workflow (through the same identity,
effect, and policy checks that gate everything else), so it does not halt on
that situation again. The correction is induced as a guarded branch, a
regression gate proves it weakens nothing, and only a verified revision is
promoted (an underdetermined or unsafe fix is refused, not guessed at). It is
deterministic and runs at $0 with the reference inducer. See
[The halt-learn loop](concepts/halt-learn-loop.md).

---

## One runner, any surface, any deployment

The execution contract is designed to carry the same compiled bundle across
surfaces and deployment boundaries. A
[substrate-agnostic runner](concepts/substrate-model.md) routes each job to the
right driver while governance stays above that boundary. Two orthogonal axes,
one contract:

| Deployment ↓ / Substrate → | **Web (browser)** | **Windows UIA** | **Native macOS** | **RDP** | **Citrix** |
|---|---|---|---|---|---|
| **OpenAdapt Cloud** | Managed runner, schedules, reports, usage, and billing | Separately ordered, workflow-qualified deployment | Separately ordered, workflow-qualified deployment | Separately ordered, workflow-qualified deployment | Separately ordered design-partner deployment |
| **Customer cloud / BYOC** | Customer runner and storage with managed governance | Customer runner and storage | Customer runner and storage | Customer runner and storage | Customer runner and storage |
| **Self-hosted / on-prem** | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail |

You choose where execution and data live. For regulated data the
[`run`](concepts/regulated-execution.md) verb is **fail-closed by default**:
it gates certification, identity and effect coverage, approval fallback,
encryption, and manifest integrity before execution.

The public subscription covers approved browser workflows. Desktop and
virtual-desktop lanes in this architecture require a separate order and
workflow-specific qualification; they are not entitlements of the browser
subscription. The [hosted guide](guides/hosted.md),
[qualification evidence](get-started/what-works-today.md), and commercial terms
define the accepted scope. Artifacts cross boundaries
only as approved sanitized derivatives, while PHI-bearing runtime observations
stay inside their declared trusted execution boundary.

---

## Measured, not claimed

We publish the numbers and the failure modes. Two representative results,
same success check on both arms:

| Task | Compiled replay | Computer-use agent |
|---|---|---|
| **OpenEMR** (real third-party EMR, add-patient-note, 18 steps) | 20/20, 39.2s p50, **$0/run**, 0 model calls | 10/10, 70.4s p50, ~$0.55/run |
| **MockMed** (CI-reproducible triage task) | 100/100, 4.9s p50, **$0/run**, 0 model calls | 20/20, 37.5s p50, ~$0.27/run |

The compiled arm made no model calls and recorded no model-API cost in these
measured runs. This excludes authoring, review, infrastructure, exception, and
service costs. Full methodology and caveats live in the [openadapt-flow benchmark
docs](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark).

Detailed task definitions, environments, run counts, oracles, and failure
taxonomies live in the [qualification evidence](get-started/what-works-today.md)
and [engine benchmarks](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark).

---

## Start here

<div class="grid cards" markdown>

-   [__Get started__](get-started/index.md)

    Install, compile, lint, certify, drift, inspect, teach, and deploy.

-   [__Qualification evidence__](get-started/what-works-today.md)

    Accepted substrate results, exact environments, and deployment boundaries.

-   [__Core concepts__](concepts/index.md)

    The compiler model, the capability ladder, effect verification, the
    identity gate, and how safety is enforced.

-   [__Guides__](guides/index.md)

    Record your own app, handle parameters and secrets, write a policy, and
    deploy on-prem.

-   [__Reference__](reference/index.md)

    Every `openadapt flow` verb, the bundle format, and configuration.

</div>
