---
description: >-
  Review and sign off staged PrepareCard drafts across offices at
  app.openadapt.ai/prepare across four surfaces: Sign-Off Queue, Async Inbox
  and Routing, Reconciliation and Signed Receipts, and Trust and Progress.
---

# Multi-Office PREPARE Sign-Off Queue

The `PREPARE` console at
[app.openadapt.ai/prepare](https://app.openadapt.ai/prepare) is the web and
mobile Human-in-the-Loop workspace for reviewing staged claims, quotes, and
portal drafts across offices and portals. Operators clear exceptions in seconds
from one screen without sharing passwords or uploading patient health
information (PHI).

## Try the live preview

Open [app.openadapt.ai/prepare?demo=1](https://app.openadapt.ai/prepare?demo=1)
to inspect all four surfaces with sample cards and zero setup. Filter the queue
by office or portal using query parameters such as `?office=...` and
`?portal=...`.

## How Human-in-the-Loop works

Human involvement is bounded to three specific moments rather than continuous
supervision:

1. **One-time Shadow Capture:** An operator completes a portal workflow once
   while Chrome Co-Pilot records local evidence (`extension_evidence.jsonl`).
   `openadapt-kernel` induces a zero-PII `PortalPack` from that trace and
   qualifies it offline before it handles live work.
2. **Runtime `PrepareCard` micro-handoffs (5 to 15 seconds):** During live
   runs, OpenAdapt fills known fields and stops when it hits an unbound field,
   an ambiguous option, or a commit boundary. It emits a zero-PHI `PrepareCard`
   for human review. Each operator choice is learned back into the workflow's
   bindings, so repeat runs pause less often over time.
3. **Admin governance and zero-PHI egress audits:** Administrators inspect
   signed receipts, unresolved reconciliations, egress counters, and warm
   hit-rate trends across offices to verify that every write was authorized and
   no PHI left the workstation.

## The four surfaces in `app.openadapt.ai/prepare`

Both the desktop web app and mobile web layout organize operator and admin work
into four dedicated surfaces.

### 1. Sign-Off Queue

The primary review workspace for clearing pending `PrepareCard` items one at a
time:

- **Pause Reason Banner:** Explains why the run stopped (for example, an
  unmatched dropdown value, a missing variable binding, or a required final
  commit check).
- **Side-by-Side Evidence Strip:** Shows the target portal control metadata
  alongside the proposed `$var` or enum binding so the reviewer can compare
  source and target without opening the underlying portal tab.
- **Forced-choice controls:** Presents typed inputs, option pills, or structured
  prose choices for each unresolved field. The **Approve & Sign Off** action
  stays disabled until every highlighted field has an explicit selection.
- **One-click Reject reasons:** Lets operators reject a card with a structured
  reason code (such as wrong portal account, stale record, or mismatched code)
  instead of free-text triage.
- **Post-submit verification:** Tracks the downstream commit and read-back
  check after sign-off, displaying whether the save was verified or needs
  follow-up.

### 2. Async Inbox and Routing

The multi-office dispatch view for routing paused runs to the right person:

- **Filters:** Slice pending cards by **Office**, **Portal**, **Pause Type**,
  and **Role** (such as billing specialist, office manager, or admin).
- **Live vs. Parked resume state:** Distinguishes **Live** runs (where the
  local browser or desktop runner is actively waiting and resumes immediately
  after sign-off) from **Parked** runs (where the session has been suspended
  and will pick up the signed decision on the next scheduled or operator-driven
  resume).

### 3. Reconciliation and Signed Receipts

The audit and recovery view for runs that crossed a commit boundary:

- **`SUBMITTED_PENDING_RECONCILIATION` tracking:** Lists any run where a
  commit action fired but post-submit read-back could not yet confirm the
  saved record. Operators can inspect the last verified state, attach
  confirmation from the portal, and close out the reconciliation without
  re-running a duplicate submission.
- **One-click receipt verification:** Checks the cryptographic signature and
  payload digest of any completed run receipt directly in the console, matching
  the offline check in [Check a receipt online](verify-a-receipt.md).

### 4. Trust and Progress

The governance and operational health view for practice leaders and security
reviewers:

- **Zero-PHI Egress Monitor:** Displays live egress accounting proving `0 B`
  of PHI left the local environment, alongside counts of blocked or masked
  fields rejected before entering the queue.
- **SHA-256 hash chain:** Shows the tamper-evident chain of canonical decision
  digests linking each operator sign-off to its downstream execution receipt.
- **Warm hit-rate progress:** Tracks the share of fields and runs resolved
  automatically by prior operator bindings versus those still requiring a
  `PrepareCard` pause, showing how the micro-handoff volume drops over time.

## How Chrome Extension, Cloud Web/Mobile, and Desktop divide the work

All three clients read and write the same `PrepareCard` and signed-decision
data contract. Each client focuses on the form factor where it works best:

| Client | Form factor | Primary responsibility |
|---|---|---|
| **Chrome Co-Pilot extension** | Inline single-tab side panel in Chrome | Runs inside your signed-in browser session, records Shadow Capture traces, fills fields locally, and handles single-tab inline pauses while keeping PHI and credentials in Chrome. |
| **Cloud Web and Mobile (`app.openadapt.ai/prepare`)** | Desktop web and mobile web console | Provides the full four-surface cockpit: batch multi-office Sign-Off Queue, Async Inbox and Routing across roles, Reconciliation and Signed Receipts, and Trust and Progress governance. Receives only zero-PHI card metadata. |
| **Desktop app (`openadapt-desktop`)** | Local workstation client (macOS and Windows) | Captures local Win32 and Citrix window crops, hosts the local verifier and Native Messaging bridge, and executes local desktop steps when a workflow spans native practice management software (PMS) and web portals. |

Because the data contract is symmetrical, a run paused in Chrome Co-Pilot or on
a Windows desktop workstation can be reviewed and signed off from the Cloud Web
console or a mobile phone, and the signed decision flows back to the local
runner for verified execution.

## Keyboard shortcuts

Every card in the Sign-Off Queue can be cleared without leaving the keyboard:

| Key | Action |
|---|---|
| `1` to `9` | Select an option for the active highlighted field and advance to the next unresolved field |
| `A` | Approve and sign off the card (enabled only after every unresolved field is bound) |
| `R` | Reject the card |
| `S` | Skip the card and move it to the back of the pending queue |

## Safety invariants

- **Anti-rubber-stamping:** Bulk approval (`approve_all: true`) is rejected
  whenever a card has unresolved fields. Each highlighted field requires an
  explicit forced-choice binding to a declared `$var` or an allowed enum option
  before **Approve & Sign Off** becomes active.
- **Zero-PHI previews:** Cards and resolutions contain only variable
  references (`$var`), enum options, control labels, selectors, and masked
  suffixes. Raw Social Security numbers, phone numbers, and email addresses are
  rejected before a card can enter the queue.
- **SHA-256 signed decisions:** Every approve or reject decision produces a
  deterministic SHA-256 digest over the canonical resolution payload. The
  digest is recorded in the queue's audit trail so downstream runners can
  verify what the operator signed off before committing.

## Related guides

- [openadapt-kernel](../guides/openadapt-kernel.md): generate `PrepareCard`
  drafts in Stage-Only mode.
- [Chrome Co-Pilot extension](../guides/chrome-copilot.md): stage form drafts
  inside your signed-in Chrome session.
- [Answer a halt from a phone](../how-to/answer-from-a-phone.md): review and
  sign off paused runs on mobile.
- [Check a receipt online](verify-a-receipt.md): verify signed run receipts.
- [Review a repair](review-a-repair.md): approve or reject proposed workflow
  repairs in OpenAdapt Cloud.
