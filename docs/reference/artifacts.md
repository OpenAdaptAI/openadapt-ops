---
description: >-
  What each folder and file OpenAdapt writes holds, which ones contain
  protected data, and which ones are safe to share.
---

# Files and evidence

OpenAdapt writes everything to folders on the computer that runs it. This
page lists what each folder holds and whether it can contain protected data,
such as patient details.

| Folder or file | Written by | Holds | Protected data? |
|---|---|---|---|
| Recording (`rec/`) | `record`, `demo-record` | `events.jsonl` (each step and who did it), `meta.json`, screenshots in `frames/` | Yes. Screenshots and typed values. Passwords and secret fields are never saved. |
| Bundle (`bundle/`) | `compile`, `induce`, `for-each`, `compose` | `workflow.json` or `workflow.json.enc`, target crops under `templates/`, and a manifest with a digest of every file | Yes. Crops and recorded default values. |
| Run directory (`runs/<run>/`) | `run`, `replay`, `resume` | `report.json`, `REPORT.md`, step screenshots, `checkpoints/` for durable runs, `pending_escalation.json` when paused | Yes. `report.json` keeps literal identifiers on purpose, as the audit trail. |
| `receipt.json`, `receipt.card.json`, `receipt.private.json` | Every run | The signed receipt, its public version, and the salts and values behind its commitments | `receipt.private.json` does. The other two hold counts, digests, and commitments only. |
| Qualification folder | `qualify` | Per-trial run reports, `qualification/result.json`, `QUALIFICATION.md` | Yes, when run against real records. |

Treat recordings, bundles, and run directories as protected data and limit
who can read them. Use `openadapt flow sanitize` to make a redacted copy
before anything leaves your boundary.

## The run report

`report.json` records, for every step: what it acted on, how it found the
target, every check and its result, and timing. For the whole run it records
the profile, approval mode, `execution_outcome`, `transaction_outcome`, the
number of model calls, and whether screenshots could have left the computer.
`REPORT.md` is the same information to read. `openadapt flow explain` turns
it into a short account with the next command to run.

<span id="the-receipt-and-the-seal"></span>

## The receipt

A run writes a receipt: a signed, itemized record of what it changed, how
each change was checked, and who signed it. It holds counts, digests, and
versions, no record values. A run tracked by Cloud Execute can also carry
Cloud's countersignature. The receipt is `receipt.json`, its private
openings are `receipt.private.json`, and its public version is
`receipt.card.json`. The run summary that older releases wrote as
`receipt.json` (schema `openadapt.run-receipt/v2`) is now
`run-summary.json`. Older Seal files (`seal.json`, `public-seal.json`) still
verify. See [Receipts](receipts.md).

