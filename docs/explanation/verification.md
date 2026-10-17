---
description: >-
  How OpenAdapt decides that a save happened, which kinds of read-back count
  for which result, and what the main branch enforces today.
---

# How a save is checked

A screen can show "Saved" when nothing was stored: an optimistic page, a
save that failed on the server, a duplicate submit. OpenAdapt therefore
never takes the screen's word for a save. A record check reads the record
back and returns `confirmed`, `refuted`, or `indeterminate`. Only
`confirmed` lets a run continue.

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
halt or `RECONCILIATION_REQUIRED`, whatever an operator or a banner says.

**Certification through qualification.** Qualification labels each read
`independent_readback` (rank 1), `screen_readback` (any read through the
app's screens, including `ui_readback`), or `unchecked`. To certify, the
normal case must be confirmed and every fault case must show nothing landed,
all at `independent_readback`. A workflow whose only read-back is
`ui_readback` can run the cases but can't be certified this way.

**A Seal.** OpenAdapt Cloud signs a Seal only when the run was confirmed by
a system-of-record read.

A change under review would make a rank-1 read the requirement for
`VERIFIED` under every production profile. The rule above is what
`openadapt-flow` 2.1.0 and `main` enforce.

## How a save is approved

Checking a save and approving one are separate. The approval mode decides
whether a run waits for an answer before each save:

- `each_item`: the run waits before each save until a person approves the
  filled form in OpenAdapt Desktop. This is what `openadapt flow run` uses
  unless another mode is set.
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
