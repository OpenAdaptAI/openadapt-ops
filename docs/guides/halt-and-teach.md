# The halt → teach loop

A governed workflow **halts** rather than guesses: when a step meets a situation
its demonstration never covered — an unexpected dialog, a new confirmation, a
changed field — it stops and writes the halt into the run report instead of
clicking something plausible. The **halt → teach loop** is how you resolve that
permanently: demonstrate the fix once, and `teach` compiles it back into the
workflow so the same situation never halts again.

This is the self-serve alternative to filing a bug and waiting. It runs through
the [governed induction path](../concepts/halt-learn-loop.md), so a *bad* fix is
**refused**, not merged.

!!! note "This loop is real today"
    Unlike the desktop and managed-deployment pages, `teach` is fully wired in the
    CLI and runs `$0` on the shipped path (the correction is induced by the
    model-free reference inducer). The one target-state seam is noted at the end.

## 1. A run halts

When a run halts, it exits nonzero and the run directory holds a `report.json`
whose halt names the violated expectation:

```bash
openadapt flow run bundle --config deployment.yaml
# ... Replay FAILED: runs/replay-20260714-craft/REPORT.md
```

Open `REPORT.md`: the halt tells you which step stopped and why (for example, "an
unexpected confirmation dialog blocked the Save click"). Nothing was guessed and
no consequential write was performed past the halt. If the run was
[durable](../concepts/durable-runtime.md), it paused at the last verified
checkpoint instead of unwinding.

## 2. Demonstrate the fix once

Record **only the corrective actions** — the minimal steps that resolve the
situation (e.g. dismiss the dialog and continue). Keep it tight: `teach` induces
exactly what you show.

```bash
openadapt flow record --url https://your.app --out recordings/dismiss-the-dialog
# perform ONLY the fix: dismiss the dialog. Then stop.
```

For scripted or CI use, a `.json` correction spec works instead of a recording
(`resolution_steps`, optional `tail_intents` / `facts` / `params`).

## 3. Teach the correction

`teach` takes the halted run, the fix demonstration, and the base bundle, and
writes an **updated bundle only if the correction passes** its gates:

```bash
openadapt flow teach runs/replay-20260714-craft \
  --fix recordings/dismiss-the-dialog \
  --bundle bundle \
  --out bundle-v2
```

Under the hood, `teach`:

1. **Induces** the correction as a *guarded exception branch* — it fires only in
   the situation that halted, not unconditionally.
2. **Gates** it against a regression check (the base workflow still passes) and a
   held-out canary (the fix generalizes, it is not overfit to one frame).
3. **Promotes** the revision into a versioned skill library that keeps the full
   lineage — only if both gates pass.

## 4. Re-run — it no longer halts

```bash
openadapt flow replay bundle-v2
# the workflow now handles the dialog and continues
```

## When teach refuses

A refusal is the feature working, not a failure:

| Exit | Meaning | What to do |
|---|---|---|
| `0` | Promoted | The verified revision is at `--out`; deploy it. |
| `1` | **Governed refusal** | The correction was underdetermined or would weaken a safety invariant. Nothing was written; the base bundle still halts here. Supply a clearer or safer fix. |
| `2` | Unusable inputs | No halt in the report, no base bundle, or a malformed fix. Fix the inputs. |

A governed refusal never leaves you with a silently-weakened bundle. The base
bundle keeps halting on the situation until a fix passes — which is the safe
default for a regulated workflow.

## Target-state seam

When the fix is demonstrated on a **desktop / Citrix** surface, the `record` step
uses a desktop backend that is [not yet wired into the CLI](desktop-and-citrix.md#what-is-not-yet-wired).
The `teach` induction, gating, and promotion themselves are substrate-agnostic
and unchanged. See [The halt-learn loop](../concepts/halt-learn-loop.md) for the
concept and [`teach` in the CLI reference](../reference/cli.md#teach) for every
flag.
