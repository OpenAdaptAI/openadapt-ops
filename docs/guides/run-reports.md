# Read and audit run reports

Every replay writes a run directory. The report inside it is the audit trail: per
step, exactly what happened and why. This guide explains how to read one and what
to check when auditing a run.

## Where the report lives

Each replay writes a timestamped directory under `runs/` (override with
`--run-dir`). It contains:

- `REPORT.md`: the illustrated, human-readable report; review or sanitize it
  before sharing.
- `report.json`: the machine-readable version, for programmatic auditing.

The final console line names the report path and its precise execution outcome.

## Read the final outcome first

Flow 1.26 records one closed execution outcome in `report.json` and in the
human-readable report:

| Outcome | Meaning |
|---|---|
| `VERIFIED` | Every contract required by the selected profile passed. This is the only production success. |
| `COMPLETED_UNVERIFIED` | Execution finished, but the evidence did not prove the complete contract. Standard and Regulated execution treat this as non-success. |
| `HALTED` | A policy, identity, state, target, postcondition, or effect gate refused to continue. |
| `FAILED` | An infrastructure or runtime failure stopped the run. |
| `ROLLED_BACK` | A configured compensating action completed and its result was verified. This remains a non-success. |

The outcome envelope also records which contracts were required and passed,
the evidence classes that support the result, model-call count, external-network
call state, and compensation count. Do not infer success from the legacy
`success` boolean when this envelope is present.

For a stopped consequential run, read `transaction_outcome` before deciding
what to do next. `HALTED_BEFORE_EFFECT` requires positive evidence that the
effect is absent. `RECONCILIATION_REQUIRED` means delivery or persistence can
be uncertain, conflicting, or unverifiable. Reconcile the current business
state before a retry. An empty evidence list does not prove that no write
occurred.

## What the report tells you, per step

For each step, the report records:

- **Resolution**: which rung of the [resolution ladder](../concepts/self-healing.md)
  resolved the target (template, global template, OCR, geometry, or a grounding
  model), and whether a heal was applied.
- **Identity**: whether the step was identity armed, and what the pre-click check
  verified or refused. Unreadable bands are flagged (`identity: "unreadable"`),
  not hidden.
- **Postconditions**: which assertions passed, and any [effect](../concepts/effect-verification.md)
  verified against the system of record, with its verdict.
- **Model calls**: any call to a grounding or state-verification model, so the $0
  property is observable, not assumed.
- **Outcome**: the precise execution outcome, its required and passed
  contracts, and a halt or reconciliation reason when applicable.

## The identity-coverage line

Every report states how many click steps were identity armed (for example "4 of
12 click steps identity-armed") and lists the unarmed steps by id with the reason
each was not armed. This is the same [coverage metric](../concepts/identity-gate.md)
that `workflow.json` carries before the run, so you can audit it ahead of time and
confirm it afterward.

## An audit checklist

When auditing a consequential run, check:

1. **Is the final outcome `VERIFIED`?** Standard and Regulated runs have no
   other successful outcome. If reconciliation is required, inspect the
   current business state before any retry.
2. **Did every write verify an effect?** A write with only a screen
   postcondition is exactly as silent as the [five transactional
   faults](../concepts/effect-verification.md). Confirm the effect verdict is
   CONFIRMED, not just a passing screen check.
3. **Were consequential clicks identity armed?** Cross-check the
   identity-coverage line against the steps that navigate to or write a record.
4. **Did anything heal?** A heal means the UI drifted. Review the diff and
   confirm the healed target is correct before promoting the healed bundle.
5. **Were there model calls?** On a healthy deterministic run there should be
   none. Any call is recorded; understand why it happened.
6. **Read the halt.** The report names the violated expectation. A halt is not
   terminal: demonstrate the fix once and
   [`openadapt flow teach`](../reference/cli.md#teach) compiles it back into the
   workflow through the governed induction path, so it stops halting on that
   situation. See [The halt-learn loop](../concepts/halt-learn-loop.md).

## Scrubbing shared reports

Before sharing `REPORT.md` outside the environment, scrub it. With the `privacy`
extra and `OPENADAPT_FLOW_SCRUB=on`, the sanitizer processes the report and logs
on the persist path, while the bundle and `report.json` keep literal identifiers
behind a documented boundary. Sanitizer success is not proof that detectors found
every identifier; review the result before egress. See
[Deploy on-prem](deploy-on-prem.md).
