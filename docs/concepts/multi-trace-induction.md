# Multi-trace induction

One demonstration is **evidence**, not a **specification**: it shows what
happened once, not what should happen every time. Multi-trace induction recovers
the intended program from more than one demonstration, and refuses to emit a
workflow while intent stays ambiguous.

!!! note "Status"
    Induction ships today as the [`induce`](../reference/cli.md#induce) verb: it
    takes two or more recordings of the same task and emits a parameterized
    program bundle, or refuses (nonzero exit, no bundle) when intent is
    underdetermined. It builds on the shipping compiler, which already treats a
    demonstration as evidence when it decides which values are parameters and
    which screen text is incidental. The full workflow-program IR it targets
    lands in phases (see [the workflow-program IR](workflow-ir.md)).

## Why one trace under-determines intent

The compiler already knows a single trace is ambiguous, because most of its work
is resolving that ambiguity:

- **Which literal values are parameters.** The demo shows a note of
  "Follow-up in 2 weeks." Nothing in one trace says whether the *patient*, the
  *encounter type*, or the *priority filter* were meant to be fixed or free.
- **Which screen text is incidental.** Clocks and counters versus a date of
  birth. One frame cannot tell you which is invariant.
- **The absent branch.** A single successful trace never shows the failure path.
- **The loop.** One pass over a worklist does not reveal that the operator meant
  to repeat it.

## The induction loop

Induction turns several demonstrations into a program by proposing, questioning,
and validating:

```mermaid
flowchart TD
    A[Bootstrap one interpretation<br/>from one demo] --> B[Enumerate candidate<br/>generalizations]
    B --> C{Ambiguous?}
    C -->|yes| Q[Ask the operator a concrete<br/>multiple-choice question]
    Q --> D[Fold in additional traces]
    C -->|no| D
    D --> E[Infer the shared<br/>control-flow graph]
    E --> F[Validate on held-out traces<br/>plus synthetic perturbations]
    F -->|underdetermined| G([Quarantine:<br/>refuse to emit])
    F -->|resolved| H([Emit workflow program])
```

1. **Bootstrap** one interpretation from one demonstration.
2. **Enumerate** candidate generalizations (is this value a parameter, is this
   step a loop body).
3. **Resolve ambiguity by asking**: surface concrete multiple-choice questions
   to the operator.
4. **Fold in additional traces** and infer the shared control-flow graph.
5. **Validate** on held-out traces and synthetic perturbations.
6. **Quarantine** when intent stays underdetermined: refuse to emit a workflow
   that might do the wrong thing.

## Induce a program

Point `induce` at several recordings of the same task. It aligns them, recovers
the shared parameters, loops, and branches, and either **certifies** a program
bundle or **refuses** and lists what stayed underdetermined.

```bash
openadapt flow induce rec-1 rec-2 rec-3 --out program --name my-program --held-out
```

`--held-out` also runs leave-one-out validation and prints per-fold reproduction
scores. A certified program can then loop over a data source with
[`replay --worklist`](../guides/induce-a-program.md#run-a-program-over-a-worklist).
The worked walkthrough is in
[Induce a program from multiple traces](../guides/induce-a-program.md).

## Disambiguate before certify

The disambiguation step ships as a CLI verb. It surfaces the compile-time
questions an ambiguous demonstration raises and applies the answers as guards or
parameters, so a consequential ambiguity must be answered before the bundle is
certified.

```bash
openadapt flow disambiguate bundle --interactive --write
```

A consequential (must-answer) ambiguity exits nonzero until it's resolved. When
the right action isn't determined, stop and ask.

OpenAdapt spent enormous effort making a *single trace* safe: the
[identity ladder](identity-gate.md), volatility mining, postconditions,
[effect verification](effect-verification.md). That work is necessary, and it
still leaves the trace under-specified. Induction recovers the intended
program. Quarantine withholds a program when it cannot.
