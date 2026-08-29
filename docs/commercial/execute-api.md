# Invoke a program: Seal or halt

`POST /api/v1/executions` runs one already-qualified compiled program. When
the run ends, `GET /v1/executions/{execution_id}/receipt` returns the Seal:
`ExecuteEvidenceReceiptV1`. That is the existing evidence receipt. Do not
look for a second object.

Unsigned local `openadapt-flow replay` stays free. A production `verified`
outcome without that receipt is a failure. HTTP `202` only means OpenAdapt
accepted the request for durable processing.

This page is for an approved private-pilot partner. OpenAdapt supplies the
service credential and the identifiers from the qualification pack. The hosted
Execute lane stays gated (`EXECUTE_LANE_ENABLED` is false) until a
founder-gated production deploy can issue a signed Seal.

## Oracle tiers

`oracle_tier` on the receipt says how the effect was checked. Mint a
production Seal only at tier 2 or 3.

| Tier | Check | Production Seal |
|---|---|---|
| 0 | Visual / OCR | No. Dev only. |
| 1 | Second session / independent UI read | No. |
| 2 | System-of-record read (API, DB, file, ack) | Yes. |
| 3 | Counterparty artifact (payer status, legal export) | Yes. |

`--break-it` on `openadapt-flow qualify` is the fail-closed test. A fake
success banner must halt. The store must stay unchanged.

## Attended first

A person stays the legal actor. A Seal is not a physician signature.
Consequential writes pause at `decision_required` so an authorized operator
can finish the signed task on phone or desktop. Do not type a physician
password.

The rest of this page is the request, poll, receipt, and webhook contract.

## Choose where execution runs

Execute can dispatch to an approved managed runner or to a customer-controlled
runner. A customer-owned cloud runner and storage boundary can use the existing
[bring your own cloud (BYOC)](../reference/glossary.md#byoc) connector. The
customer runner executes the workflow. Cloud carries bounded authorization and
control metadata and receives only the declared result and evidence allowed by
the data boundary. Other customer-controlled deployments can use a workstation,
server, or on-premises virtual machine without using BYOC.

## Authenticate the service

OpenAdapt issues one service token. The token is restricted to one organization
and a non-empty list of qualification identifiers.

Store the token in a server-side secret manager. Do not send it to a browser or
mobile client. Send it only over HTTPS:

```http
Authorization: Bearer <service-token>
Content-Type: application/json
```

The production base URL is:

```text
https://app.openadapt.ai/api
```

All resource examples below are relative to that base URL.

## Create an execution

Send `POST /v1/executions` with an `ExecuteRequestV1` body:

```json
{
  "schema_version": "openadapt.execute-request/v1",
  "qualification_id": "qualification_12345678",
  "workflow_version": "workflow_20260729",
  "workflow_digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "environment_id": "environment_12345678",
  "parameters": {
    "date": "2026-08-15",
    "record": {
      "id": "12345"
    }
  },
  "idempotency_key": "caller_key_12345678",
  "authorization_context": {
    "actor_id": "caller_agent_12345678",
    "authorization_reference": "authorization_12345678"
  },
  "effect_strength_schema_version": "1",
  "minimum_effect_strength": "independent_system_of_record"
}
```

Use the qualification, workflow, digest, environment, parameter, and effect
values from the qualification pack. The service refuses a request that does
not match the active qualification exactly.

A successful submission returns HTTP `202`:

```json
{
  "schema_version": "openadapt.execute-accepted/v1",
  "execution_id": "018f5b5a-1f8d-7e20-8b70-4e0c8d9a4f21",
  "state": "queued"
}
```

HTTP `202` means that OpenAdapt accepted the transaction for durable
processing. It does not mean that the business effect occurred.

## Keep one idempotency key

Create one idempotency key for one business transaction. Retain the key with
the transaction in your system.

- If an HTTP response is lost, send the exact same request and the same key.
  OpenAdapt returns the existing execution.
- If any request field changes, use a new transaction and a new key.
- OpenAdapt refuses a changed request under an existing key.
- Do not create a new key to repeat a transaction after an uncertain delivery
  or a `reconciliation_required` outcome. Reconcile the possible effect first.

This rule prevents a network timeout from becoming a duplicate write.

## Read the lifecycle state

Poll `GET /v1/executions/{execution_id}`. The response is an
`ExecuteStatusV1`:

```json
{
  "schema_version": "openadapt.execute-status/v1",
  "execution_id": "018f5b5a-1f8d-7e20-8b70-4e0c8d9a4f21",
  "state": "running",
  "terminal_outcome": null,
  "evidence_receipt_id": null,
  "updated_at": "2026-07-29T12:00:15.000Z"
}
```

A lifecycle state reports current work. It does not report the final result.

| State | Integration action |
|---|---|
| `queued` | Wait for dispatch. |
| `running` | Wait while the runner acts or verifies. |
| `decision_required` | Let the authorized operator complete the signed decision task. |
| `waiting_for_reconciliation` | Do not repeat the write. Wait for the live effect check. |
| `terminal` | Read and validate the receipt. |

Only `terminal` carries `terminal_outcome` and `evidence_receipt_id`. A run can
return to `running` after a decision. Do not treat the state sequence as a
strict one-way list.

## Read and validate the receipt

When the state is `terminal`, request
`GET /v1/executions/{execution_id}/receipt`. Before that point, the endpoint
returns HTTP `409`. It also returns HTTP `409` if the terminal run still waits
for trusted evidence.

The evidence receipt is the Seal. Validate it with the published
`openadapt-types` Execute models or the JSON Schema in that package. Then
confirm these bindings in your application:

1. `execution_id` matches the accepted execution.
2. `receipt_id` matches the status resource.
3. `workflow_digest` matches the submitted qualified workflow.
4. `workflow_version`, `qualification_id`, `environment_id`, `runner_id`, and
   `nonce` are present and bind the program, admission, environment, and
   runner.
5. `oracle_tier` is 2 or 3 when `outcome` is `verified`.
6. `outcome` matches `terminal_outcome`.
7. The receipt schema accepts all contract and effect-strength invariants.
8. Store the full receipt with your transaction record.

Python validation is small:

```python
from openadapt_types import ExecuteEvidenceReceiptV1, ExecuteStatusV1

status = ExecuteStatusV1.model_validate(status_json)
receipt = ExecuteEvidenceReceiptV1.model_validate(receipt_json)

assert receipt.execution_id == accepted_execution_id
assert receipt.receipt_id == status.evidence_receipt_id
assert receipt.workflow_digest == submitted_workflow_digest
assert receipt.workflow_version == submitted_workflow_version
assert receipt.environment_id == submitted_environment_id
assert receipt.nonce
assert receipt.oracle_tier >= 2
assert receipt.outcome == status.terminal_outcome
```

Treat only `verified` as proof that the requested business effect passed its
complete configured contract.

| Outcome | Required action |
|---|---|
| `verified` | Accept the requested effect as verified. |
| `halted_before_effect` | Record the halt. The evidence established that no consequential effect occurred. |
| `reconciliation_required` | Do not repeat the write. Reconcile the possible or conflicting effect. |
| `rejected_policy` | Correct the authorization, qualification, identity, environment, or policy input. |
| `failed_platform` | The platform failed before any possible business effect. |
| `rolled_back_verified` | Record that the compensating effect passed. Do not record the original request as successful. |

The portable receipt contains evidence identifiers and contract results. The
customer-controlled runner retains detailed screenshots, live identity values,
and report bodies inside the declared boundary.

## Receive signed webhooks

Execute sends these versioned event bodies:

- `execution.state_changed` with the current `ExecuteStatusV1`;
- `execution.decision_required` with the signed decision task; and
- `execution.terminal` with the `ExecuteEvidenceReceiptV1`.

OpenAdapt returns the webhook signing secret only during endpoint creation or
rotation. Store it in a secret manager. Select it by the signed
`issuer_key_id`.

For every delivery:

1. Parse the body as one strict `openadapt.execute-webhook/v1` event.
2. Remove only the top-level `signature` field.
3. Serialize the remaining object as UTF-8 JSON with sorted keys, no optional
   whitespace, and ASCII escaping.
4. Prefix those bytes with `openadapt.execute-webhook/v1` and one null byte.
5. Calculate HMAC-SHA-256 with the endpoint signing secret.
6. Compare the result with the body `signature` in constant time.
7. Reject the event if its schema, key identifier, or signature is invalid.
8. Persist the event and its `event_id` before you return a successful HTTP
   response.

The `openadapt-types` models implement the same canonicalization and
`verify_hmac()` check. Use them instead of maintaining a second algorithm when
possible.

Each delivery includes these transport headers:

```http
Content-Type: application/json
User-Agent: OpenAdapt-Execute-Webhook/1.0
X-OpenAdapt-Event-Id: <opaque-event-id>
X-OpenAdapt-Delivery-Attempt: <positive-integer>
```

`X-OpenAdapt-Event-Id` and `X-OpenAdapt-Delivery-Attempt` are advisory copies
of the signed body `event_id` and `delivery_attempt`. The signed body is
authoritative. Select the secret with the signed body `issuer_key_id` and
verify the signed body `signature`; the signature is not an HTTP header.

### Delivery, order, and retry rules

Webhook delivery is at least once. A delivery can arrive more than once or
after a later state notification.

- Verify the signature before deduplication.
- Deduplicate by the signed `event_id`.
- Return a `2xx` response only after durable persistence.
- A timeout, network error, or retryable HTTP response can cause redelivery.
- Do not use arrival order to update the execution state.
- Fetch `GET /v1/executions/{execution_id}` after a notification when you need
  the current state.
- Treat a validated `execution.terminal` receipt, or the matching receipt
  resource, as authoritative. Never let a late state event replace it.

This pattern also covers a response loss after your endpoint accepted an
event: OpenAdapt can retry, and your `event_id` record makes the second delivery
safe.

## Process children are separate executions

A [ProcessContract](../concepts/process-contract.md) parent sequences
independently admitted capabilities. Each child is one `POST /v1/executions`
with that child's `qualification_id`, `workflow_version`, `workflow_digest`,
and its own `idempotency_key`. The parent doesn't collapse them into one
request.

Copy a handoff parameter into the next child's `parameters` only when the
predecessor receipt `outcome` is `verified` and the predecessor's effect
contract bound that fact. Don't replay the parent. If a predecessor returns
`reconciliation_required`, stop and reconcile; don't dispatch the successor.

See [Sequence work across two applications](../guides/compose-multi-application.md).

## Integration checklist

- Keep the service token and webhook secret on the server.
- Bind every request to the supplied qualification identifiers.
- Keep the same idempotency key and body across transport retries.
- Distinguish lifecycle states from terminal outcomes.
- Validate and store the terminal receipt.
- Never resubmit a possible write before reconciliation.
- Verify, persist, and deduplicate each webhook before acknowledgment.

For the product and qualification boundary, read the
[OpenAdapt Execute private-pilot guide](oem-brief.md).
