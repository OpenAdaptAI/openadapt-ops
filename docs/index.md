---
title: OpenAdapt, the demonstration compiler
hide:
  - toc
---

<!--
================================================================================
TARGET-STATE SPEC — HELD. DO NOT PUBLISH UNTIL TRUE.
This home page and the concept pages it links describe the product AS IT WILL BE
when in-flight work lands (the substrate-agnostic desktop runner, the BYOC
Connector, and the fail-closed `run` gate). It is not a description of what ships
today. Lanes are labelled honestly; nothing here authorizes claiming an unbuilt
capability. Publish only when the described capabilities are real.
================================================================================
-->

!!! warning "Target-state spec — held until it ships"
    This page describes OpenAdapt **as it will be** once in-flight work lands:
    the substrate-agnostic desktop/Citrix runner, the BYOC deployment, and the
    fail-closed [`run`](concepts/regulated-execution.md) gate. Cells and claims
    are labelled honestly with what is real today. It is a **held specification**,
    not a description of the current release.

# Record a workflow once. Replay it forever, for free.

<p class="oa-lede">
OpenAdapt is a <strong>demonstration compiler</strong>. You perform a GUI
workflow one time. It compiles that demonstration into a deterministic,
self-healing script that runs locally, verifies real effects against the
system of record, and halts rather than guessing. An API compiler for the
API-less long tail.
</p>

[Get started in 5 minutes](get-started/index.md){ .md-button .md-button--primary }
[See how it works](concepts/demonstration-compiler.md){ .md-button }

---

## Who it is for

OpenAdapt is built for **regulated, repetitive desktop and web work**: the
500th patient referral this month, the daily claims batch, the mortgage file
that moves through six screens the same way every time. Work that a person has
already figured out, that runs many times, and where a wrong action has a real
cost.

A computer-use agent re-reasons through the whole task with a large model on
every run. That is the right shape for a task nobody has automated before, and
the wrong one for a workflow you run a thousand times. OpenAdapt compiles the
demonstration instead, so the model is only consulted to repair the script, not
to drive it.

It runs where that work lives: a web app (the reference Playwright backend), a
native Windows desktop via UI Automation, or a pixel-only Citrix/RDP session —
all behind [one substrate-agnostic runner](concepts/substrate-model.md), with
desktop and Citrix the differentiated wedge. And it runs where your compliance
posture requires — our cloud, your VPC (BYOC), or fully air-gapped — under a
single [deployment matrix](concepts/deployment-matrix.md) where you choose where
the data lives.

---

## Three things that make it different

<div class="grid cards" markdown>

-   __Deterministic $0 replay__

    ---

    A compiled workflow replays with **zero model calls** on the healthy path.
    Local template match, OCR, and geometry resolve each step in milliseconds.
    No per-run API cost, no network round trip, no cloud dependency.

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

The same compiled bundle runs on any surface and in any deployment, because the
runtime sits behind one [substrate-agnostic runner](concepts/substrate-model.md)
that routes on a single field and never sees pixels or resolved values. Two
orthogonal axes, one contract:

| Deployment ↓ / Substrate → | **Web (browser)** | **Windows-desktop / Citrix** |
|---|---|---|
| **Our cloud — non-PHI** | Managed runner *(preview · waitlist)* | Hosted Windows-in-QEMU runner *(target-state)* |
| **BYOC — regulated (your VPC)** | Connector + your storage; **PHI never enters our infra** *(target-state)* | Engine beside your Citrix Workspace; **pixels never leave** *(target-state · highest-value lane)* |
| **Self-hosted / on-prem** | Local run-queue, no egress *(partial today)* | Same + Windows/RDP; Citrix-pixel proof live at small N *(partial today · the pilot lane)* |

You choose where the data lives — there is no company-wide "never leaves your
network" claim; the guarantee is scoped to the tier you pick. For regulated data
the [`run`](concepts/regulated-execution.md) verb is **fail-closed**: it refuses
to execute unless the bundle is certified, identity coverage meets policy,
declared effects have a verifier, the bundle is signed, and config is pinned.

!!! note "What is real today"
    The self-hosted row is the region that ships today, at pilot maturity.
    Everything marked *target-state* is designed and demand-gated — the
    substrate-agnostic desktop runner, the BYOC Connector, and the `run` gate are
    in flight, not released. See [the deployment matrix](concepts/deployment-matrix.md).

---

## Measured, not claimed

We publish the numbers and the failure modes. Two representative results,
same success check on both arms:

| Task | Compiled replay | Computer-use agent |
|---|---|---|
| **OpenEMR** (real third-party EMR, add-patient-note, 18 steps) | 20/20, 39.2s p50, **$0/run**, 0 model calls | 10/10, 70.4s p50, ~$0.55/run |
| **MockMed** (CI-reproducible triage task) | 100/100, 4.9s p50, **$0/run**, 0 model calls | 20/20, 37.5s p50, ~$0.27/run |

The compiled arm costs $0 per run, every run, forever. Full methodology and
caveats live in the [openadapt-flow benchmark
docs](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark).

!!! note "Stated honestly"
    Compiled replay has real limits, and we test for them by attacking our own
    system before anyone else does. A 125% browser zoom currently zeroes
    replayability. Instance-specific screen state means per-tenant
    re-recording. On pure-pixel substrates a look-alike identifier can force a
    halt rather than a verify. The full list is in
    [what it does not do yet](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).

---

## Start here

<div class="grid cards" markdown>

-   [__Get started__](get-started/index.md)

    Install and compile your first workflow in about five minutes.

-   [__Core concepts__](concepts/index.md)

    The compiler model, the capability ladder, effect verification, the
    identity gate, and how safety is enforced.

-   [__Guides__](guides/index.md)

    Record your own app, handle parameters and secrets, write a policy, and
    deploy on-prem.

-   [__Reference__](reference/index.md)

    Every `openadapt flow` verb, the bundle format, and configuration.

</div>
