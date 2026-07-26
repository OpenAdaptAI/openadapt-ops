---
title: OpenAdapt, the demonstration compiler
hide:
  - toc
---

# Show it a repeated workflow. OpenAdapt compiles it into governed, deterministic replay.

<p class="oa-lede">
OpenAdapt is a demonstration compiler for repeated GUI work across browser,
Windows, macOS, Linux, RDP, Citrix, and other virtual desktops. Demonstrate a
task once. OpenAdapt compiles it into a deterministic, locally executable
program that replays with no model calls on a healthy run. When interfaces
drift, it re-resolves targets deterministically or uses an explicitly configured
model tier, records the repair, and halts instead of guessing when verification
fails.
</p>

[Try it locally](get-started/index.md){ .md-button .md-button--primary }
[Read the concepts](concepts/demonstration-compiler.md){ .md-button }
[Evaluate a workflow](https://openadapt.ai/#book){ .md-button }

---

## Who it is for

OpenAdapt is built for **regulated, repetitive work in web, desktop, and
virtual-desktop interfaces**: the 500th patient referral this month, the daily
claims batch, the mortgage file that moves through six screens the same way
every time. A person has already figured out the task, it runs many times, and
a wrong action has real cost.

A computer-use agent re-reasons through the whole task with a large model on
every run. That fits a task nobody has automated before, not a workflow you run
a thousand times. OpenAdapt compiles the demonstration instead, so the model is
consulted only to repair the script, not to drive it.

One compiled workflow and one governance model run across browser, Windows,
native macOS, native Linux, RDP, Citrix, and other VDI surfaces. Each substrate
supplies the strongest observations and actions available; the compiler,
identity checks, effect verification, policy, repair, and audit trail stay
consistent. Teams qualify each workflow against its real application and
success oracle before production use.

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
and postconditions derived from what the demonstration changed on screen. At
replay a resolution ladder tries them in order. Healthy scripts never leave the
first rung. When the UI drifts, a lower rung still finds the target, and the fix
is written back to the bundle as a reviewable diff. When nothing matches, the
run halts safely instead of guessing.

A halt is not a dead end. Demonstrate the fix once and `openadapt flow teach`
compiles the correction back into the workflow, through the same identity,
effect, and policy checks that gate everything else, so it will not halt on that
situation again. The correction becomes a guarded branch, a regression gate
proves it weakens nothing, and only a verified revision is promoted; an
underdetermined or unsafe fix is refused, not guessed at. It is deterministic
and runs at $0 with the reference inducer. See
[The halt-learn loop](concepts/halt-learn-loop.md).

---

## One runner, any surface, any deployment

The execution contract carries the same compiled bundle across surfaces and
deployment boundaries. A [substrate-agnostic runner](concepts/substrate-model.md)
routes each job to the right driver while governance stays above that boundary.
Two orthogonal axes, one contract:

| Deployment ↓ / Substrate → | **Web (browser)** | **Windows UIA** | **Native macOS** | **Native Linux** | **RDP** | **Citrix / VDI** |
|---|---|---|---|---|---|---|
| **OpenAdapt Cloud** | Managed runner, schedules, reports, usage, and billing | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud |
| **Customer cloud / BYOC** | Customer runner and storage with managed governance | Customer runner and storage | Customer runner and storage | Customer runner and storage | Customer runner and storage | Customer runner and storage |
| **Self-hosted / on-prem** | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail |

You choose where execution and data live. For regulated data the
[`run`](concepts/regulated-execution.md) verb is **fail-closed by default**:
it gates certification, identity and effect coverage, approval fallback,
encryption, and manifest integrity before execution.

The public subscription covers approved browser workflows on the managed
runner. Windows, macOS, Linux, RDP, and Citrix/VDI execute in a local,
self-hosted, or customer-controlled boundary and can connect to the same Cloud
control plane for governed operation. They are not silently moved into
OpenAdapt's shared managed-browser boundary or included as managed-runner
entitlements. The
[hosted guide](guides/hosted.md),
[qualification evidence](get-started/what-works-today.md), and commercial terms
define the accepted scope. Artifacts cross boundaries only as approved sanitized
derivatives; PHI/PII-bearing runtime observations stay inside their declared trusted
execution boundary.

---

## Measured, not claimed

The [OpenAdapt website](https://openadapt.ai/how-it-works) and
[public Cloud demo](https://app.openadapt.ai/demo#footage) share one viewer
contract for real OpenEMR, Frappe Lending, and openIMIS footage:

- **Recorded demonstration** is source capture and carries no execution outcome.
- **Verified replay** appears only for exact replay media bound to a complete
  passing outcome contract.
- **Fail-safe halt** appears only when exact retained halt media exists. The
  current openIMIS reference includes it; the viewer never invents a halt mode
  for another application.

**Guided view** adds the presentation layer to a derivative; **Raw footage**
shows the immutable media. Guided target tracking appears only when the media
digest, exact decoded frame, viewport mapping, and runtime target binding all
agree. The status capsule uses a bottom corner that does not cover the target
or another protected region, and disappears if neither corner is safe. Neither
the target outline nor the capsule is verification evidence.

Cloud uses the same application, mode, and view choices, then adds an openIMIS
deep dive with the compiled graph, contracts, six retained Standard-profile
results, and byte-inventoried evidence links. **VERIFIED** means the complete
declared contract passed; **HALTED** means the run stopped rather than claim an
outcome it could not prove.

[Watch the shared real-application demo](https://openadapt.ai/how-it-works){ .md-button .md-button--primary }
[Inspect the Cloud evidence deep dive](https://app.openadapt.ai/demo#footage){ .md-button }

We publish the numbers and the failure modes. These two results run **both
arms**, compiled replay against a computer-use agent, under the same
arm-independent success check. **OpenEMR** is the flagship real-EMR
head-to-head; **MockMed** is the CI-reproducible control anyone can rerun:

| Task | Compiled replay | Computer-use agent |
|---|---|---|
| **OpenEMR** (real third-party EMR, add-patient-note, 18 steps) | 20/20, 39.2s p50, **$0/run**, 0 model calls | 10/10, 70.4s p50, ~$0.55/run |
| **MockMed** (CI-reproducible triage task) | 100/100, 4.9s p50, **$0/run**, 0 model calls | 20/20, 37.5s p50, ~$0.27/run |

The compiled arm made no model calls and recorded no model-API cost in these
measured runs. This excludes authoring, review, infrastructure, exception, and
service costs. Full methodology and caveats live in the [openadapt-flow benchmark
docs](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark).

### Governed replay across verticals

On 2026-07-21, the paid computer-use agent arm was run on all three pinned,
synthetic reference environments. Each trial began from a reset baseline,
drove the same task contract as the compiled reference, and was classified by
an arm-independent system-of-record oracle rather than pixels or the agent's
self-report. The agent used `claude-sonnet-5` with explicit action and cost
caps.

| Vertical (pinned, synthetic) | Earlier compiled / API reference | Paid computer-use agent |
|---|---|---|
| **Insurance** (openIMIS claim intake) | 3/3 compiled replays SQL-verified, $0, 0 model calls | **3/3 correct**, 0/3 over-halt, 0/3 silent incorrect, $0.4793/run |
| **Lending** (Frappe Lending loan application) | compiled + API 12/12 correct, $0, 0 model calls | **6/6 correct writes** (5/6 clean), 1/6 post-write cost-cap over-halt, 0/6 silent incorrect, $0.4240/run |
| **Healthcare** (OpenEMR patient registration) | compiled + API 12/12 correct, $0, 0 model calls | **0/6 correct; 6/6 missing write**, 0/6 over-halt, 0/6 silent incorrect, $0.8901/run |

These are **not matched head-to-head rows**. The paid-agent trials used newly
provisioned baselines separate from the earlier compiled/API subsets, and the
sample is small (3-6 trials per environment). They are local engineering
evidence, not a publication matrix, certification result, or broad claim about
computer-use agents. The OpenEMR row is an honest negative result: all six
bounded runs ended after exhausting their action budget without writing a
patient.

All three environments used synthetic data on one local host and ran through
the **Browser (Playwright)** substrate, whose reference path is **Beta**. The
healthcare row is distinct from the shared-public-demo OpenEMR field result
above. Frappe Lending and openIMIS are API-rich references, and neither is
evidence for a legacy Windows/Citrix system.

The public [aggregate report](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark/agent_arm_verticals)
retains the method, run counts, outcomes, failure taxonomy, and caveats. Raw
per-run rows, environment fingerprints, detailed spend records, and
application-specific driver/oracle recipes are retained privately and are not
part of the public repository or package.

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
