---
description: >-
  How OpenAdapt checks that an action took effect, how the four-level check
  ladder works across Standard and Regulated runs, and what the main branch
  enforces today.
---

# How a save is checked

A record check is how OpenAdapt checks its own work. After an action that
changes state (clicking a Save button, editing a grid cell in place, toggling a
setting, or submitting a step in a wizard), it reads the target state back and
compares the expected values. That catches a value in the wrong field, an entry
on the wrong record, a missed keystroke, a duplicate submit, or a step that ran
before the view settled. Not every UI has a Save button, a separate post-save
screen, or a safe page reload, so OpenAdapt grades checks on a four-level
ladder from a bounded check on the settled screen up to a direct read of the
system of record. Each check returns `confirmed`, `refuted`, or
`indeterminate`. Only `confirmed` at or above the run's required level ends
`VERIFIED`, and every report and receipt records `checked_how`.

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 390" role="img" aria-labelledby="oa-ver-title oa-ver-desc">
  <title id="oa-ver-title">How OpenAdapt checks an action at the commit boundary</title>
  <desc id="oa-ver-desc">On the acting surface, OpenAdapt first performs a right-record check and captures a baseline. If the wrong record or an unexpected screen appears, the run stops before acting with HALTED_BEFORE_EFFECT and nothing is written. Otherwise it performs the action, then checks the target state on a four-level ladder: Tier 1 system_of_record (REST, GraphQL, FHIR, SQL, file, email, or document store), Tier 2 separate_session (ui_readback or fresh_session, minimum floor for Regulated), Tier 3 reopened (idempotent fresh_reload or demonstrated reopen), or Tier 4 same_screen (bounded check on the settled screen, eligible for VERIFIED under Standard). Every report and receipt records checked_how and effect_assurance. If the check matches at or above the required floor, the run ends VERIFIED with a signed Ed25519 receipt (OpenAdapt Cloud countersigns only after a Tier 1 system_of_record read). If the check disagrees or cannot tell, the run ends RECONCILIATION_REQUIRED and the ledger blocks blind retries until a person checks the record.</desc>
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

  <!-- Step 2: Apply change -->
  <g class="oa-svg-node">
    <rect x="192" y="62" width="128" height="118" rx="10" class="oa-svg-panel"/>
    <text x="204" y="84" font-size="10" class="oa-svg-accent">2 · ACTION</text>
    <text x="204" y="105" font-size="13" class="oa-svg-title">Enter or</text>
    <text x="204" y="122" font-size="13" class="oa-svg-title">apply</text>
    <text x="204" y="144" font-size="10.5" class="oa-svg-muted">Form, in-place edit,</text>
    <text x="204" y="160" font-size="10.5" class="oa-svg-muted">or wrapped agent</text>
  </g>

  <text x="30" y="216" font-size="11" class="oa-svg-muted">Every report and receipt stamps checked_how.</text>
  <text x="30" y="234" font-size="10.5" class="oa-svg-mono">approval-gated by profile</text>

  <!-- Split from Action to Read-back tiers -->
  <path d="M320,104 C354,104 352,72 384,72" class="oa-svg-line-verified oa-svg-flow" marker-end="url(#ver-arr-v)"/>
  <path d="M320,138 C354,138 352,196 384,196" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#ver-arr)"/>

  <!-- Step 3: Tier 1 System-of-Record Read-Back -->
  <g class="oa-svg-node">
    <rect x="390" y="16" width="276" height="114" rx="12" class="oa-svg-panel-verified"/>
    <circle cx="648" cy="36" r="4.5" class="oa-svg-gate-dot oa-svg-gate-dot--verified"/>
    <text x="406" y="40" font-size="10" class="oa-svg-verified-txt">3A · TIER 1 SYSTEM OF RECORD</text>
    <text x="406" y="62" font-size="14" class="oa-svg-title">System-of-record read-back</text>
    <text x="406" y="83" font-size="11.5" class="oa-svg-muted">API (REST, GraphQL, FHIR), SQL,</text>
    <text x="406" y="100" font-size="11.5" class="oa-svg-muted">file, email, or document store</text>
    <text x="406" y="118" font-size="10" class="oa-svg-mono">system_of_record · independent_readback</text>
  </g>

  <!-- Step 3: Tiers 2-4 UI & On-Screen Ladder -->
  <g class="oa-svg-node">
    <rect x="390" y="144" width="276" height="108" rx="12" class="oa-svg-panel"/>
    <text x="406" y="168" font-size="10" class="oa-svg-accent">3B · TIERS 2 TO 4 UI &amp; SCREEN</text>
    <text x="406" y="190" font-size="14" class="oa-svg-title">Session, reopen, or settled view</text>
    <text x="406" y="211" font-size="11" class="oa-svg-muted">separate_session (T2) · reopened (T3)</text>
    <text x="406" y="229" font-size="11" class="oa-svg-muted">same_screen bounded check (T4)</text>
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
    <text x="756" y="85" font-size="11" class="oa-svg-muted">Meets profile + minimum_readback</text>
    <text x="756" y="102" font-size="11" class="oa-svg-muted">Cloud countersigns Tier 1 only</text>
    <text x="756" y="119" font-size="10" class="oa-svg-mono">receipt.json · checked_how</text>
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
    <text x="32" y="352" font-size="12" class="oa-svg-muted">Stops before acting and asks a person. Nothing was written, so the item is safe to fix and re-run.</text>
  </g>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Commit-boundary verification:</strong> Pre-action identity prevents wrong-record writes; graded outcome checks confirm the target state and record <code>checked_how</code>; uncertainty stops without blind retry.</span>
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

OpenAdapt ranks every check on one ladder by how independent it is of the
surface that performed the action. The Flow tier numbers run 1 (strongest) to
4; the run report and MCP result carry the `checked_how` code and its label;
the receipt records `effect_tier_reached` and `effect_assurance`; and Cloud's
countersignature uses its own check level:

| `checked_how` (label) | What it checks | How you set it up | Flow tier | Grade (`effect_assurance`) | Ends `VERIFIED` | Certifies through `qualify` | Cloud check level |
|---|---|---|---|---|---|---|---|
| `system_of_record` ("Checked in your system's records") | The system of record, through its API, database, FHIR, GraphQL, file, email, or document store | `effects.kind` `rest`, `graphql`, `fhir`, `sql`, `file`, `document`, `email`, or `document-hash` | 1, `independent_system` | `independent_readback` | Yes (`Standard` and `Regulated`) | Yes | 2 |
| `separate_session` ("Checked in a separate session") | The app's view in a separate, freshly signed-in, read-only browser or app session | `effects.kind: ui_readback` or `fresh_session` | 2, `independent_session` | `screen_readback` | Yes (`Standard`, and `Regulated` unless policy requires Tier 1) | No | 1 |
| `reopened` ("Reopened in the same session") | Same-session state reset, refresh, or reopen when the UI supports idempotent re-reading | `fresh_reload` or demonstrated reopen; see [Reload or reopen in the same session](../how-to/record-checks.md#reload-the-record-page-in-the-same-session) | 3, `persisted_state_reacquisition` | `fresh_reload` or `screen_readback` | Yes under `Standard`; `COMPLETED_UNVERIFIED` under `Regulated` | No | 0 |
| `same_screen` ("Checked on the screen") | A bounded region or element on the current screen after the action settles | `effects.kind: onscreen` or auto-derived `same_screen` | 4, `immediate_screen` | `screen_readback` | Yes under `Standard`; `COMPLETED_UNVERIFIED` under `Regulated` | No | 0 |
| `unchecked` ("Not checked") | No check confirmed the action | | | `unchecked` | No | No | |

Different UIs call for different rungs on this ladder:

- **In-place edits, non-idempotent flows, and closed apps (`same_screen`, Tier 4).**
  Many applications have no separate post-save page or Save button (spreadsheet
  and grid cell edits, auto-saving fields, toggles, `Apply` or `Ctrl+S` dialogs
  that stay on the same view, or queue items that leave a list), and many web
  portals use non-idempotent `POST` flows or multi-step wizards where reloading
  would re-submit or break session state. Bounded `same_screen` verification is
  default-eligible out of the box when a target region stabilizes with the
  expected state after the action, reaches `VERIFIED` under `Standard`, and
  stamps `checked_how: "same_screen"` and `effect_assurance: "screen_readback"`
  on the report and receipt.
- **Idempotent web pages and reopenable views (`reopened`, Tier 3).** When
  reloading a URL or closing and reopening a record is safe and idempotent,
  `fresh_reload` or a demonstrated reopen check resets client-side form state
  and re-reads the record in the same session without a second account or API
  token.
- **Separate sessions and direct backend reads (`separate_session` Tier 2, `system_of_record` Tier 1).**
  Configure `ui_readback` when you want an isolated read-only session, or an
  API, database, FHIR, or file verifier when the system exposes one. Cloud check
  level 3 (`counterparty_confirmed`) is a counterparty artifact, such as a
  payer status, which Flow doesn't read directly.

A workflow can set `minimum_readback` to `"same_screen"`, `"reopened"`,
`"separate_session"`, or `"system_of_record"` to enforce a stricter floor than
the profile's default. When a run has multiple writes, its report and receipt
record the weakest level reached across all of them (`checked_how`,
`effect_tier_reached`, and `effect_assurance`). See
[Receipts](../reference/receipts.md).

## What each result needs

**`VERIFIED` under Standard.** Every declared change must be confirmed on the
ladder (Tier 4 `same_screen` through Tier 1 `system_of_record`), at or above
any `minimum_readback` the workflow sets. Every report and receipt states
`checked_how` (`same_screen`, `reopened`, `separate_session`, or
`system_of_record`) so reviewers and calling agents see the exact check level.

**`VERIFIED` under Regulated.** Every declared change must be confirmed at
Tier 2 (`separate_session`) or Tier 1 (`system_of_record`), outside the session
that performed the action. The `regulated` policy pack raises that floor to
Tier 1 (`system_of_record`). A run whose saves were confirmed only at
`reopened` or `same_screen` (or below the workflow's `minimum_readback`) ends
`COMPLETED_UNVERIFIED` with `below_minimum: true` in `report.json`, never
`VERIFIED`.

**Certification through qualification.** To certify through `qualify`, the
normal case must be confirmed and every fault case must show nothing landed,
all at Tier 1 (`system_of_record` / `independent_readback`). A workflow
checked only through UI or screen levels can run cases where supported, though
it cannot be certified through `qualify`.

**Cloud's countersignature.** OpenAdapt Cloud countersigns a receipt only
when the run was confirmed by a Tier 1 `system_of_record` read.

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
read can see, so it should cover every table a save can change. These were faults we wrote and injected into our own engine to test coverage
over a fixed list; they do not represent a real-world error rate.
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
