# Induce a program from multiple traces

A single demonstration is evidence, not a specification: it cannot show which
values are parameters, where a branch or loop belongs, or what the failure path
is. `induce` recovers a parameterized **program** from several demonstrations of
the same task, and refuses rather than guesses when the traces leave intent
underdetermined. For the model behind this, see
[Multi-trace induction](../concepts/multi-trace-induction.md).

## Record the same task more than once

Record the task a few times, varying the values you intend to be parameters (a
different note, a different record) and keeping the intended path the same:

```bash
openadapt flow record --backend web --url https://your.app --out rec-1
openadapt flow record --backend web --url https://your.app --out rec-2
openadapt flow record --backend web --url https://your.app --out rec-3
```

## Induce

Feed the recordings (or already-compiled bundles) to `induce`:

```bash
openadapt flow induce rec-1 rec-2 rec-3 --out program --name my-program
```

`induce` aligns the traces to recover the shared parameters, loops, and branches.
It is deterministic and model-free at its core. The outcome is one of two explicit
results:

- **CERTIFIED**: it writes a parameterized program bundle to `--out` and prints
  the parameters and column decisions it inferred.
- **NOT CERTIFIED**: it writes **no bundle** and exits nonzero, listing exactly
  what stayed underdetermined. Refuse-rather-than-guess: a CI or deploy gate will
  refuse an ambiguous program.

Resolve an underdetermined program by supplying more or more-consistent traces,
or by answering the questions [`disambiguate`](../concepts/multi-trace-induction.md)
surfaces.

### Validate on held-out traces

With three or more traces, add `--held-out` to run leave-one-out validation and
print per-fold reproduction scores, showing how well the induced program
reproduces a trace it was not fit on:

```bash
openadapt flow induce rec-1 rec-2 rec-3 --out program --name my-program --held-out
```

## Run a program over a worklist

A program with a loop over a relation runs that loop over a data source you
supply at replay time: a `--worklist` file of parameter rows (CSV or JSON). Each
row is one iteration's bindings.

```bash
# bind a CSV to the program's sole loop relation
openadapt flow replay program --worklist patients.csv

# bind a named file to a named relation (repeatable)
openadapt flow replay program --worklist referrals=todays_referrals.json
```

- A CSV's header row names the parameters; each subsequent row is one iteration.
- A JSON worklist is a list of `{param: value}` row objects (or a single object
  for one row).
- A **bare** `--worklist FILE` binds to the program's single loop relation and
  errors if the program has zero or several; use `RELATION=FILE` to be explicit.
- `--worklist` applies only to a **program** bundle. Passing it to a linear
  bundle is refused loudly.

Every iteration runs the same governed machinery: the [identity gate](../concepts/identity-gate.md)
fires per row, and (when configured) [effect verification](../concepts/effect-verification.md)
confirms each write against the system of record. A production worklist run is
usually a [deployment run](run-a-deployment.md) with `--config`, so effects,
actuation, and durability are all configured.

## When one trace is enough

If your task has no real conditionals or loops and only varies typed values, you
do not need `induce`: record once and make the varying values
[parameters](parameters-and-secrets.md). Reach for `induce` when the intent spans
more than one path, or when you want held-out validation of the recovered
program.
