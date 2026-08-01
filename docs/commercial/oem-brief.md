# OpenAdapt Execute: private-pilot guide

OpenAdapt Execute gives a software or service provider a safe way to complete
an authorized transaction in an application that the provider cannot directly
integrate with.

Your product decides the business action. OpenAdapt executes the qualified
transaction in the customer-controlled browser, desktop, RDP, Citrix, or API
environment. It then returns a precise outcome and a receipt.

```text
authorized transaction
  -> qualified local execution
  -> effect verification
  -> verified | a precise non-success outcome + receipt
```

This is a good fit for a vertical software vendor, an RCM provider, a BPO, or
an integration firm. The provider already has structured inputs, business
logic, and an exception team. OpenAdapt supplies the verified last action in
the customer system.

!!! note "Private pilot. Not a public API."
    This page describes the private-pilot product contract. It is not an
    self-service integration recipe and it does not publish partner access,
    credentials, an SDK, or a webhook URL. `openadapt-types` 0.9.0 publishes
    the shared async Execute schema, OpenAPI document, and signed decision
    contract. OpenAdapt Cloud provides private execution, customer-runner
    coordination, and receipt delivery for approved pilot partners.

## What a partner gets

OpenAdapt starts with one named transaction in one customer environment. For
example: create a follow-up appointment, submit a claim correction, update a
loan application, or post a reconciled record.

The qualification work produces:

- a reviewed workflow and parameter contract;
- a named application, version, environment, and runner boundary;
- identity checks for each consequential action;
- a declared effect and the required evidence strength;
- an idempotency rule and an uncertain-delivery rule;
- representative and fault cases;
- a sealed qualified version and an acceptance report.

The partner can then submit an authorized transaction to the private pilot
service. The service selects only the exact qualified workflow and the exact
customer-controlled runner that can meet the contract.

## The Execute contract

The production surface is asynchronous. A transaction can wait for a person,
wait for reconciliation, or resume after a runner restart. A caller receives
an execution identifier and observes state changes. It does not wait for a GUI
session in one HTTP request.

### ExecuteRequestV1

Each `ExecuteRequestV1` contains exactly these public fields:

- `schema_version: openadapt.execute-request/v1`;
- `qualification_id`;
- `workflow_version` and `workflow_digest`;
- `environment_id`;
- typed `parameters`;
- `idempotency_key`;
- `authorization_context` with `actor_id` and `authorization_reference`;
- `effect_strength_schema_version`; and
- `minimum_effect_strength`.

The same idempotency key with the same request returns the existing execution.
A changed request under that key is refused. OpenAdapt also keeps an
effect-aware record of delivery, so it does not repeat a write after an
uncertain result.

### Internal qualification and runtime binding

The qualification and runtime hold additional controls outside
`ExecuteRequestV1`. They bind the approved workflow to its sealed bundle,
policy, runner capability set, and customer environment. The runner also
checks the locally issued authority and its exact delivery and input binding
before it acts. These controls protect the execution path; they are not caller
fields in the public Execute request.

### Lifecycle states

The private-pilot contract uses these states. A state describes current work;
it is not a success claim.

| State | Meaning |
|---|---|
| `queued` | OpenAdapt accepted the request for dispatch. |
| `running` | The runner is observing, resolving, acting, or verifying. |
| `decision_required` | A typed attended question needs an authorized person. |
| `waiting_for_reconciliation` | A possible or conflicting effect needs a live read before OpenAdapt can continue. |
| `terminal` | The execution has one final transaction outcome and a receipt. |

### Terminal transaction outcomes

The released OpenAdapt Execute v1 contract defines these outcomes. The
private-pilot service exposes the same values without translating them into a
generic "success" flag.

| Outcome | Meaning for the partner |
|---|---|
| `verified` | The configured authorization, identity, postcondition, and effect contracts passed. |
| `halted_before_effect` | OpenAdapt stopped and evidence established that no consequential effect occurred. |
| `reconciliation_required` | Delivery, persistence, or the observed effect is uncertain or conflicting. Do not submit the write again. Reconcile first. |
| `failed_platform` | A platform failure occurred before any possible business effect. |
| `rejected_policy` | Qualification, authorization, identity, environment, or policy refused the transaction before effect. |
| `rolled_back_verified` | A configured compensating action completed and the receipt includes verification evidence for that compensating effect. |

`verified` is the business-success outcome. `rolled_back_verified` proves the
configured compensating effect, not the original requested effect.

## Customer-controlled execution

The runner stays in the agreed customer boundary. This can be a workstation,
a customer-managed VM, a VDI client, or a dedicated browser runner.

The runner validates the exact authorization locally before it acts. The
control plane cannot substitute the bundle, widen the policy, or reuse an
authorization for a different input. Sensitive screen content and live entity
identifiers stay in that boundary unless the customer explicitly configures a
different evidence path.

OpenAdapt uses a qualification-owned entity class only as static presentation
metadata. A task may say `patient record`, `insurance claim`, or `loan
application` when its certified contract declares that class. A remote surface
does not infer a class or an identity from a screenshot, OCR, an application
name, parameters, or a model. If the class is unavailable, it uses `record` or
`item`. The runner rechecks the real identity before any resumed action.

## Attended decisions and mobile delivery

When the runner cannot prove a required condition, it creates one signed,
typed decision task. The operator can answer from the local console or the
authenticated phone/web decision surface. The phone receives a closed context;
the customer runner retains the detailed evidence.

An operator answer is not a command to repeat a write. The runner first
reacquires focus, a fresh observation, the workflow state, identity evidence,
and the target. It continues only if those checks pass. The resulting receipt
binds the decision, the runner transition, and the final state to the exact
task and authorization.

The released public contract for this round trip is
`openadapt-types` 0.9.0. It defines the async Execute schema and OpenAPI
document, plus signed, PHI-safe decision tasks and receipts. Flow and Cloud use
this contract for the decision relay and private-pilot execution. The partner
event stream does not contain raw screenshots or live record data.

## Receipts and partner integration

### ExecuteEvidenceReceiptV1

Every terminal execution returns an `ExecuteEvidenceReceiptV1` with exactly
these public fields:

- `schema_version: openadapt.execute-evidence-receipt/v1`;
- `receipt_id`, `execution_id`, and `workflow_digest`;
- the terminal `outcome`;
- `contracts`: `authorization_passed`, `identity_passed`,
  `postcondition_passed`, `effect_passed`, `minimum_effect_strength`, optional
  `observed_effect_strength`, `model_used`, and `external_network_used`;
- `delivery_uncertain`;
- `compensation_effect_verified`: always present, normally `false`, and `true`
  only when the outcome is `rolled_back_verified`;
- `evidence_digest`; and
- `issued_at`.

The status resource supplies the receipt identifier only when its state is
`terminal`. It also supplies the terminal outcome. This keeps an in-progress
state separate from a final outcome.

### Local and private evidence

The customer-controlled runner retains richer evidence outside
`ExecuteEvidenceReceiptV1`. This can include the exact bundle and input
bindings, runner and environment details, report bodies, screenshots, live
identity checks, and application observations. The public receipt identifies
that evidence by digest. It does not copy it into the partner event stream.

The partner stores the receipt with its own transaction record. This lets the
partner tell an end customer what happened without using a screenshot or a UI
banner as proof.

Private-pilot integrations use signed, versioned webhook events and polling.
Webhook retry, signature verification, ordering, and event deduplication are
part of the Execute contract. The [Execute integration guide](execute-api.md)
shows the request, status, receipt, and webhook flow.

## Start with one workflow

The first step is a [Workflow Qualification Sprint](qualification-sprint.md),
not broad platform integration. Bring one repeated transaction, the actual
target application and environment, a verifier path, and the operator who
handles exceptions.

The sprint gives both teams a qualified transaction, a measured acceptance
campaign, and a clear reuse decision. If the same transaction can transfer to
additional customer environments, OpenAdapt and the partner turn it into a
commercial compatibility pack.

## Product boundary

| Layer | Availability | Role |
|---|---|---|
| OpenAdapt Flow | MIT-licensed | Local compiler, governed runtime, transaction outcomes, qualification tools, and receipt mechanisms. |
| `openadapt-types` 0.9.0 | MIT-licensed and released | Shared async Execute schema and OpenAPI document, plus signed decision-task and decision-receipt contracts. |
| OpenAdapt Cloud foundation | Private and deployed | Tenant control plane, private Execute endpoints, customer-runner coordination, signed decision relay, audit records, and managed operations. |
| OpenAdapt Execute | Private pilot | Versioned transaction submission, status, receipt delivery, and partner integration for approved pilot partners. |
| Compatibility packs and verifier recipes | Commercial | Per-application and per-environment qualification assets, deployment evidence, and support. |

The open runtime remains inspectable. The commercial value is the qualified
transaction, customer-environment evidence, operational delivery, and support.

## Next step

[Qualify one workflow](qualification-sprint.md){ .md-button .md-button--primary }

Bring one system, one transaction, and one measurable business result. We will
define the execution and evidence contract together.
