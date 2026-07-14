# Choose a deployment

OpenAdapt is a **deployment-choice spectrum**, not one hosting model. The engine,
the bundle format, the CLI, the run report, and the safety model are identical
everywhere; what changes is **where the data lives and who operates the runner**.
This page helps you pick, and links to the how-to for each.

!!! note "Target-state overview"
    The self-hosted / on-prem lane is real today. The managed lanes
    (our-cloud runner, BYOC-in-your-VPC connector) are **partially built** — the
    control-plane contract and the engine exist; the managed provisioning and the
    outbound connector are in progress. Each lane below states its honest status.
    Nothing here takes recurring money for a runner that cannot yet run.

## The spectrum

| Deployment | Where PHI/data lives | Who operates the runner | Status |
|---|---|---|---|
| [**Self-hosted / on-prem**](deploy-on-prem.md) (air-gapped) | Entirely in your environment | You | **Available** |
| [**BYOC — in your VPC**](deploy-byoc.md) (control-plane-managed) | In your cloud account / perimeter | You host the data plane; we manage orchestration | **In progress** |
| [**Our cloud — non-PHI**](hosted.md) (Hosted) | Our infrastructure | We do | **Preview / waitlist** |
| **Confidential-hosted — regulated** (single-tenant CVM) | Our infrastructure, provider-excluded | We do | **Deferred** (contract-gated) |

Read the rows top-to-bottom as "most control / least managed" → "most managed /
least control". There is no single right answer; the right answer is the row your
data policy and your ops appetite point to.

## How to choose

**Start with the data.**

- **Regulated data that cannot leave your environment (PHI, PII, contractual
  residency)** → [self-hosted / on-prem](deploy-on-prem.md) or
  [BYOC](deploy-byoc.md). In both, PHI never enters our infrastructure — we see
  only PHI-free run metadata (status, timings, counts, a storage *path*). On-prem
  is the strictest (air-gapped, no egress at all); BYOC keeps the data plane in
  your cloud account while we manage orchestration.
- **Non-regulated data, and you would rather not operate the stack** → the
  [our-cloud Hosted](hosted.md) lane (currently preview / waitlist).
- **You want us to run it *and* the data is regulated** → the confidential-hosted
  lane. It is **deferred**: we build it only when a contract funds the compliance
  program (SOC 2 / HITRUST + BAA). Until then, BYOC gives you a managed experience
  without moving PHI into our cloud.

## What is the same in every lane

Because the [bundle](../reference/bundle-format.md) is the trust boundary and the
[runner contract](../reference/connector-config.md) is uniform, moving between
lanes changes deployment wiring, not workflow behavior:

- The **same compiled bundle** runs unchanged.
- The **same `deployment.yaml`** wires backend / effects / actuation / durability
  / policy.
- The **same run report** (`REPORT.md` + `report.json`) is the audit trail.
- The **control/data boundary is architectural**: the control plane may see run
  status, timings, aggregate metrics, a PHI-free halt descriptor, and an opaque
  storage path — never screenshots, OCR text, resolved field values, patient
  identifiers, or `report.json` bodies. See
  [the runner contract](../reference/connector-config.md#the-phi-free-control-and-data-boundary).

## Honest claims by lane

We scope every data-handling claim to the **lane**, never to the company:

- **Self-hosted / BYOC** → *"PHI never enters our infrastructure."* (We see
  PHI-free metadata only.)
- **Confidential-hosted** (when built) → *"provider-excluded and
  attestation-gated, on a customer-verifiable image we cannot change without your
  re-approval."* We deliberately do **not** claim "we literally cannot see your
  data" — that overstates what a skeptical security review will accept.
- A **BAA and a current HIPAA risk analysis are required** for any PHI lane, even
  the self-hosted one, and even where the data is encrypted and we cannot read it.

There is no company-wide "never leaves your network" promise. You choose where
the data lives; the claim follows your choice.

## Next

- [Deploy on-prem (air-gapped)](deploy-on-prem.md)
- [Deploy BYOC (in your VPC)](deploy-byoc.md)
- [The our-cloud Hosted option](hosted.md)
- [Run fail-closed for regulated work](regulated-run.md)
