# Concepts

These pages explain the model behind OpenAdapt: what a demonstration compiler
is, how a compiled workflow resolves and verifies each step, and how safety is
enforced. Read them in order for the full picture, or jump to what you need.

<div class="grid cards" markdown>

-   [__The demonstration compiler__](demonstration-compiler.md)

    Why compile a demonstration instead of re-reasoning through it. The
    record, compile, replay loop.

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

-   [__Policy and certify__](policy-and-certify.md)

    Fail-closed safety: `lint` reports gaps, `certify` refuses an unsafe
    bundle before it deploys.

-   [__The on-prem VLM appliance__](vlm-appliance.md)

    Optional local grounding and identity. Data stays in the building.

</div>
