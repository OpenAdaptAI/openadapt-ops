# Run outcomes and halt reasons

Every run terminates in exactly one **execution outcome**, refined by a
**transaction outcome** that states what is known about the business effect.
This page is the single reference for every terminal state a run report or the
hosted Execute API can show, what each one means, and what to do next.

All values below are read from the engine's typed report models
(`execution_outcome`, `transaction_outcome`, and the effect-verification
evidence in `report.json`) and, for the hosted lifecycle, from the published
Execute status contract.

## Execution outcomes

The coarse, evidence-qualified result in `report.json`
(`execution_outcome`) and on the final console line.

| Outcome | Meaning | What to do next |
|---|---|---|
| `VERIFIED` | Execution completed **and** every declared contract passed: governed authorization, identity coverage, postconditions, and every effect confirmed at or above the required tier. Only possible under the Standard or Regulated profile. The only production success. | Nothing. Archive the run directory; the report and receipt are the audit evidence. |
| `COMPLETED_UNVERIFIED` | Execution reached the end, but the run lacked the evidence to claim `VERIFIED` (typically a Demo-profile replay with no independent effect verifier). Never billable, never a production success. | Fine for development. For production, wire an effect verifier and run under the Standard or Regulated profile so the same workflow can terminate `VERIFIED`. See [Run a deployment](../guides/run-a-deployment.md). |
| `HALTED` | The runtime **refused to act** on a governed check: identity, postcondition, effect verdict, an unhandled state, or a policy gate. A halt is a governed stop, not a crash. | Read the halt reason in `REPORT.md` (categories below). Usually: [`teach`](cli.md#teach) the correction, or fix the target/parameters and re-run. Do not blind-retry a run whose transaction outcome is `RECONCILIATION_REQUIRED`. |
| `FAILED` | A non-governed runtime failure (for example the browser or agent connection died) rather than a safety refusal. | Check the environment (target reachable, backend agent up, permissions), then re-run. If the transaction outcome is `FAILED_PLATFORM`, no business effect occurred. |
| `ROLLED_BACK` | A detected duplicate or collateral write was **compensated** and the compensation was re-verified. Non-success, but the system of record was restored. | Review the compensation entries in the effect journal, confirm the record state, then address the root cause before re-running. |

## Transaction outcomes

`transaction_outcome` refines the execution outcome: it states what the
evidence proves about the **business effect** when a run stops.

| Outcome | Meaning | What to do next |
|---|---|---|
| `VERIFIED` | Every declared effect passed at or above the required tier under a production profile. | Nothing; this is the billable success. |
| `HALTED_BEFORE_EFFECT` | The run stopped and the evidence proves **no consequential write landed**: every consequential step was verified absent or stopped before delivery was attempted. | Safe to fix and re-run. This is the evidenced version of "nothing happened". |
| `RECONCILIATION_REQUIRED` | Delivery or persistence is **uncertain, conflicting, or unverifiable**. A write may have half-landed. | Do **not** re-run yet. Reconcile against the independent system of record first (find or rule out the record), then re-run. The per-step effect journal in the report shows which step is uncertain. |
| `FAILED_PLATFORM` | An OpenAdapt/platform failure before any possible business effect. Never billable. | Re-run after the platform issue is resolved; report persistent cases. |
| `CANCELED` | The run was canceled before any business effect could occur. | Re-run when ready. |
| `REJECTED_POLICY` | Authorization, identity coverage, qualification, or environment gates refused execution **before** any business effect. | Fix the gate: certify the bundle, supply the required authorization, or adjust the [deployment configuration](deployment-config.md). |
| `COMPLETED_UNVERIFIED` | Demo-only completion with no production-grade effect evidence. | Same as the execution outcome above: acceptable in development only. |
| `ROLLED_BACK` | A duplicate/collateral write was compensated and re-verified. | Review the compensation evidence, then address the root cause. |

## Effect-verifier verdicts

Each declared effect on a consequential step gets an independent read of the
system of record, recorded per effect in the report's evidence:

| Verdict | Meaning | What to do next |
|---|---|---|
| `confirmed` | The verifier independently observed the intended effect in the system of record. | Nothing; this is what `VERIFIED` is built from. |
| `refuted` | The verifier affirmatively observed the effect is **absent** (or wrong). The run halts. | The write did not land as intended. If the observed effect is `absent`, the run maps to `HALTED_BEFORE_EFFECT` and is safe to re-run after fixing the cause; if `conflicting`, reconcile the duplicate/wrong record first. |
| `indeterminate` | The verifier could not establish presence or absence (unreachable, ambiguous read). The run halts; an unreachable verifier is **never** treated as success. | Check verifier connectivity and configuration (`--effects-kind`, `--effects-base-url`). Treat the write as uncertain: reconcile before re-running. |

The evidence also records what the verifier **observed** about the record,
independent of the verdict: `present`, `absent`, `conflicting` (a record was
written but is a duplicate or wrong value), or `unknown` (fail-safe default;
absence cannot be claimed).

## Halt reasons and remediation

When a run reports `HALTED`, `REPORT.md` names the violated expectation and
`report.json` carries a typed refusal code. The categories:

| Halt reason (code) | Stage | What happened | Remediation |
|---|---|---|---|
| `target_ambiguous` | target resolution | More than one (or zero) candidate matched the step's recorded evidence; acting would be a guess. | Re-record the step with cleaner evidence, or [`teach`](cli.md#teach) the disambiguation. Prefer a structural backend (DOM / UIA / AX / AT-SPI) over pixels where the app exposes one. |
| `identity_conflict` | identity verification | The pre-click identity check read a **different record identifier** than the run's parameters expect (the wrong-record gate firing). | First verify the parameters or worklist row are correct. If the UI legitimately changed, `teach` the correction. Do not lower the gate: see [Troubleshooting](../guides/troubleshooting.md#it-halts-too-much-over-halting-on-citrix-pixel-only). |
| `identity_unverifiable` | identity verification | The identity band could not be read confidently (common on pixel-only substrates where OCR meets confusable glyphs). | Raise substrate fidelity (structural backend), re-capture the identifier crop, or `teach` the specific case. Over-halting beats a silent wrong write. |
| `actuation_observation_changed` | actuation revalidation | The screen changed between resolving the target and acting on it; the runtime refused to click a stale observation. | Usually transient (a late toast or dialog): re-run. If it recurs at the same step, `teach` the interstitial state so the program handles it. |
| `api_path_unavailable` | API admission | A step bound to the API actuation tier could not use it. | Check `--api-base-url` / the deployment config's actuation section and the credentials it references. |
| `effect_strength_insufficient` | effect strength | The configured verifier cannot meet the minimum verification tier the policy or profile requires for this write. | Wire a stronger verifier in the [deployment configuration](deployment-config.md), or revisit the required tier in the policy (a deliberate governance decision, not a tweak). |
| `effect_verifier_missing` | effect verification | The step declares effects but no verifier is configured; the profile refuses to treat the write as verified. | Configure `--effects-kind` (`rest`, `fhir`, `document-hash`) or, in Demo development only, explicitly approve the unverified write. |

Beyond the typed refusal codes, a run also halts on an **unhandled state**: a
resolution failure, a dead-end branch, an unmet `halt` guard, a non-confirmed
effect, or an explicit `halt` terminal in the program. The report records where
it stopped, what unexpected on-screen state it observed, and the steps that
succeeded before it, which is exactly the evidence [`teach`](cli.md#teach) consumes.
See [The halt-learn loop](../concepts/halt-learn-loop.md).

`report.json` also carries a machine-readable `failure_category` per failed
step: `governed_refusal` and `safety_halt` (the gates above), `runtime_failure`
(a non-governed error), or `continuation_preempted` (a durable run superseded
this attempt).

## Hosted Execute lifecycle

The hosted [Execute API](../commercial/execute-api.md) reports a run through a
published status contract. Lifecycle states:

| State | Meaning | What to do next |
|---|---|---|
| `queued` | Accepted, not yet running. | Poll or wait for the webhook. |
| `running` | Executing under its governed profile. | Wait. |
| `decision_required` | The run paused for an attended human decision (a durable halt an operator can answer). | Answer the decision from the runner-local portal or the hosted lane; the engine re-verifies live state before continuing. See [Attend a paused run](../concepts/halt-learn-loop.md). |
| `waiting_for_reconciliation` | A consequential write is uncertain; the run waits for reconciliation against the system of record. | Reconcile; do not re-submit the same request without its idempotency key. |
| `terminal` | The run ended; `terminal_outcome` carries the result. | Read the outcome and evidence receipt. |

Terminal outcomes mirror the engine taxonomy in lowercase: `verified`,
`halted_before_effect`, `reconciliation_required`, `rejected_policy`,
`failed_platform`, and `rolled_back_verified`.

## CLI exit codes

| Command | Exit codes |
|---|---|
| [`replay`](cli.md#replay) | `0` success (`VERIFIED` under Standard/Regulated); `1` on a halt or failure. |
| [`run`](cli.md#run) | Same as `replay` once admitted; `2` when an admission gate (certification, policy, profile requirement) refuses the run before it starts. |
| [`tutorial`](../get-started/index.md) | `0` when `VERIFIED`; `1` on any other outcome; `2` when the tutorial is refused before running. |
| [`lint`](cli.md#lint) | `0` clean (or advice only); `1` once a finding reaches `error` severity (`--strict`: also on warnings). |
| [`certify`](cli.md#certify) | `0` pass; `2` when the bundle fails certification (the gate refusing an unsafe bundle). |
| [`teach`](cli.md#teach) | `0` correction promoted; `1` governed refusal (nothing written); `2` unusable inputs. |

A nonzero exit from `lint`, `certify`, or a halted `replay` is the safety
boundary doing its job. The run stopped instead of guessing. See the
per-reason remediation above before changing any gate.

## Still stuck?

- [Troubleshooting](../guides/troubleshooting.md) covers first-week symptoms.
- [Read and audit run reports](../guides/run-reports.md) explains the report.
- Ask on [Discord](https://discord.gg/yF527cQbDG) or open an issue on
  [GitHub](https://github.com/OpenAdaptAI).
