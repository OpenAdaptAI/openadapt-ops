# The workflow-program IR

Today's compiled bundle is a **trajectory**: a flat list of steps, one recorded
moment each. That is the correct v0, and also a ceiling. The workflow-program IR
evolves that linear action list into a **parameterized program**: a state
machine with typed parameters, guards, `wait_until` predicates, loops, branches,
subflows, effects, and exception handlers.

!!! note "Status"
    The linear v0 IR ships today and is stable. The full workflow-program IR is
    a design that lands in phases, and each phase is backward compatible: the
    linear workflow is the degenerate case of the program (one entry state,
    unconditional fall-through, no loops).

## Why a trajectory is not enough

A single demonstration under-specifies intent. The compiler already spends most
of its effort guessing which observed facts are invariant and which incidental.
A straight-line trace cannot express:

- **Conditionals**: a survey modal that *sometimes* appears after Save is not
  drift, it is a branch the operator handles.
- **Loops**: clearing one task from a queue of fifteen does not itself say
  "repeat for every open task."
- **The failure branch**: a successful trace never shows what should happen when
  the result is absent or wrong.
- **Essential versus incidental order**: fill three independent fields in any
  order, but Save last. The trace imposes a total order; the intent is usually
  partial.

The next unit of value is recovering the **intended program**, not replaying the
**observed trajectory**.

## What the program adds

The workflow-program IR promotes the flat step list into a state machine:

- **Typed parameters**: a value the workflow varies per run, with a declared
  type, instead of a literal baked into every assertion.
- **Guards and `wait_until`**: a transition fires only when its precondition
  holds, so a slow render waits instead of racing.
- **Loops over worklists**: iterate a semantic action across a data-dependent
  list.
- **Branches and subflows**: handle an optional modal, or factor a shared
  sub-task out of several workflows.
- **Effects**: the typed system-of-record assertions that
  [effect verification](effect-verification.md) checks (`record_written`,
  `field_equals`), with per-step risk and compensation.
- **Exception handlers and human-approval nodes**: an explicit place to pause,
  escalate, or ask.

## One meaning, many implementations

A single semantic transition in the IR can compile to backend-specific
implementations (API, DOM/UIA, visual), each satisfying the **same contract**.
This is [the capability ladder](capability-ladder.md) in the schema: the IR
separates *what* a step means from *how* the current app permits it, so a
workflow can retarget across surfaces without a rewrite.

## A tiered runtime

The program runs on a tiered runtime with a deliberate ceiling on how much the
model is trusted to do:

1. a **deterministic fast path** (the resolution ladder, $0),
2. a **bounded model recovery** of exactly one local transition when the fast
   path cannot resolve it,
3. a **[durable pause, approve, resume](durable-runtime.md)** from the last
   verified checkpoint.

Recovery is scoped to a single transition. After a halt, OpenAdapt does not
hand the rest of the workflow to a free-form agent. The checkpoint is where a
human takes over if the next action is not determined. When a human
demonstrates the fix at a halt, the [halt-learn loop](halt-learn-loop.md) folds
it back into the program through the same governed induction and regression
gate, so that state need not halt again.

The IR is how OpenAdapt gets from "replay this one demonstration safely" to
"run this program safely across the variation the real world throws at it." How
a program is *recovered* from more than one demonstration is
[multi-trace induction](multi-trace-induction.md).
