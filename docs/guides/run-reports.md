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

The final console line names the report path and whether the run succeeded.

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
- **Outcome**: the exact terminal state and the violated expectation, when one
  exists. A transaction ends as `VERIFIED`, `HALTED_BEFORE_EFFECT`,
  `RECONCILIATION_REQUIRED`, `FAILED_PLATFORM`, `CANCELED`, `REJECTED_POLICY`,
  `COMPLETED_UNVERIFIED`, or `ROLLED_BACK`. Only `VERIFIED` is a successful
  production outcome. Every typed halt reason is defined in
  [Run outcomes and halt reasons](../reference/run-outcomes.md).

## The identity-coverage line

Every report states how many click steps were identity armed (for example "4 of
12 click steps identity-armed") and lists the unarmed steps by id with the reason
each was not armed. This is the same [coverage metric](../concepts/identity-gate.md)
that `workflow.json` carries before the run, so you can audit it ahead of time and
confirm it afterward.

## An audit checklist

When auditing a consequential run, check:

1. **Did every write verify an effect?** A write with only a screen
   postcondition is exactly as silent as the [five transactional
   faults](../concepts/effect-verification.md). Confirm the effect verdict is
   CONFIRMED, not just a passing screen check.
2. **Were consequential clicks identity armed?** Cross-check the
   identity-coverage line against the steps that navigate to or write a record.
3. **Did anything heal?** A heal means the UI drifted. Review the diff and
   confirm the healed target is correct before promoting the healed bundle.
4. **Were there model calls?** On a healthy deterministic run there should be
   none. Any call is recorded; understand why it happened.
5. **Read the halt.** The report names the violated expectation. A halt is not
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
