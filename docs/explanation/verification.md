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

![On the acting surface, the app screen OpenAdapt types into, a run checks that the right record is on screen, then enters and saves. It then reads the record back. A screen read-back uses the app's UI in a separate session and is not independent. An independent read uses the system of record through its API, database, or file export, never through the UI. If the read matches, the run ends VERIFIED with a run report and a receipt; OpenAdapt Cloud countersigns the receipt only after an independent read. If it doesn't match or can't tell, the run ends RECONCILIATION_REQUIRED and a person checks the record. If the right-record check fails, the run ends HALTED_BEFORE_EFFECT before saving and asks a person.](../assets/diagrams/record-check.svg)

## Commit-boundary verification

When an agent or compiled program crosses a commit boundary, OpenAdapt captures
a baseline before the write and compares the post-write read-back against it:

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 270" role="img" aria-labelledby="oa-ver-title oa-ver-desc">
  <title id="oa-ver-title">Commit-boundary verification flow</title>
  <desc id="oa-ver-desc">Before a consequential action, OpenAdapt captures a baseline and checks that the right record is on screen. After the save, it reads the record back either independently from the system of record (Tier 1: REST, GraphQL, FHIR, SQL, or file export) or from a separate signed-in UI session (Tier 2: ui_readback). Confirmed effects end VERIFIED with a signed receipt; refuted or indeterminate checks end RECONCILIATION_REQUIRED and the ledger blocks blind retries.</desc>
  <defs>
    <marker id="ver-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="ver-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
    <marker id="ver-arr-s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-stopped"/>
    </marker>
  </defs>

  <!-- Pre-state & Action -->
  <rect x="14" y="42" width="176" height="122" rx="12" class="oa-svg-panel-link"/>
  <text x="28" y="66" font-size="10" class="oa-svg-accent">BEFORE WRITE</text>
  <text x="28" y="88" font-size="14" class="oa-svg-title">Pre-state gate</text>
  <text x="28" y="108" font-size="11.5" class="oa-svg-muted">Baseline snapshot</text>
  <text x="28" y="125" font-size="11.5" class="oa-svg-muted">Right-record check</text>
  <text x="28" y="146" font-size="10.5" class="oa-svg-mono">begin_write()</text>

  <path d="M190,103 L222,103" class="oa-svg-line-accent" marker-end="url(#ver-arr)"/>

  <!-- Action / Save -->
  <rect x="228" y="42" width="148" height="122" rx="12" class="oa-svg-panel"/>
  <text x="242" y="66" font-size="10" class="oa-svg-accent">COMMIT BOUNDARY</text>
  <text x="242" y="88" font-size="14" class="oa-svg-title">Action and save</text>
  <text x="242" y="108" font-size="11.5" class="oa-svg-muted">Compiled step or</text>
  <text x="242" y="125" font-size="11.5" class="oa-svg-muted">external agent</text>
  <text x="242" y="146" font-size="10.5" class="oa-svg-mono">approval-gated</text>

  <!-- Split to read-back tiers -->
  <path d="M376,80 L402,80 L402,68 L428,68" class="oa-svg-line-verified" marker-end="url(#ver-arr-v)"/>
  <path d="M376,126 L402,126 L402,174 L428,174" class="oa-svg-line-accent" marker-end="url(#ver-arr)"/>

  <!-- Tier 1: Independent read-back -->
  <rect x="434" y="16" width="268" height="106" rx="12" class="oa-svg-panel-verified"/>
  <text x="450" y="39" font-size="10" class="oa-svg-verified-txt">TIER 1 · INDEPENDENT READ</text>
  <text x="450" y="60" font-size="14" class="oa-svg-title">System-of-record read-back</text>
  <text x="450" y="80" font-size="11.5" class="oa-svg-muted">REST, GraphQL, FHIR, SQL, or file export</text>
  <text x="450" y="97" font-size="11.5" class="oa-svg-muted">Qualifies, certifies, and backs Cloud Seal</text>

  <!-- Tier 2: Separate UI session -->
  <rect x="434" y="136" width="268" height="106" rx="12" class="oa-svg-panel"/>
  <text x="450" y="159" font-size="10" class="oa-svg-accent">TIER 2 · SEPARATE SESSION</text>
  <text x="450" y="180" font-size="14" class="oa-svg-title">Separate UI read-back</text>
  <text x="450" y="200" font-size="11.5" class="oa-svg-muted">Fresh read-only session (ui_readback)</text>
  <text x="450" y="217" font-size="11.5" class="oa-svg-muted">Ends VERIFIED outside regulated policy</text>

  <!-- Merge to outcomes -->
  <path d="M702,68 L748,68" class="oa-svg-line-verified" marker-end="url(#ver-arr-v)"/>
  <path d="M702,188 L748,188" class="oa-svg-line-stopped" marker-end="url(#ver-arr-s)"/>

  <!-- Outcome: Commit / VERIFIED -->
  <rect x="754" y="24" width="212" height="88" rx="12" class="oa-svg-panel-verified"/>
  <text x="770" y="49" font-size="12" class="oa-svg-verified-txt">VERIFIED</text>
  <text x="770" y="70" font-size="11.5" class="oa-svg-muted">All effects confirmed</text>
  <text x="770" y="88" font-size="11.5" class="oa-svg-muted">Emit signed receipt</text>

  <!-- Outcome: Pause / Reconcile -->
  <rect x="754" y="138" width="212" height="102" rx="12" class="oa-svg-panel-reconcile"/>
  <text x="770" y="162" font-size="10.5" class="oa-svg-reconcile-txt">RECONCILIATION_REQUIRED</text>
  <text x="770" y="183" font-size="11.5" class="oa-svg-muted">Refuted or indeterminate:</text>
  <text x="770" y="200" font-size="11.5" class="oa-svg-muted">stop and ask a person</text>
  <text x="770" y="220" font-size="10.5" class="oa-svg-mono">ledger blocks blind retry</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Read-back tiers:</strong> Tier 1 reads the system of record directly; Tier 2 reads a separate UI session. Unconfirmed writes stop for reconciliation.</span>
  <span><a href="../../reference/receipts/">Signed receipts &rarr;</a></span>
</figcaption>
</figure>

### Programmatic verification (`openadapt.verify`)

Any Python agent or automation script can use the same commit-boundary verifier
directly via `openadapt.verify` (backed by `openadapt_flow.verifier`) and its
uncertain-write ledger:

```python
from openadapt.verify import Contract, begin_write, verify_write
```

Each call returns a three-valued outcome (`CONFIRMED`, `REFUTED`, or
`UNCERTAIN`) and records uncertain writes in the local ledger so a retry cannot
silently duplicate a write.

## How strong a read-back is

OpenAdapt ranks every read-back by how independent it is of the screen that
did the work. The rank is the Flow tier, 1 the strongest. The run report and
the receipt also give each read a grade, and Cloud's countersignature names a check level.
This table maps the three:

<!-- The R0–R3 read-back ladder from the reopen read-back work goes here when
it ships: one more column naming each row's rung, and minimum_readback and
checked_how in "What each result needs". Until then, these are the tiers
Flow uses. -->

| Read-back | How you set it up | Flow tier | Grade | Ends `VERIFIED` | Certifies through qualification | Cloud check level |
|---|---|---|---|---|---|---|
| The system of record, through its API, database, or files | `effects.kind` `rest`, `graphql`, `fhir`, `sql`, `file`, `document`, `email`, or `document-hash` | 1, `independent_system` | `independent_readback` | Yes | Yes | 2 |
| The app's record page, in a separate, read-only, freshly signed-in session | `effects.kind: ui_readback` | 2, `independent_session` | `screen_readback` | Yes, except under the `regulated` policy | No | 1 |
| The acting session clears what the screen remembers, reopens the record, and reads it | A check shown by demonstration; see [Show how you'd check the save](../how-to/record-checks.md#show-how-youd-check-the-save) | 3, `persisted_state_reacquisition` | `screen_readback` | No | No | 0 |
| The screen that did the work still shows the value | `effects.kind: onscreen` | 4, `immediate_screen` | `screen_readback` | No | No | 0 |
| No read-back | | | `unchecked` | No | No | |

A tier-2 read is independent of the session that acted, but it still reads
the app's screens, so it can't tell a record the app stored from one it only
displays. Tiers 3 and 4 read the acting session's screen; they can stop a
run, but never make one `VERIFIED`. Cloud check level 3 is a counterparty
artifact, such as a payer status, which Flow doesn't read.

A run's receipt records the weakest read among its saves as
`effect_tier_reached` and its grade as `effect_assurance`. See
[Receipts](../reference/receipts.md).

## What each result needs

**`VERIFIED` under Standard or Regulated.** Every save must be confirmed at
tier 2 or stronger: the system of record, or a separate-session
`ui_readback`. The `regulated` policy pack raises that to tier 1. A
pixel-only Citrix save with no tier-1 or tier-2 read ends in a halt or
`RECONCILIATION_REQUIRED`, whatever an operator or the screen says.

**Certification through qualification.** To certify, the normal case must be
confirmed and every fault case must show nothing landed, all at
`independent_readback`. A workflow whose only read-back is `ui_readback` can
run the cases but can't be certified this way.

**Cloud's countersignature.** OpenAdapt Cloud countersigns a receipt only
when the run was confirmed by a system-of-record read.

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
- `problems_only`: only saves that fail a check go to a person. It turns on
  only after the workflow passes a readiness gate; until then, every save
  asks.
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
