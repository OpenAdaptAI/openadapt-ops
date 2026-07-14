# Concepts

These pages explain the model behind OpenAdapt: what a demonstration compiler
is, how a compiled workflow resolves and verifies each step, and how safety is
enforced. Read them in order for the full picture, or jump to what you need.

<div class="grid cards" markdown>

-   [__The demonstration compiler__](demonstration-compiler.md)

    Why compile a demonstration instead of re-reasoning through it. The
    record, compile, replay loop.

-   [__The substrate model__](substrate-model.md)

    One substrate-agnostic runner drives web, native Windows, and pixel-only
    Citrix/RDP. Route on one field; everything above it is identical.

-   [__The deployment matrix__](deployment-matrix.md)

    Our cloud, BYOC (your VPC), or air-gapped self-hosted. You choose where the
    data lives; the PHI-free control/data boundary is architectural.

-   [__Fail-closed regulated execution__](regulated-execution.md)

    `replay` is the local $0 dev path; `run` refuses to execute unless
    certified, identity-covered, effect-verified, signed, and config-pinned.

-   [__The capability ladder__](capability-ladder.md)

    One semantic step, many implementations: structural (DOM/UIA), API, and
    visual. First viable rung wins.

-   [__Effect verification__](effect-verification.md)

    The screen is not the system of record. The five silent write faults and
    how OpenAdapt catches them.

-   [__The identity gate__](identity-gate.md)

    Never click the wrong record. The identity ladder and why it refuses
    rather than guesses.

-   [__Governed self-healing__](self-healing.md)

    Repairs under UI drift, written back as reviewable diffs, with zero model
    calls on the healthy path.

-   [__The workflow-program IR__](workflow-ir.md)

    Typed parameters, guards, `wait_until`, loops, branches, and subflows. A
    program, not a trajectory.

-   [__Multi-trace induction__](multi-trace-induction.md)

    One demo is evidence, not a specification. How more traces recover the
    intended program.

-   [__The halt-learn loop__](halt-learn-loop.md)

    Halt, demonstrate the fix, induce it through a regression gate, and never
    halt there again. Governed, $0, no free-form agent.

-   [__Durable runtime__](durable-runtime.md)

    Checkpoint verified progress; a halt becomes a durable pause an operator
    approves and resumes, never re-running a confirmed write.

-   [__Policy and certify__](policy-and-certify.md)

    Fail-closed safety: `lint` reports gaps, `certify` refuses an unsafe
    bundle before it deploys.

-   [__Backends: where it runs__](backends.md)

    Web (Playwright), desktop Windows (UIA), and pixel-only RDP behind one
    backend protocol. The ladder is backend-agnostic.

-   [__The on-prem VLM appliance__](vlm-appliance.md)

    Optional local grounding and identity. Data stays in the building.

</div>
