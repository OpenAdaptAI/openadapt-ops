---
title: OpenAdapt documentation
description: >-
  OpenAdapt takes the last manual step off your team. It enters approved
  information into the systems you already use and checks that it saved. When
  something doesn't match, it stops and asks a person instead of guessing.
hide:
  - toc
---

# Take the last manual step off your team

<p class="oa-lede">
OpenAdapt enters approved information into the systems you already use, such
as EMRs, payer portals, and desktop and Citrix apps, and checks that it saved.
When something doesn't match, it stops and asks a person instead of guessing.
</p>

<div class="grid cards" markdown>

-   [__Evaluate it for one workflow (no install)__](evaluate/index.md)

    See what changes in your team's day, what you control, where your data
    stays, and how a first project runs, in plain language.

-   [__Install and run it yourself__](get-started/index.md)

    The engine is free and open source (MIT). Install the Desktop app, or run
    `pip install openadapt` with Python 3.10 to 3.12, and try the tutorial on
    your own computer.

</div>

[Watch a recorded run on OpenEMR with synthetic data](https://app.openadapt.ai/demo){ .md-button }

---

## What happens in one run

1. Someone on your team does the task once while OpenAdapt records it.
2. OpenAdapt turns the recording into a fixed set of steps. Your team tests
   it on your own cases before it handles real work.
3. For each item, it opens the record, checks that it's the right patient or
   account, and enters the approved information.
4. It reads the saved record back through a second path, such as a report, an
   API, or a read-only login, and compares it with what it meant to enter.
5. If everything matches, the item is done and checked, and you get a receipt.
   If something doesn't match, it stops and asks a person.

A normal run makes no AI model calls. For work with patient data, your screens
and records stay on a computer you control. Read
[Security and where data stays](evaluate/security.md) for the details, or the
[glossary](evaluate/glossary.md) for the terms the technical pages use.

---

## For developers, IT, and AI agent teams

The rest of this page uses the technical terms. OpenAdapt compiles a
demonstration into a program that a person or an agent can invoke. Healthy runs
make no model calls. Uncertainty escalates to a person.

<div class="grid cards" markdown>

-   __An inspectable program__

    The compiler turns the demonstrated actions into explicit steps,
    parameters, guards, and expected state changes. You can review the program
    before it runs.

    [The demonstration compiler](concepts/demonstration-compiler.md)

-   __Evidence for each consequential step__

    A step can carry structural selectors, accessibility data, visual anchors,
    identity requirements, and a declared result check. The available evidence
    depends on the application surface.

    [The capability ladder](concepts/capability-ladder.md)

-   __A typed outcome and report__

    `VERIFIED` means the declared result check passed. A run that cannot meet
    its identity, result, policy, or state requirements stops and records the
    reason.

    [Run outcomes](reference/run-outcomes.md)

</div>

The healthy path follows the approved program with no generative-model API
calls. When the interface changes, OpenAdapt first uses the evidence retained
from the demonstration. A configured model can propose a repair when policy
permits. The repaired version passes the same review and qualification gates
before promotion.

OpenAdapt separates action delivery from result verification. A save message
on the acting screen does not prove that the intended record changed. A
workflow can verify the result through an API, database, document store,
read-only session, or persisted-state reacquisition.

[Read about effect verification](concepts/effect-verification.md){ .md-button }
[Read about identity checks](concepts/identity-gate.md){ .md-button }

---

## Where it runs

| Surface | Execution options | Evidence available |
|---|---|---|
| Browser | Local, customer-controlled, or managed for approved workflows | DOM, accessibility, visual, geometry, and interaction evidence |
| Windows, macOS, Linux | Local or customer-controlled | Native accessibility data plus retained visual evidence |
| RDP, Citrix, VDI | Local or customer-controlled | Window-scoped pixels, keyboard, mouse, OCR, and visual anchors |

Each workflow is qualified against its exact application, environment,
identity rules, result verifier, and deployment boundary. The
[qualification evidence](get-started/what-works-today.md) records the supported
scope and its limits.

Sensitive runtime observations stay inside the declared execution boundary.
Only an approved, sanitized derivative can cross that boundary.

[Compare deployment options](concepts/deployment-matrix.md){ .md-button }
[Review security and data handling](guides/security-and-data-handling.md){ .md-button }

---

## Inspect the evidence

The public references include the source demonstration, compiled replay,
declared verifier, run counts, failure categories, and limits for each claim.
The visual demo helps you understand a run. The result verifier and retained
report determine its outcome.

[Watch the real-application demo](https://app.openadapt.ai/demo){ .md-button .md-button--primary }
[Review qualification evidence](get-started/what-works-today.md){ .md-button }
[Read the benchmark methods](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/benchmark){ .md-button }

[Check the current Production status](reference/production-lifecycle.md){ .md-button }

---

## Connect an AI agent

OpenAdapt is the governed last mile an agent calls when the next write has no
API. A person or a local agent they watch demonstrates. A named human admits
the program. The calling agent operates it. The human returns for identity,
effect, and judgment halts, then samples seals.

OpenAdapt supports automation teams, BPOs, service providers, and software
companies that operate browser, native desktop, RDP, Citrix, or other virtual
desktop applications.

!!! info "What the calling agent may do / must not do"
    **May:** bind declared parameters, invoke a compiled program, read
    `VERIFIED` / `HALTED` / `RECONCILIATION_REQUIRED`, supply a missing
    declared parameter, retry a retryable transport failure, escalate.

    **Must not:** summarize halt as success, resolve an identity or effect
    contradiction, teach by emitting guessed clicks, or be the sole source of
    a production demonstration.

    Machine contract: [agents.txt](agents.txt). Outcome vocab:
    [Run outcomes](reference/run-outcomes.md).

---

## Choose your next step

<div class="grid cards" markdown>

-   [__Evaluate one workflow__](evaluate/index.md)

    What changes for your team, four worked examples, and how a first project
    runs. No install needed.

-   [__Install OpenAdapt__](get-started/index.md)

    Desktop or pip on this computer. Tutorial is optional.

-   [__Author a workflow__](get-started/first-workflow.md)

    A person or a local agent they watch records one browser workflow.
    A named human admits the compiled program and inspects the report.

-   [__Prepare a production workflow__](guides/qualify-a-workflow.md)

    Define the identities, results, failure cases, policy, and deployment
    boundary for one exact workflow.

</div>
