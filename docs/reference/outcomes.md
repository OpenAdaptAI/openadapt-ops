---
description: >-
  Every result a run can end with, what each one means, what to do next, and
  how it appears to an agent and in exit codes.
---

# Run outcomes

Every run writes `report.json` and `REPORT.md` to its run directory. Two
fields in `report.json` say how it ended:

- `transaction_outcome` says what is known about the record. Base every
  decision to rerun on this field.
- `execution_outcome` is the shorter result printed on the last console line.

## Transaction outcomes

| Outcome | What it means | What to do next |
|---|---|---|
| `VERIFIED` | Every save was confirmed by a record check strong enough for the profile. Only possible under Standard or Regulated. | Nothing. Keep the run directory as evidence. |
| `HALTED_BEFORE_EFFECT` | The run stopped, and the evidence shows no save landed. | Fix the cause and run again. |
| `RECONCILIATION_REQUIRED` | A save may have landed, but it couldn't be confirmed or the evidence conflicts. | Don't run it again yet. A person checks the record first. |
| `REJECTED_POLICY` | A gate refused the run before any save: certification, admission, identity coverage, or environment. | Fix the gate, for example certify the bundle or supply the admission. |
| `CANCELED` | The run was canceled before any save. | Run again when ready. |
| `FAILED_PLATFORM` | OpenAdapt or the computer failed before any save could happen. | Fix the environment and run again. |
| `COMPLETED_UNVERIFIED` | A Demo run finished, but nothing confirmed the save. | Fine for testing. Not a production success. |
| `ROLLED_BACK` | A duplicate or extra write was undone, and the undo was confirmed. | Check the record, then fix the cause. |

## Execution outcomes

| Outcome | What it means |
|---|---|
| `VERIFIED` | Same as the transaction outcome. |
| `COMPLETED_UNVERIFIED` | The steps finished without the evidence to claim `VERIFIED`. |
| `HALTED` | A check refused to act. This is a designed stop, not a crash. |
| `FAILED` | Something outside the checks failed, such as a closed browser. |
| `ROLLED_BACK` | Same as the transaction outcome. |

## Record-check verdicts

Each record check on a save gets one verdict:

| Verdict | Meaning |
|---|---|
| `confirmed` | The check found the expected record. |
| `refuted` | The check found the record missing or wrong. The run stops. |
| `indeterminate` | The check couldn't tell, for example because the system was unreachable. The run stops; an unreachable check never counts as success. |

The report also records what the check saw: `present`, `absent`,
`conflicting` (a duplicate or a wrong value), or `unknown`.

## Why a run stopped

`REPORT.md` names the check that failed, and `report.json` carries a code:

| Code | What happened | What to do |
|---|---|---|
| `target_ambiguous` | More than one control, or none, matched the step. | Re-record the step or teach the fix. |
| `identity_conflict` | The screen showed a different record from the one the inputs name. | Check the inputs. If the screen changed, teach the fix. |
| `identity_unverifiable` | The record identifier couldn't be read with confidence. | Use a surface with structure where possible, or teach the case. |
| `actuation_observation_changed` | The screen changed between finding the target and acting. | Run again. If it recurs, teach the extra state. |
| `api_path_unavailable` | A step set to use the app's API couldn't reach it. | Check the API settings and credentials. |
| `effect_strength_insufficient` | The configured record check is weaker than the profile or policy requires. | Configure a stronger record check. |
| `effect_verifier_missing` | A save declares a record check, but none is configured. | Configure `effects:` in the deployment file. |

A run also stops on a screen it doesn't recognize. The report records where
it stopped, what it saw, and the steps that finished, which is what
[`teach`](../how-to/handle-a-halt.md#3-teach-the-program-the-fix) uses.

## What an agent sees

The MCP server reduces every result to four outcomes:

| Agent `outcome` | Comes from | `safe_to_retry` |
|---|---|---|
| `done` | `VERIFIED` | false; don't send again |
| `needs_review` | A run stopped before a save and waiting for a decision, or waiting for approval | false |
| `not_sure_if_saved` | `RECONCILIATION_REQUIRED`, a Demo completion, or a run that timed out after it started | false; a person checks the record |
| `did_not_run` | A refusal or failure before anything was written | true when fixing the cause and resending is safe |

## Exit codes

| Command | Exit codes |
|---|---|
| `run` | `0` when Standard or Regulated ends `VERIFIED`, or a Demo run finishes. `1` otherwise. `2` when refused before the first step. |
| `replay` | `0` when the steps finished. `1` on a stop or failure. |
| `lint` | `0` with no errors. `1` with an error, or with a warning under `--strict`. |
| `certify` | `0` on pass. `2` on failure. |
| `resume` | Same as `run`. `3` when the resume is refused, for example after a person declined the save. |

An exit code never says why a run stopped. Read `transaction_outcome`.
