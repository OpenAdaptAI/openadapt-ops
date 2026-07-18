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
[See what works today](get-started/what-works-today.md){ .md-button }
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

The goal is any repeated GUI task on any surface — browser, Windows, native
macOS, RDP, Citrix — through one substrate-agnostic runner and one compiled
bundle format. Maturity is uneven across those surfaces: browser/Playwright is
the reference path; Windows UIA has scoped acceptance for one 3/3 in-tree
WinForms matrix; native macOS has scoped one-host TextEdit action-effect and
ambiguity-refusal evidence; and RDP has scoped 3/3 one-snapshot network-input
and independent guest-file evidence. All three remain partner qualification.
Citrix still needs a design partner with an actual ICA/HDX environment and does
not inherit RDP evidence. Customer-controlled execution is scoped to
the actual substrate and data boundary; backend presence alone is not a
production-readiness claim. See
[What works today](get-started/what-works-today.md) and the deployment matrix
below.

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

The same compiled bundle runs on any surface and in any deployment, because the
runtime sits behind one [substrate-agnostic runner](concepts/substrate-model.md)
that routes on a single field and never sees pixels or resolved values. Two
orthogonal axes, one contract:

| Deployment ↓ / Substrate → | **Web (browser)** | **Windows UIA** | **Native macOS** | **RDP** | **Citrix** |
|---|---|---|---|---|---|
| **Our cloud** | Managed execution of locally authored, attested browser bundles *(Beta launch candidate; production qualification pending)* | Not in hosted candidate; partner qualification with one scoped 3/3 WinForms acceptance result | Not in hosted candidate; partner qualification with scoped one-host TextEdit evidence | Not in hosted candidate; partner qualification with scoped 3/3 one-snapshot RDP evidence | No hosted Citrix claim; design partner needed |
| **Customer cloud / BYOC** | Connector + customer storage *(deployment qualification required)* | Partner qualification; scoped evidence does not qualify the customer's app or effect oracle | Partner qualification; scoped evidence is not clean-machine or partner acceptance | Partner qualification; scoped evidence does not qualify the customer's RDP server, app, identity, or effect oracle | Design partner needed; no ICA/HDX evidence |
| **Self-hosted / on-prem** | Local browser engine *(Beta reference path)* | Partner qualification; workflow-specific acceptance required | Partner qualification; workflow-specific acceptance required | Partner qualification; workflow-specific network RDP acceptance is still required despite the scoped result | Design partner needed; RDP evidence does not transfer |

You choose where the data lives — there is no company-wide "never leaves your
network" claim; the guarantee is scoped to the tier you pick. For regulated data
the [`run`](concepts/regulated-execution.md) verb is **fail-closed by default**:
it gates certification, identity and effect coverage, approval fallback,
encryption, and manifest integrity before execution.

!!! note "Launch-candidate scope"
    The hosted launch candidate covers browser workflows. It does not promote Windows, RDP,
    or Citrix. Artifacts cross boundaries only as approved sanitized
    derivatives, while PHI-bearing runtime observations stay inside their
    declared trusted execution boundary. This is not a public availability
    statement. See
    [the deployment matrix](concepts/deployment-matrix.md).

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

    Install, compile, lint, certify, drift, inspect, teach, and deploy.

-   [__What works today__](get-started/what-works-today.md)

    Integrated maturity, hosted limits, and pre-deployment boundaries.

-   [__Core concepts__](concepts/index.md)

    The compiler model, the capability ladder, effect verification, the
    identity gate, and how safety is enforced.

-   [__Guides__](guides/index.md)

    Record your own app, handle parameters and secrets, write a policy, and
    deploy on-prem.

-   [__Reference__](reference/index.md)

    Every `openadapt flow` verb, the bundle format, and configuration.

</div>
