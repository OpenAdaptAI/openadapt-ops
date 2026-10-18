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
| `receipt.json` and `receipt.png` | A `VERIFIED` run | A summary safe to share | No. Counts and digests only. |
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

## The receipt and the Seal

A `VERIFIED` run writes `receipt.json` (schema `openadapt.run-receipt/v2`)
and `receipt.png`: counts, digests, and versions, no record values. A run
tracked by Cloud Execute can also carry Cloud's signature on it, the Seal, in
`report.json` as `execute_receipt`. See
[Receipts, Seals, and countersigning](receipts-and-seals.md).

