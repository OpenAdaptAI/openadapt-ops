---
description: >-
  How OpenAdapt decides that a save happened, which kinds of read-back count
  for which result, and what the main branch enforces today.
---

# How a save is checked

A record check is how OpenAdapt checks its own work. After a save, it reads
the record back and compares the fields it typed. That catches a value in
the wrong field, an entry on the wrong record, a missed keystroke, a
duplicate submit, or a step that ran before the page was ready. The
confirmation on screen shows that a save happened, not what was stored, so
it isn't used as proof. A record check returns `confirmed`, `refuted`, or
`indeterminate`. Only `confirmed` lets a run continue.

![On the acting surface, the app screen OpenAdapt types into, a run checks that the right record is on screen, then enters and saves. It then reads the record back. A screen read-back uses the app's UI in a separate session and is not independent. An independent read uses the system of record through its API, database, or file export, never through the UI. If the read matches, the run ends VERIFIED with a run report and a receipt; OpenAdapt Cloud signs a Seal only after an independent read. If it doesn't match or can't tell, the run ends RECONCILIATION_REQUIRED and a person checks the record. If the right-record check fails, the run ends HALTED_BEFORE_EFFECT before saving and asks a person.](../assets/diagrams/record-check.svg)

## How strong a read-back is

The engine ranks every read-back by how independent it is of the screen that
did the work:

| Rank | Read-back | Example |
|---|---|---|
| 1, strongest | The system of record, through its API, database, or files | REST, GraphQL, FHIR, read-only SQL, a file or report drop, an email capture folder |
| 2 | The app's record page in a separate, separately signed-in, read-only session | `ui_readback` |
| 3 | The same session navigates back to the record and reads it again | |
| 4, weakest | The screen that did the work still shows the value | |

A rank-2 read is independent of the session that acted, but it still reads
a screen. It can't tell a record the app stored from one the app only
displays.

## What each result needs

**`VERIFIED` under Standard or Regulated.** On the `main` branch and in
`openadapt-flow` 2.1.0, every save must be confirmed at rank 2 or stronger:
the system of record, or a separate-session `ui_readback`. The `regulated`
policy pack raises that to rank 1. Ranks 3 and 4 can never produce
`VERIFIED`. A pixel-only Citrix save with no rank-1 or rank-2 read ends in a
halt or `RECONCILIATION_REQUIRED`, whatever an operator or the screen says.

**Certification through qualification.** Qualification labels each read
`independent_readback` (rank 1), `screen_readback` (any read through the
app's screens, including `ui_readback`), or `unchecked`. To certify, the
normal case must be confirmed and every fault case must show nothing landed,
all at `independent_readback`. A workflow whose only read-back is
`ui_readback` can run the cases but can't be certified this way.

**A Seal.** OpenAdapt Cloud signs a Seal only when the run was confirmed by
a system-of-record read.

## What a record check catches

On 21 July 2026 we ran ten scenarios through the governed runtime against a
local test system, 9 runs each, 90 runs in all. Nine scenarios were faults we
injected into the save. In 72 runs the record ended up wrong: missing,
partial, duplicated, on the wrong record, with other data overwritten, or
with an extra write to another table. Three checks judged the same runs:

| Check | Wrong records it reported as saved |
|---|---|
| The success message on the screen | 54 of 72 |
| A read of the record through the app's REST API | 9 of 72, all extra writes to a billing table that this read didn't cover |
| A read-only SQL query over every table a save could change | 0 of 72 |

Each check also stopped 9 of the 18 runs that saved correctly, because the
reply to the save never reached the client. A record check catches what its
read can see, so it should cover every table a save can change. These
were faults we wrote and injected into our own engine: a coverage test over a
fixed list, not a real-world error rate.
[Method and per-fault results](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/effect_e2e/EFFECT_E2E.md).

## How a save is approved

Checking a save and approving one are separate, and both are separate from
admission, which happens once per workflow. The approval mode decides
whether a run waits for an answer before each save:

- `each_item`: the run waits before each save until the filled form is
  approved. This is what `openadapt flow run` uses unless another mode is
  set. [Run a workflow](../how-to/run.md#3-choose-how-saves-are-approved)
  shows how to answer.
- `problems_only`: only saves that fail a check go to a person. It isn't
  available to customers yet; until it is configured, every save still asks.
- `not_gated`: no pause. Runs that OpenAdapt Cloud dispatches use this, and
  every report records it.

An approval never replaces the record check. An approved save that the
record check can't confirm still doesn't end `VERIFIED`.

## Why stopping is the default

Each check is three-valued, and both `refuted` and `indeterminate` stop the
run. An unreachable database, a timeout, or an ambiguous read is never
treated as success. The cost is that a run sometimes stops when the save was
fine; the [limits](limits.md) page covers when that happens most. The
alternative, a run that reports success when the record is wrong, is the
failure OpenAdapt is built to prevent.
