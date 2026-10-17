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

## The receipt

A `VERIFIED` run writes `receipt.json` (schema `openadapt.run-receipt/v2`)
and an image of it. From the quickstart:

```json
{
  "outcome": "VERIFIED",
  "transaction_outcome": "VERIFIED",
  "profile": "standard",
  "substrate": "web",
  "steps_ok": 6, "steps_total": 6,
  "identity_confirmed": 5, "identity_required": 5,
  "effects_confirmed": 2, "effects_required": 2,
  "effect_tier_reached": "independent_system",
  "model_calls": 0,
  "external_network_calls": "none",
  "bundle_digest": "d9b3102c…",
  "provenance": "synthetic-tutorial"
}
```

A stopped run gets no receipt, only its local report.

## The Seal

A Seal is OpenAdapt Cloud's Ed25519 signature on the receipt of a run that
Cloud Execute tracked. A run gets one when it ends `VERIFIED` with a record
check that read the system of record, and it was started with
`--cloud-execution-id` and `OPENADAPT_EXECUTE_API_KEY` set. Flow then fetches
the signed receipt into `report.json` as `execute_receipt`.
`openadapt flow attach-seal RUN_DIR --execution-id ID` does the same later.

To check a Seal offline, pin Cloud's public keys once, comparing the printed
fingerprint with the one OpenAdapt publishes:

```bash
openadapt seal keys pin
openadapt seal verify runs/<run>/report.json
```

`seal verify` also accepts a receipt file or a webhook body, and `--json`
prints the result as JSON. It never fetches keys while it checks.
