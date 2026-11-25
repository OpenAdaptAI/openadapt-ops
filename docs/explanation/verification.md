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

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 390" role="img" aria-labelledby="oa-ver-title oa-ver-desc">
  <title id="oa-ver-title">How OpenAdapt checks a save at the commit boundary</title>
  <desc id="oa-ver-desc">On the acting surface, OpenAdapt first performs a right-record check and captures a baseline. If the wrong record or an unexpected screen appears, the run stops before saving with HALTED_BEFORE_EFFECT and nothing is written. Otherwise it enters and saves, then reads the record back either independently from the system of record (Tier 1: REST, GraphQL, FHIR, SQL, or file export) or from a separate signed-in UI session (Tier 2: ui_readback). The acting screen alone never confirms a save. If the read matches, the run ends VERIFIED with a signed Ed25519 receipt (OpenAdapt Cloud countersigns only after a Tier 1 independent read). If the read disagrees or cannot tell, the run ends RECONCILIATION_REQUIRED and the ledger blocks blind retries until a person checks the record.</desc>
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

  <!-- Acting Surface container -->
  <rect x="14" y="16" width="320" height="236" rx="14" class="oa-svg-panel-link"/>
  <text x="30" y="42" font-size="10.5" class="oa-svg-accent">ACTING SURFACE · WEB, DESKTOP, RDP/CITRIX</text>

  <!-- Step 1: Right-record check -->
  <g class="oa-svg-node">
    <rect x="28" y="62" width="136" height="118" rx="10" class="oa-svg-panel"/>
    <text x="40" y="84" font-size="10" class="oa-svg-accent">1 · PRE-CHECK</text>
    <text x="40" y="105" font-size="13" class="oa-svg-title">Right-record</text>
    <text x="40" y="122" font-size="13" class="oa-svg-title">check</text>
    <text x="40" y="144" font-size="10.5" class="oa-svg-muted">Baseline + target</text>
    <text x="40" y="162" font-size="10" class="oa-svg-mono">begin_write()</text>
  </g>

  <path d="M164,121 L188,121" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#ver-arr)"/>

  <!-- Step 2: Enter and save -->
  <g class="oa-svg-node">
    <rect x="192" y="62" width="128" height="118" rx="10" class="oa-svg-panel"/>
    <text x="204" y="84" font-size="10" class="oa-svg-accent">2 · ACTION</text>
    <text x="204" y="105" font-size="13" class="oa-svg-title">Enter and</text>
    <text x="204" y="122" font-size="13" class="oa-svg-title">save</text>
    <text x="204" y="144" font-size="10.5" class="oa-svg-muted">Compiled step or</text>
    <text x="204" y="160" font-size="10.5" class="oa-svg-muted">wrapped agent</text>
  </g>

  <text x="30" y="216" font-size="11" class="oa-svg-muted">The acting screen alone never confirms a save.</text>
  <text x="30" y="234" font-size="10.5" class="oa-svg-mono">approval-gated by profile</text>

  <!-- Split from Action to Read-back tiers -->
  <path d="M320,104 C354,104 352,72 384,72" class="oa-svg-line-verified oa-svg-flow" marker-end="url(#ver-arr-v)"/>
  <path d="M320,138 C354,138 352,196 384,196" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#ver-arr)"/>

  <!-- Step 3: Tier 1 Independent Read-Back -->
  <g class="oa-svg-node">
    <rect x="390" y="16" width="276" height="114" rx="12" class="oa-svg-panel-verified"/>
    <circle cx="648" cy="36" r="4.5" class="oa-svg-gate-dot oa-svg-gate-dot--verified"/>
    <text x="406" y="40" font-size="10" class="oa-svg-verified-txt">3A · TIER 1 INDEPENDENT READ</text>
    <text x="406" y="62" font-size="14" class="oa-svg-title">System-of-record read-back</text>
    <text x="406" y="83" font-size="11.5" class="oa-svg-muted">API (REST, GraphQL, FHIR), SQL,</text>
    <text x="406" y="100" font-size="11.5" class="oa-svg-muted">or file export; never through the UI</text>
    <text x="406" y="118" font-size="10" class="oa-svg-mono">independent_readback</text>
  </g>

  <!-- Step 3: Tier 2 Separate Session UI Read-Back -->
  <g class="oa-svg-node">
    <rect x="390" y="144" width="276" height="108" rx="12" class="oa-svg-panel"/>
    <text x="406" y="168" font-size="10" class="oa-svg-accent">3B · TIER 2 SEPARATE SESSION</text>
    <text x="406" y="190" font-size="14" class="oa-svg-title">Separate UI read-back</text>
    <text x="406" y="211" font-size="11.5" class="oa-svg-muted">Fresh read-only session (ui_readback)</text>
    <text x="406" y="229" font-size="11" class="oa-svg-muted">Ends VERIFIED outside regulated policy</text>
  </g>

  <!-- Connectors to Outcomes -->
  <path d="M666,68 C702,68 702,66 734,66" class="oa-svg-line-verified oa-svg-flow" marker-end="url(#ver-arr-v)"/>
  <path d="M666,196 C702,196 702,204 734,204" class="oa-svg-line-stopped oa-svg-flow-slow" marker-end="url(#ver-arr-s)"/>
  <text x="674" y="54" font-size="10.5" class="oa-svg-muted">matches</text>
  <text x="670" y="224" font-size="10.5" class="oa-svg-muted">mismatch /</text>
  <text x="670" y="238" font-size="10.5" class="oa-svg-muted">uncertain</text>

  <!-- Outcome 1: VERIFIED -->
  <g class="oa-svg-node">
    <rect x="740" y="16" width="226" height="114" rx="12" class="oa-svg-panel-verified"/>
    <circle cx="948" cy="36" r="4.5" class="oa-svg-gate-dot oa-svg-gate-dot--verified"/>
    <text x="756" y="42" font-size="12" class="oa-svg-verified-txt">VERIFIED</text>
    <text x="756" y="64" font-size="12" class="oa-svg-title">Signed Ed25519 receipt</text>
    <text x="756" y="85" font-size="11" class="oa-svg-muted">All declared effects confirmed</text>
    <text x="756" y="102" font-size="11" class="oa-svg-muted">Cloud countersigns Tier 1 only</text>
    <text x="756" y="119" font-size="10" class="oa-svg-mono">receipt.json · /r/&lt;id&gt;</text>
  </g>

  <!-- Outcome 2: RECONCILIATION_REQUIRED -->
  <g class="oa-svg-node">
    <rect x="740" y="146" width="226" height="106" rx="12" class="oa-svg-panel-reconcile"/>
    <circle cx="948" cy="166" r="4" class="oa-svg-gate-dot oa-svg-gate-dot--stopped"/>
    <text x="756" y="170" font-size="10.5" class="oa-svg-reconcile-txt">RECONCILIATION_REQUIRED</text>
    <text x="756" y="191" font-size="11.5" class="oa-svg-muted">Refuted or indeterminate:</text>
    <text x="756" y="208" font-size="11.5" class="oa-svg-muted">stop and ask a person</text>
    <text x="756" y="230" font-size="10" class="oa-svg-mono">ledger blocks blind retry</text>
  </g>

  <!-- Pre-save halt branch -->
  <path d="M96,180 L96,294" class="oa-svg-line-stopped oa-svg-flow-slow" marker-end="url(#ver-arr-s)"/>
  <text x="108" y="272" font-size="10.5" class="oa-svg-muted">wrong record or unexpected screen</text>

  <!-- Outcome 3: HALTED_BEFORE_EFFECT -->
  <g class="oa-svg-node">
    <rect x="14" y="300" width="952" height="72" rx="12" class="oa-svg-panel-stopped"/>
    <circle cx="948" cy="322" r="4" class="oa-svg-gate-dot oa-svg-gate-dot--stopped"/>
    <text x="32" y="328" font-size="12" class="oa-svg-stopped-txt">HALTED_BEFORE_EFFECT</text>
    <text x="32" y="352" font-size="12" class="oa-svg-muted">Stops before saving and asks a person. Nothing was written, so the item is safe to fix and re-run.</text>
  </g>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Commit-boundary verification:</strong> Pre-save identity prevents wrong-record writes; independent read-back confirms persistence; uncertainty stops without blind retry.</span>
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
