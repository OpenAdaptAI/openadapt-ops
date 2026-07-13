---
title: OpenAdapt, the demonstration compiler
hide:
  - toc
---

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
    D -->|cannot verify| G([Halt with<br/>a report])
```

Each compiled step carries a template crop, an OCR label, geometry landmarks,
and postconditions derived from what the demonstration actually changed on
screen. At replay a resolution ladder tries them in order. Healthy scripts
never leave the first rung. When the UI drifts, a lower rung still finds the
target and the fix is written back to the bundle as a reviewable diff. When
nothing matches, the run halts.

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
