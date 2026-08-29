# Concepts

How OpenAdapt works: what a demonstration compiler is, how a compiled workflow
resolves and verifies each step, and how safety is enforced. Read in order, or
jump to what you need.

<div class="grid cards" markdown>

-   [__The demonstration compiler__](demonstration-compiler.md)

    Why compile a demonstration instead of re-reasoning through it. The
    record, compile, replay loop.

-   [__The substrate model__](substrate-model.md)

    How one runner contract routes work across browser, native Windows, native
    macOS, native Linux, RDP, and Citrix/VDI.

-   [__The deployment matrix__](deployment-matrix.md)

    Hosted browser launch, customer-controlled execution, self-hosting, and the
    authoring-versus-runtime data boundary.

-   [__Regulated execution__](regulated-execution.md)

    `replay` is the local $0 dev path; `run` refuses to execute unless
    certified, identity-covered, effect-verified, signed, and config-pinned.

-   [__The capability ladder__](capability-ladder.md)

    One semantic step, many implementations: structural (DOM/UIA), API, and
    visual. First viable rung wins.

-   [__Effect verification__](effect-verification.md)

    The screen is not the system of record. The five silent write faults and
    how OpenAdapt catches them.

-   [__The identity gate__](identity-gate.md)

    How the identity ladder distinguishes records and refuses ambiguous input.

-   [__Governed self-healing__](self-healing.md)

    Repairs under UI drift, written back as reviewable diffs, with zero model
    calls on the healthy path.

-   [__The workflow-program IR__](workflow-ir.md)

    Typed parameters, guards, `wait_until`, loops, branches, and subflows. A
    compiled workflow uses these elements to express the intended work.

-   [__Multi-trace induction__](multi-trace-induction.md)

    How several demonstrations provide enough evidence to recover a more
    complete program.

-   [__The halt-learn loop__](halt-learn-loop.md)

    Demonstrate a correction, compile it, and pass it through regression and
    promotion gates before the workflow uses it.

-   [__Durable runtime__](durable-runtime.md)

    Checkpoint verified progress; a halt becomes a durable pause an operator
    approves and resumes, never re-running a confirmed write.

-   [__Policy and certify__](policy-and-certify.md)

    `lint` reports gaps, `certify` refuses an unsafe bundle before it deploys.

-   [__Read a compiled program__](program-visualizer.md)

    The program map, live evidence, a composed parent, and a process parent.

-   [__Process contracts__](process-contract.md)

    A parent receipt over independently admitted capabilities. Handoffs copy
    effect facts. Compose sequences recordings; process points at admissions.

-   [__Backends: where it runs__](backends.md)

    Browser (Playwright), native Windows (UIA), native macOS, native Linux
    (AT-SPI), RDP, and Citrix/VDI use one backend protocol. Each surface uses
    the same bundle, identity, result, and policy contracts. Each workflow is
    qualified in its real environment.

-   [__The on-prem VLM appliance__](vlm-appliance.md)

    Optional local grounding and identity. When deployed on-prem, observations
    remain inside that declared customer boundary.

</div>
