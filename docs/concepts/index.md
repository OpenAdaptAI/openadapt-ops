# Concepts

These pages explain the model behind OpenAdapt: what a demonstration compiler
is, how a compiled workflow resolves and verifies each step, and how safety is
enforced. Read them in order for the full picture, or jump to what you need.

<div class="grid cards" markdown>

-   [__The demonstration compiler__](demonstration-compiler.md)

    Why compile a demonstration instead of re-reasoning through it. The
    record, compile, replay loop.

-   [__The substrate model__](substrate-model.md)

    Routing across web, native Windows, native macOS, and pixel-only Citrix/RDP;
    one runner contract, every substrate first-class.

-   [__The deployment matrix__](deployment-matrix.md)

    Hosted browser launch, customer-controlled execution, self-hosting, and the
    authoring-versus-runtime data boundary.

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

    Browser (Playwright), native Windows (UIA), native macOS, RDP, and
    Citrix/VDI are all first-class substrates behind one backend protocol. The
    same bundle, resolution ladder, identity gate, and effect verification run on
    each; every workflow is qualified in its real environment.

-   [__The on-prem VLM appliance__](vlm-appliance.md)

    Optional local grounding and identity. When deployed on-prem, observations
    remain inside that declared customer boundary.

</div>
