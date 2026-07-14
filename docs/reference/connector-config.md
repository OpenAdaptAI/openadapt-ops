# Connector and runner configuration

!!! warning "Target-state reference — the Connector is not built yet"
    This page documents the **intended** configuration for the managed runner and
    the BYOC Connector. The runner contract (`enqueue` / `run-callback`) exists
    today for the web runner; the **outbound Connector**, its pull job API, and
    the config surface below are **in progress**. Nothing here is selectable yet.
    See the [gap list](#what-is-not-yet-built).

The [deployment config](deployment-config.md) wires a single **local** run. To
run under a **control plane** — our cloud, or [BYOC in your VPC](../guides/deploy-byoc.md)
— one more layer describes how jobs reach the engine and where results land. That
is the **runner contract** and, for BYOC, the **Connector**.

## The runner contract

Every runner variant — our-cloud web runner, the future Windows runner, the BYOC
Connector — speaks the **same two endpoints and the same job / callback shapes**.
The control plane routes on the workflow's target, never on how the runner is
deployed.

- **`enqueue(Job, x-runner-secret)`** → validate the shared secret, spawn the run
  asynchronously, return `{accepted, call_id}` immediately.
- **`Job`** = a signed bundle GET, a signed report PUT, the `target_url`, an
  `allowed_hosts` egress allow-list, `params`, and a `secrets_ref`.
- **`POST /run-callback` (`x-runner-secret`)** is the **only database writer**.
  Its body is:

  ```json
  {
    "run_id": "...", "org_id": "...",
    "status": "running | success | halt | failed",
    "report_path": "s3://.../report.json",   // a PATH, never the body
    "metrics": { "steps": 0, "halts": 0, "heals": 0, "model_calls": 0,
                 "duration_s": 0, "cost_usd": 0 },
    "error": null,
    "halt": { "step_intent": "...", "reason": "..." },  // authored PHI-free
    "new_bundle_version": null
  }
  ```

This callback body is **PHI-free by construction**: a status enum, timings,
counts, an opaque storage path, and a halt descriptor authored PHI-free.

## The PHI-free control and data boundary

The boundary is **architectural, not policy** — the control plane physically
receives only an enumerable metadata allow-list, with zero cross-account access
to your data.

| The control plane **may** see | The control plane **must never** see |
|---|---|
| Run status + timestamps | Screenshots / step frames |
| Aggregate metrics (steps, halts, heals, model calls, duration, cost) | OCR text, resolved field values |
| A halt descriptor (`step_intent` / `reason`, authored PHI-free) | Patient identifiers |
| A storage **path**, opaque to us | `report.json` **bodies** |
| Connector health / lease, engine + bundle version, billing counters | PHI-bearing params, injected secrets / EMR credentials |

Enforced by construction: the egress allow-list is applied at the **network
boundary** (fail-closed), not only in-guest; no ambient credentials sit in the run
environment (signed-URL I/O is done runner-side); secrets resolve in your
KMS/Vault by reference; and each run gets one clean environment (revert or, after
PHI, **destroy** — never returned to a shared pool).

## Intended Connector config (BYOC)

The Connector runs **in your VPC**, opens **zero inbound ports**, and long-polls
the control plane outbound for jobs. Intended shape:

```yaml
# connector.yaml — intended; not yet built
control_plane:
  url: https://app.openadapt.ai
  enrollment_token: "${OPENADAPT_ENROLL_TOKEN}"   # one-time, from the console

transport:
  mode: pull                 # outbound long-poll (push is the our-cloud runner)
  poll_interval_s: 5
  lease_ttl_s: 300           # a crashed run's lease is reaped after this

storage:
  kind: s3                   # s3 | azure-blob | gcs | filesystem
  bucket: your-phi-bucket
  prefix: openadapt-runs/    # the control plane keeps only paths under here

secrets:
  provider: vault            # vault | aws-kms | azure-keyvault | env
  # references only — resolved in YOUR account, never sent to the control plane

egress:
  allowlist:                 # fail-closed; enforced at your network boundary
    - emr.internal.example.org
```

The engine that the Connector drives is wired by your ordinary
[`deployment.yaml`](deployment-config.md) (backend, effects, policy). BYOC changes
only three things versus the our-cloud runner:

1. **transport** — push enqueue → outbound **pull** (this Connector);
2. **storage owner** — our signed URLs → **your** object store (control plane
   holds only a path);
3. **one new component** — the outbound-only Connector itself.

Engine, run-report schema, halt/teach contract, and callback body are unchanged.

## Substrate routing (target-state)

The control plane routes a job on the workflow's `target_kind`:

- `web` → the Modal gVisor web runner (exists today).
- `desktop` → the Windows runner (`acquire_session` → deploy bundle →
  launch in-session agent → `WindowsBackend.replay` → signed report PUT →
  callback → `release_session` in a `finally`). **Unbuilt.**

## What is not yet built

- The **outbound Connector** and its pull job API (`enroll`, `/jobs` long-poll +
  lease, `/callback`) — **in progress**.
- The **`connector.yaml` surface** above — not yet a real schema.
- The **Terraform stand-up module** and **Windows/Citrix Connector packaging**
  (MSI/service) — unbuilt.
- The **`desktop` (Windows) runner** wiring into the control plane — unbuilt; only
  the `web` runner is live.
- **Confidential-hosted** single-tenant CVM runner — deferred (contract-gated).
