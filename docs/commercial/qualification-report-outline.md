# Qualification report outline

The structure of the report delivered at the end of a
[Qualification Sprint](qualification-sprint.md). This page defines the sections
and fields; it is deliberately an outline, not a filled sample, because a
qualification report is only meaningful for the exact workflow, application,
environment, and bundle it names. Field semantics follow the engine's run
report schema (`REPORT.md` and `report.json`, see
[run reports](../guides/run-reports.md)) and the published benchmark report
conventions in
[openadapt-flow](https://github.com/OpenAdaptAI/openadapt-flow) (for example
`benchmark/*/results.json`).

## 1. Identification and provenance

| Field | Definition |
|---|---|
| Workflow name and version | The named workflow and its qualified revision. |
| Application and version | Exact application, version or tenant, and release channel. |
| Substrate | Browser, Windows UIA, macOS, Linux, RDP, or Citrix, with client and transport details for remote scopes. |
| Environment | The exact environment qualified (test tenant, VM snapshot, session broker); evidence never generalizes past it. |
| Engine versions | `openadapt-flow` and related package versions used. |
| Bundle digest | SHA-256 of the sealed bundle the evidence binds to. Evidence for one digest does not transfer to a modified bundle. |
| Report hashes | Digests of the evidence artifacts, so the pack is tamper-evident. |

## 2. Decision

| Field | Definition |
|---|---|
| Recommendation | Go, no-go, or go-with-conditions. |
| Basis | The specific results that determine the recommendation. |
| Boundary | The exact scope within which the recommendation holds. |
| Conditions | For conditional go: what must change or be accepted, by whom. |
| Requalification triggers | Events that void the qualification (application upgrade, layout change past healing coverage, verifier change, environment change). |

## 3. Workflow and risk inventory

| Field | Definition |
|---|---|
| Step inventory | Every compiled step with its action type. |
| Risk classification | Which steps are consequential (writes, submissions, deletions, payments) and why. Ambiguous classifications are resolved with the customer during the sprint, not assumed. |
| Parameters and secrets | Inputs the workflow takes; secrets are referenced by name and never stored in artifacts. |
| Exclusions | Paths, cases, and variants explicitly out of qualified scope. |

## 4. Coverage matrix

Delivered as its own artifact and summarized here. For each step:

| Field | Definition |
|---|---|
| Identity armed | Whether a pre-action identity check guards the step, and what evidence it compares ([identity gate](../concepts/identity-gate.md)). |
| Identity coverage line | "N of M consequential steps identity-armed", with each unarmed step listed by id and reason. |
| Effect contract | For each write: the declared effect (`record_written`, `field_equals`), its selector, and idempotency handling. |
| Verification strength | The strongest available oracle for the effect: independent system interface, independent read-only session, persisted-state reacquisition, or immediate screen confirmation. Screen-only confirmation is labeled as such, never presented as an independent system-of-record check. |
| Gaps | Every step or write without coverage, and whether policy permits it at this risk class. |

## 5. Representative case results

| Field | Definition |
|---|---|
| Case inventory | The representative cases selected with the workflow owner. |
| Trials per case | Count of repeated trials (minimum three per counted case). |
| Outcomes | Per trial: verified success, halt (with the violated expectation), or failure, per the run report's outcome field. |
| Effect verdicts | CONFIRMED / REFUTED / INDETERMINATE per declared effect ([effect verification](../concepts/effect-verification.md)). |
| Model calls | Count per run; healthy deterministic replay is expected to record zero. |
| Latency | Wall-clock per run where relevant to the ROI model. |

## 6. Fault campaign results

The seeded-fault results, summarized in the
[acceptance matrix](acceptance-matrix.md) format:

| Field | Definition |
|---|---|
| Fault classes exercised | For example wrong record, ambiguous target, stale target, drift, duplicate submission, dialog interruption, focus theft, disconnect (per substrate). |
| Expected outcome | Safe halt, refusal, or verified reconciliation per class. |
| Observed outcome | What each trial actually did, with run-report references. |
| Silent incorrect successes | Count of runs reporting success while the system of record disagrees. **Acceptance target: 0.** |
| Over-halts | Healthy runs that halted unnecessarily; reported honestly because they carry the operational cost of intervention. |

## 7. Deployment analysis

| Field | Definition |
|---|---|
| Recommended boundary | Which [deployment lane](deployment-boundaries.md) fits the data sensitivity and infrastructure. |
| Data flows | What crosses which boundary, per the deployment matrix. |
| Operational model | Scheduling, halt routing, who reviews reports, expected intervention rate. |
| Open items | Access, security review, or legal items required before pilot. |

## 8. Economics

| Field | Definition |
|---|---|
| Volume and time baseline | Customer-provided run volume and manual minutes. |
| Modeled savings | Per the [ROI worksheet](roi-calculator.md), under conservative assumptions, with every input attributed. |
| Costs | Sprint, pilot, production, and operational intervention costs. |

## 9. Evidence pack manifest

Every artifact in the pack, with hashes: run directories (`REPORT.md`,
`report.json`), fault-case reports, coverage matrix, and, on "go", the
qualified prototype bundle. Reports shared outside the customer boundary are
scrubbed first; the raw evidence stays in the agreed boundary
([run reports: scrubbing](../guides/run-reports.md#scrubbing-shared-reports)).
