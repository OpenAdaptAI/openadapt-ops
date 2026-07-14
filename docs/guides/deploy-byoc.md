# Deploy BYOC (in your VPC)

!!! warning "Target-state page — the Connector is not built yet"
    BYOC keeps the reused engine and the callback contract that exist today, and
    adds **one new component: an outbound-only Connector** that flips job delivery
    from push to pull. That Connector, its long-poll job API, and the Terraform
    stand-up module are **in progress, not shipped**. This guide documents the
    intended operator experience so you can evaluate the model; see the
    [gap list](#what-is-not-yet-built) for what is real today.

**Bring Your Own Cloud (BYOC)** runs the PHI-touching data plane **inside your
own cloud account or perimeter**, while we operate the control plane that
schedules and tracks runs. It is the managed experience of the
[hosted lane](hosted.md) with the data residency of
[on-prem](deploy-on-prem.md): **PHI never enters our infrastructure**, and you
open **zero inbound ports**.

## The topology

```
   Your VPC / perimeter                    Our control plane
  ┌───────────────────────┐               ┌──────────────────────┐
  │  Connector (outbound   │  long-poll →  │  Job queue           │
  │  only, long-polls) ────┼──────────────▶│  (schedules runs)    │
  │      │                 │  ◀── callback │  Metadata DB         │
  │      ▼                 │  (PHI-free)   │  (status/metrics)    │
  │  openadapt-flow engine │               └──────────────────────┘
  │      │                 │
  │      ▼                 │
  │  Your app / EMR + your │
  │  object storage (PHI)  │
  └───────────────────────┘
```

The **Connector** long-polls a held-open outbound socket to our control plane —
exactly the pattern the Citrix Cloud Connector and the GitHub self-hosted runner
use. When a job is available, the Connector pulls it, the local engine runs it
against your app, writes the report to **your** storage, and posts a **PHI-free
callback** (status, timings, counts, a storage path). The control plane never
holds an inbound connection into your network and never sees PHI.

## What crosses the boundary

| Direction | Carries | PHI? |
|---|---|---|
| Connector → control plane | long-poll for jobs; PHI-free run callback | **No** |
| Control plane → Connector | job descriptor (bundle ref, params ref, target) | **No** |
| Engine → your storage | `report.json`, screenshots, healed bundle | Yes — **stays in your account** |
| Engine → your app / EMR | GUI actions, effect-verification reads | Yes — **stays in your perimeter** |

The callback body is **PHI-free by construction**: a status enum, timings,
aggregate counts, a storage *path* opaque to us, and a halt descriptor authored
PHI-free. See
[the control/data boundary](../reference/connector-config.md#the-phi-free-control-and-data-boundary).

## Intended stand-up

```bash
# 1. In your VPC: deploy the Connector (intended — Terraform module in progress)
#    It needs an enrollment token from the control plane and your storage config.
openadapt-connector enroll --token <enrollment-token> \
  --storage s3://your-phi-bucket/openadapt-runs \
  --control-plane https://app.openadapt.ai

# 2. The Connector long-polls for jobs; the local engine runs each one wired by
#    your own deployment.yaml (backend, effects, policy) — see below.
```

The engine inside your VPC is wired by the **same
[`deployment.yaml`](../reference/deployment-config.md)** as any other run: your
backend URL, your system of record for
[effect verification](../concepts/effect-verification.md), your policy. BYOC
changes only three things from the hosted lane:

1. **Transport** — push enqueue becomes an outbound **pull** (the Connector).
2. **Storage owner** — our signed URLs become **your** object store; the control
   plane keeps only a path.
3. **One new component** — the outbound-only Connector.

Engine, run-report schema, halt/teach contract, and callback body are unchanged.

## Secrets and egress stay in your account

- **Secrets** (EMR credentials, `--secret` field values) resolve from **your**
  KMS/Vault by reference; no ambient credentials sit in the run environment.
- **Egress** is enforced at your network boundary against a fail-closed
  allow-list — the same allow-list math the engine applies in-process, but at the
  perimeter too.
- The [model tiers stay off](regulated-run.md) unless you opt in and point them at
  an [on-prem VLM appliance](../concepts/vlm-appliance.md) in your account.

## Compliance

BYOC's control-plane exposure is **thin** — run metadata, not PHI — but the PHI
lane still requires a **signed BAA and a current HIPAA risk analysis** before it
carries real PHI. See [the compliance gate](regulated-run.md#the-compliance-gate).
SOC 2 Type 2 helps close deals but is not strictly required to start a pilot.

## What is not yet built

- The **outbound Connector** and its pull/long-poll job API (`enroll`,
  `/jobs` long-poll + lease, `/callback`) are **in progress**.
- The **Terraform one-command stand-up module** is unbuilt.
- The **Windows/Citrix Connector packaging** (MSI / service + Citrix-adjacency
  runbook) — the highest-value BYOC form — is unbuilt.
- Until these land, the equivalent lane is
  [self-hosted / on-prem](deploy-on-prem.md), which already runs the same engine
  inside your perimeter without the managed orchestration.
