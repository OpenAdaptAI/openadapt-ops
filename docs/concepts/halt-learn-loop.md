# The halt-learn loop

A [halt](identity-gate.md) is honest, but a halt that teaches the system nothing
means the same unhandled state halts forever. The halt-learn loop closes that
gap: an operator demonstrates the fix once, the correction is folded into the
workflow *through the governed induction path*, a regression gate proves the
revision weakens nothing, and that state never halts again.

Crucially, it does this **without ever handing control to a free-form agent**
and **without any model call on the runtime path**. Learning is governed, and a
revision is adopted only if it provably does not regress safety.

## The loop

```mermaid
flowchart TD
    H([Run halts on an<br/>unhandled state]) --> T[Halt emits a<br/>learnable execution trace]
    T --> D[Operator demonstrates<br/>the resolving actions]
    D --> I[Goverened induction:<br/>compile the fix as a<br/>guarded branch]
    I --> G{Regression gate +<br/>held-out canary}
    G -->|weakens identity / effect /<br/>risk, or underdetermined| Q([Quarantine:<br/>stays halting])
    G -->|covers the new case,<br/>regresses nothing| P([Promote revision:<br/>never halts here again])
```

1. **A halt emits a learnable trace.** The run report records the halt point,
   the unexpected on-screen text, and the completed pre-context — lifted into
   the same `ExecutionTrace` type the learning loop already consumes.
2. **The correction is a demonstration.** The operator's resolving actions
   (dismiss the modal, then continue) extend the halt's pre-context, exactly the
   shape a normal recording produces.
3. **Induce through the governed path.** The demonstration feeds the same
   multi-trace [induction](multi-trace-induction.md) machinery, which compiles
   the resolution as a **guarded conditional branch** on the workflow-program
   graph — not a special case bolted on.
4. **Gate, then canary.** A candidate revision must pass a deterministic
   **regression gate** and a held-out **canary** before it is promoted.
5. **Promote or quarantine.** Only a revision that covers the new case *and*
   regresses nothing becomes active. If the single correction underdetermines
   the generalization, the loop **refuses to promote** and the workflow stays
   halting — the same discipline as induction.

## The regression gate: what a revision may not weaken

The gate is the heart of "governed." A learned revision may change *how* a step
is performed (its locator, its rung) but must never silently weaken *what the
workflow means*. It traverses **both** programs (subflows included), matches
consequential actions by structural role rather than raw step id, and
quarantines a candidate that would:

- drop or weaken a **reachable consequential/irreversible action**, or make one
  reachable under *more* conditions than before;
- shrink the set of **identity checks** that must pass before a write;
- lose a system-of-record **effect contract**, or add a new consequential action
  **without** effects;
- **downgrade a risk label** (irreversible → reversible);
- drop an **approval requirement** on an action that needed operator
  confirmation.

Any of these quarantines the revision with a reason. A revision that merely
"covers more traces" does not pass if it costs any of the above.

## Versioned, provenance-tracked skills

Promoted revisions live in a versioned skill library that keeps every revision's
provenance and status, and never silently adopts an unverified one. A quarantined
candidate is retained with its rejection reason; the active version is unchanged.

## Driving it: `openadapt flow teach`

The whole demonstrate-and-promote flow runs from one command. Point `teach` at
the halted run directory (the one holding `report.json` with a `halt`), give it
the fix demonstration and the base bundle that halted, and name where a promoted
bundle should be written:

```bash
openadapt flow teach runs/replay-20260712-140233 \
    --fix recordings/dismiss-the-dialog \
    --bundle bundles/patient-intake \
    --out bundles/patient-intake-v2
```

| Flag | Description |
|---|---|
| `run_dir` (positional) | The HALTED run directory (holds `report.json` with a `halt`) |
| `--fix` (required) | The fix demonstration: a **recording directory** of just the corrective actions (e.g. dismiss the dialog), or a `.json` correction spec (scripted / CI: `resolution_steps`, optional `tail_intents` / `facts` / `params`) |
| `--bundle` (required) | The base bundle that halted (seeds the skill's active version) |
| `--out` (required) | Output directory for the UPDATED bundle, **written only when the correction is promoted** |
| `--skill-id` | Skill id in the versioned library (default: the run's workflow name) |
| `--library` | Directory for the versioned skill library that keeps the promotion lineage (default: `<out>.skills`) |

`teach` wires the existing governed loop end to end: it loads the halt, turns
the fix into the operator-correction trace, runs induction, the regression gate,
and the held-out canary, and writes `--out` **only** if the revision is promoted.
On the shipped path it is deterministic and makes **no model calls** ($0): the
resolution is induced by the model-free reference inducer (the structural-diff
inducer that handles the "an unexpected optional dialog intercepted the
workflow" class the loop was built for). A model-backed inducer wires in behind
the same `Inducer` seam without touching this flow.

**The refusal path is a normal outcome, not an error.** If the single correction
underdetermines the generalization, or the induced revision would weaken a
safety invariant, the loop **refuses to promote**: nothing is written to `--out`,
the base bundle stays halting exactly as before, and the command exits nonzero
(`1`) with the reason. Unusable inputs (no halt in the report, no base bundle, a
malformed fix) are a distinct failure and exit `2`. A successful promotion exits
`0` and prints the re-run command.

!!! note "What is proven, and what depends on the inducer"
    The loop's **governance** (the regression gate, the held-out canary, the
    versioned skill library, the halt→demonstration bridge) is proven
    independently of any particular induction implementation, because the
    inducer is injected behind an `Inducer` seam and a deterministic reference
    inducer exercises the loop in tests. The reference inducer covers the
    optional-dialog resolution class; generalizing to arbitrary corrections is
    the job of a richer inducer behind that same seam, and it inherits the same
    gate.

## Why this shape

Every other safety mechanism in OpenAdapt refuses rather than guesses. The
halt-learn loop is how the system *improves* without abandoning that posture: the
only thing trusted to generalize a fix is a demonstration plus a gate, and the
gate is biased exactly the way the runtime is — a revision that might weaken
safety is quarantined, not shipped. It is the counterpart to
[multi-trace induction](multi-trace-induction.md) (recover the program from
several traces) and [policy and certify](policy-and-certify.md) (refuse a bundle
whose gaps were not closed): learn only what you can prove safe.
