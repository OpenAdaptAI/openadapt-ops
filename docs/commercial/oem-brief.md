# OpenAdapt Execute

OpenAdapt Execute gives a software or service provider a way to complete an
authorized transaction in an application that the provider cannot directly
integrate with.

Your product decides the business action. OpenAdapt executes the qualified
transaction in the customer-controlled browser, desktop, RDP, Citrix, or API
environment. It then returns a Seal: `ExecuteEvidenceReceiptV1`. Unsigned
success is failure.

Hosted Execute is the easy path: an org API key at
`https://app.openadapt.ai/api`, an OpenAdapt-signed Seal, customer runner by
default, $10 / 1,000 `VERIFIED`. The MIT reference is
`openadapt-flow serve-execute` on one machine. Those receipts are self-signed,
so they aren't an OpenAdapt production Seal. The
[Execute integration guide](execute-api.md) has the shared JSON contract.

```text
authorized transaction
  -> qualified local execution
  -> effect verification
  -> Seal (verified | halt | reconciliation_required)
```

The one CLI story:

```bash
openadapt-flow replay bundle --seal
```

A sealed verified run prints `VERIFIED`, a seal id, and
`https://openadapt.ai/seals/{id}`. That route is synthetic and non-PHI only.
`--seal` on replay is the intended Seal command. `openadapt flow seal`
encrypts a bundle for deployment.

The buyer is the technical owner at a vertical software vendor, an RCM
provider, a BPO, or an agent platform. That company already has structured
inputs, business logic, and an exception team. OpenAdapt supplies the last
action in the customer GUI, then a Seal. Health-system IT is a downstream
environment. Do not staff this motion as an IDN RFP.

!!! note "Hosted Execute lane is off."
    Production has `EXECUTE_LANE_ENABLED=false`. Cloud does not mint live keys.
    When the lane is on, create the org API key in the Cloud dashboard.
    `openadapt-types` 0.9.0 publishes the shared async Execute schema, OpenAPI
    document, and signed decision contract. Hosted browser is an Enterprise
    engagement with its own contract.

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

The partner can then submit an authorized transaction to Hosted Execute. The
service selects only the exact qualified workflow and the exact
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

The Execute contract uses these states. A state describes current work; it is
not a success claim.

| State | Meaning |
|---|---|
| `queued` | OpenAdapt accepted the request for dispatch. |
| `running` | The runner is observing, resolving, acting, or verifying. |
| `decision_required` | A bounded attended question needs an authorized person. |
| `waiting_for_reconciliation` | A possible or conflicting effect needs a live read before OpenAdapt can continue. |
| `terminal` | The execution has one final transaction outcome and a receipt. |

### Terminal transaction outcomes

The released OpenAdapt Execute v1 contract defines these outcomes. Hosted
Execute and the MIT reference expose the same values without translating them
into a generic "success" flag.

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

## Two sales motions

Do not mix these in one pitch.

**Attended.** A person is in session. The runner uses that session. Consequential
writes pause for a signed phone or console answer, then recheck live identity
and state. This is the motion you can sell now. The human remains the legal
actor. A Seal is not a physician signature.

**Unattended.** Needs a dedicated agent identity, PAM, and session recording. It
does not type a physician password or stuff a physician login.

Halt UX is the commercial product: who gets the push, what they see, how they
teach one step without invalidating the bundle, and how "click continue" is
refused.

## Oracle tiers

Charge 2 and 3. Tiers 0 and 1 never mint a production Seal.

| Tier | What it reads | Production Seal |
|---|---|---|
| 0 | Visual / OCR | Never. Dev only. |
| 1 | Second session or independent UI read | Never. |
| 2 | System-of-record read (API, database, file, ack) | Yes. |
| 3 | Counterparty artifact (payer status, legal export) | Yes. |

The field map, `requires_seal`, and Copilot coexistence live on
[The Seal](seal.md).

## Attended decisions and mobile delivery

When the runner cannot prove a required condition, it creates one signed,
bounded operational decision task. The operator can answer from the local
console or the authenticated phone/web decision surface. The hosted lane
receives a closed-schema context without screenshots or protected fields. The
runner-local portal can show detailed retained evidence inside the customer
boundary.

An operator answer is not a command to repeat a write. The runner first
reacquires focus, a fresh observation, the workflow state, identity evidence,
and the target. It continues only if those checks pass. The resulting Seal
binds the decision, the runner transition, and the final state to the exact
task and authorization.

These three images show the runner-local, full-evidence portal with synthetic
OpenEMR data. The hosted lane uses the same signed actions and transition
states, but it does not receive these screenshots.

<div class="grid" markdown>

<figure markdown="span">
  ![A mobile identity request shows a retained synthetic OpenEMR frame, the available safe actions, and that no action was sent.](../assets/ui/mobile-decision-request.jpg){ width="314" }
  <figcaption>Request: the phone shows one bounded question and only the actions allowed for that exact pause.</figcaption>
</figure>

<figure markdown="span">
  ![A mobile decision result confirms that the signed answer was accepted and awaits the customer runner.](../assets/ui/mobile-decision-pending.jpg){ width="314" }
  <figcaption>Answer accepted: the signed answer is bound to the run. It is not a successful result. The customer runner must retrieve it and check the live application.</figcaption>
</figure>

<figure markdown="span">
  ![A mobile decision result reports Identity verified after the customer runner checked the live application and saved a bound receipt.](../assets/ui/mobile-decision-result.jpg){ width="314" }
  <figcaption>Runner result: the answer does not become success until the customer runner checks the live state and records the receipt.</figcaption>
</figure>

</div>

[Try all six synthetic decision types](https://app.openadapt.ai/demo/attention)
or review the full
[attended-decision contract](../concepts/halt-learn-loop.md#where-a-halt-goes-the-attended-decision).

The released public contract for this round trip is
`openadapt-types` 0.9.0. It defines the async Execute schema and OpenAPI
document, plus signed, PHI-safe decision tasks and receipts. Flow and Cloud use
this contract for the decision relay and Execute. The partner event stream
does not contain raw screenshots or live record data.

## Receipts and partner integration

### ExecuteEvidenceReceiptV1 is the Seal

Every terminal execution returns an `ExecuteEvidenceReceiptV1`. That object is
the Seal. Map the receipt fields 1:1.

| Receipt field | Seal field |
|---|---|
| `receipt_id` | Seal id. Verify at `https://openadapt.ai/seals/{receipt_id}` (synthetic only). |
| `execution_id` | The `POST /v1/executions` that produced this Seal |
| `workflow_digest`, `workflow_version` | Admitted program |
| `qualification_id`, `environment_id`, `runner_id`, `nonce` | Admission, environment, runner, uniqueness |
| `oracle_tier` | 0 visual, 1 second-session, 2 SoR, 3 counterparty |
| `outcome` | `verified` / halt / `reconciliation_required` / the other terminal values |
| `contracts` | Authorization, identity, postcondition, effect |
| `evidence_digest` | Pointer to retained evidence. Bytes stay in the boundary. |
| `issued_at` | When the Seal was issued |

`verified` requires `oracle_tier` 2 or 3. HTTP `202` is not a Seal. The status
resource supplies `evidence_receipt_id` only when its state is `terminal`.

Consequential MCP tools advertise `requires_seal: true`. If the tool returns
unsigned success, treat it as failure.

### Local and private evidence

The customer-controlled runner retains richer evidence outside
`ExecuteEvidenceReceiptV1`. This can include the exact bundle and input
bindings, runner and environment details, report bodies, screenshots, live
identity checks, and application observations. The public receipt identifies
that evidence by digest. It does not copy it into the partner event stream.

The partner stores the Seal with its own transaction record. That is what you
show an end customer. A screenshot or a UI banner is not proof.

Hosted Execute integrations use signed, versioned webhook events and polling.
Webhook retry, signature verification, ordering, and event deduplication are
part of the Execute contract. The [Execute integration guide](execute-api.md)
shows the request, status, Seal, and webhook flow. The field map lives on
[The Seal](seal.md).

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
| OpenAdapt Flow | MIT-licensed | Local compiler, governed runtime, halt/teach, qualification tools. `openadapt-flow serve-execute` is the intended one-machine reference. Receipts are self-signed. |
| `openadapt-types` | MIT-licensed | Shared Execute schema. The evidence receipt is the Seal. |
| OpenAdapt Cloud foundation | Private and deployed | Tenant control plane, customer-runner coordination, signed decision relay. |
| Hosted Execute | $10 / 1,000 VERIFIED | Org API key at `https://app.openadapt.ai/api`. OpenAdapt-signed Seal. Customer runner by default. Lane off until `EXECUTE_LANE_ENABLED` is true. |
| Hosted browser | Enterprise | OpenAdapt operates the browser. Separate from the Execute meter. |
| Compatibility packs and verifier recipes | Commercial | Per-application and per-environment qualification assets. Bundles are not liquid. |

Embed through Execute and MCP into RCM vendors and agent platforms. Hospital
IT RFPs are not the growth engine. If Copilot or Power Automate already
clicked, OpenAdapt can still emit the Seal when asked.

The compiler stays inspectable. Settlement is the Seal.

## Next step

[Qualify one workflow](qualification-sprint.md){ .md-button .md-button--primary }

Bring one system, one transaction, and one measurable business result. We will
define the execution and evidence contract together.
