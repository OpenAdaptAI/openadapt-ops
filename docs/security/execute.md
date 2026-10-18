---
description: >-
  OpenAdapt Execute, the API that lets a software provider run an authorized
  transaction in an application it can't integrate with, and get a signed
  receipt back.
---

# Execute

Execute lets a software or service provider complete an authorized
transaction in an application it can't integrate with directly. The
provider's product decides what to do. OpenAdapt runs the qualified workflow
on a runner in the customer's environment and returns a signed receipt, the
Seal.

!!! note "Private pilot"
    Execute is available to approved pilot partners. This page describes the
    contract. It doesn't publish credentials, an SDK, or a webhook address.
    The request and receipt schemas are published in the engine
    (`openadapt_flow.contracts.execute`).

## How a request works

Execute is asynchronous. A transaction can wait for a person, wait for a
reconciliation, or resume after a runner restarts, so the caller gets an
execution ID and watches its state.

An `ExecuteRequestV1` has these fields:

| Field | What it is |
|---|---|
| `schema_version` | `openadapt.execute-request/v1` |
| `qualification_id` | The qualification the workflow passed |
| `workflow_version`, `workflow_digest` | The exact workflow |
| `environment_id` | The customer environment and runner |
| `parameters` | Typed inputs |
| `idempotency_key` | The same key with the same request returns the existing execution; a different request under the same key is refused |
| `authorization_context` | `actor_id` and `authorization_reference` |
| `effect_strength_schema_version`, `minimum_effect_strength` | The weakest record check the caller accepts |

The runner checks the authorization against the exact bundle and inputs
before it acts. The service can't substitute a different bundle, loosen the
policy, or reuse an authorization for other inputs.

## States and outcomes

| State | Meaning |
|---|---|
| `queued` | Accepted for dispatch |
| `running` | The runner is working |
| `decision_required` | A question is waiting for an authorized person |
| `waiting_for_reconciliation` | A save may or may not have happened; someone must check the record before anything continues |
| `terminal` | Finished, with one outcome and a receipt |

| Outcome | Meaning |
|---|---|
| `verified` | Authorization, identity, and record checks all passed |
| `halted_before_effect` | Stopped, with evidence that nothing was saved |
| `reconciliation_required` | Whether the save happened is uncertain or conflicting. Don't send the write again; check the record first. |
| `failed_platform` | A platform failure before anything could be saved |
| `rejected_policy` | Refused before any save by qualification, authorization, identity, environment, or policy |
| `rolled_back_verified` | A configured undo ran and was confirmed. This confirms the undo, not the original request. |

Only `verified` is business success.

## The Seal

The Seal is an `ExecuteEvidenceReceiptV1` signed by OpenAdapt Cloud. It names
the execution, the exact workflow version and digest, the qualification, the
environment and runner, the outcome, the check level that confirmed the
save, whether delivery was uncertain, and a digest of the evidence. Only a
check level of 2 (the system of record) or 3 (a counterparty artifact) can
back one.

A local run that ends `VERIFIED` is still reported as done, with
`"proof": "local"`, to an agent; a Seal is not required for that. To attach
Cloud's Seal to a local run, pass `--cloud-execution-id`. How to get, check,
timestamp, and countersign a Seal is in
[Receipts, Seals, and countersigning](../reference/receipts-and-seals.md).

Anyone with the receipt can check the Seal online or offline. See
[Check a Seal online](../cloud/verify-a-seal.md). To be told when an execution
stops before any save, subscribe an endpoint to `execution.halted`; see
[Get told when a run stops](../cloud/stop-alerts.md#the-executionhalted-webhook).

`openadapt flow seal` is a different command: it encrypts a bundle for
deployment and doesn't issue a Seal.

## Try the contract locally

`openadapt flow serve-execute` starts a local reference server on
`127.0.0.1:8787` with a generated bearer token. `--seed-mockmed` adds
synthetic MockMed admissions for testing. It is for development and
isn't the hosted service.

## Attended and unattended

Attended means a person is in session and answers when the run stops to ask.
Unattended needs a dedicated agent identity, privileged access management,
and session recording, and it is qualified separately.

To start, see [Engagements](engagements.md).
