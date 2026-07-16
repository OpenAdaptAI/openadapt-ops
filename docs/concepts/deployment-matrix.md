# Deployment and data-boundary matrix

OpenAdapt separates the surface a workflow drives from the boundary in which it
runs. The same compiler, bundle format, safety gates, and report schema can be
used in each lane; substrate maturity and data handling differ.

## Current matrix

| Deployment / substrate | Browser | Windows desktop | Remote display / Citrix |
|---|---|---|---|
| **OpenAdapt Hosted** | **Beta launch candidate.** Managed execution of validated browser bundles, structural reports, replacement activation, billing, and metering is implemented. The bounded non-regulated recorder is live-provider qualified; the complete paid account-to-run lifecycle remains pending. | Experimental runner work; not included in the browser candidate. | Research only; no hosted Citrix claim. |
| **Customer cloud / BYOC** | **Experimental / scoped deployment.** Customer storage and runner must satisfy the destination policy and be qualified for the actual deployment. | Experimental; qualify the actual app and runner. | Research; a protocol adapter or analog is not a validated Citrix deployment. |
| **Self-hosted / on-prem** | **Beta reference engine.** Local record, compile, replay, and reports. | Experimental local proof. | RDP and pixel-only analog are research spikes. |

The browser launch candidate does not promote every cell. Code presence, a shared runner
protocol, or successful checkout is not evidence that Windows, RDP, or Citrix
is production-ready.

## Artifact boundary and runtime boundary

Two boundaries must be reviewed independently:

1. **Authoring artifacts:** recordings, screenshots, input events, compiled
   bundles, templates, reports, and teaching evidence.
2. **Runtime observations:** live frames, OCR/accessibility text, injected
   parameters, model inputs, logs, and effect-verifier values generated while a
   workflow runs.

An authoring artifact may cross an approved boundary only as a sanitized,
manifested derivative. A sanitized recording does not imply that runtime data
will remain sanitized; a real EMR can display PHI as soon as replay begins.

| Data movement | Hosted | Customer cloud / BYOC | Self-hosted |
|---|---|---|---|
| Existing raw authoring artifact | Refuse generic remote upload. | Keep within customer policy. | Local. |
| Explicit hosted-recorder observations | Allow only for a public-HTTPS, non-regulated session inside the declared hosted recording boundary. | Keep within customer policy. | Local. |
| Approved sanitized derivative | Allow when manifest, hash, review, and destination pass. | Allow to a verified customer endpoint when policy permits. | Local or explicitly exported. |
| PHI-bearing runtime frame | Outside the shared hosted boundary unless a specific regulated service is configured. | Remains inside customer boundary. | Remains local. |
| Minimized control metadata | Allow by schema and destination policy. | Allow by schema and destination policy. | Optional/no egress. |
| Secret value | Never browser-visible or serialized into enqueue payloads. | Resolve inside customer runner. | Resolve locally. |

## Sanitized derivatives

“Scrubbed” means the source was inventoried, a separate copy was transformed,
the result was rescanned, unresolved content was refused, and a manifest binds
the policy and approval to the exact derivative hash. It does not mean the
source was modified or that every future run is PHI-free.

It also does not mean a transformed recording remains runnable. Register the
approved recording derivative, compile/lint/certify/replay locally, then
sanitize/review/approve the bundle. Hosted admits that exact bundle only with a
fresh `validate-hosted` operator attestation. If recording sanitation changed
execution-bearing content, ingest returns `needs_parameterization`; parameterize
before compilation rather than weakening the privacy or runtime gate.

Cloud checks the attestation's exact recording and bundle hashes, provenance,
report and evidence hashes, policy, engine-derived `low`/`consequential` risk
class, HMAC, freshness, and one-time organization/token challenge. Server-side
policy, risk-class, and deployed compiler-version allowlists are additional
restrictions. This is operator self-attestation, not independent certification
or a general safety guarantee.

The risk-based launch default is:

- schema-minimized break descriptors may upload automatically;
- recordings and bundles require local review unless an administrator adopts a
  measured automatic policy with complete handler coverage;
- unsupported, unknown, symlinked, or unresolved content is blocked;
- modifications after approval invalidate the derivative hash;
- the destination must be known and allowed independently of artifact status.

See [Hosted browser execution](../guides/hosted.md) for the complete protocol.

## Hosted browser launch candidate

The implemented candidate path comprises:

- Stripe Checkout using the configured product and price;
- authentication, onboarding, and organization isolation;
- local recording, compilation, repair, and runtime validation before upload;
- bounded hosted recording for explicitly initiated, public-HTTPS,
  non-regulated targets;
- object-backed approved artifacts and signed access;
- runner enqueue and authenticated callbacks;
- structural reports, locally validated replacement activation, schedules, and recovery;
- subscription entitlements and usage metering.

Production selects live mode explicitly. Development mock mode is visibly
synthetic. A missing production dependency makes the affected operation
unavailable rather than substituting a simulated success.

The hosted recorder has passed its bounded, non-simulated live-provider
qualification on a Flow 1.8.0 worker. Authenticated live health also qualified
the exact-version replay and compiler service identities. Those health probes
do not establish successful workflow execution. The documented clean-account
purchase-to-run acceptance lifecycle remains pending. Do not infer public paid
availability from this architecture description.

The configured Stripe offer is the commercial source of truth. This matrix does
not create a price, quota, SLA, certification, or backend entitlement.

## Customer-controlled regulated execution

Use a customer-controlled boundary when a live workflow necessarily displays
PHI or other regulated data. Sanitized authoring derivatives and minimized
metadata may cross approved endpoints; PHI-bearing live frames and values stay
inside the boundary.

A deployment scope must name:

- the exact application and substrate;
- who operates the control plane, runner, storage, and model endpoints;
- allowed destinations and artifact classes;
- credentials and secret resolution;
- identity coverage and independent system-of-record effect verification;
- policy, certification, review, approval, and exception handling;
- encryption, retention, deletion, logs, incident response, updates, rollback,
  support, and legal agreements.

Architecture documentation is not a HIPAA, PHIPA, SOC 2, or other compliance
determination. The parties must complete the legal, contractual, security, and
risk work required for the actual deployment.

## Backend evidence boundary

- **Browser:** Beta local engine and the hosted launch-candidate substrate. It is the only
  backend exercised end to end against a real third-party application in the
  published engine evidence.
- **Windows UIA:** Experimental local evidence, not a broad app/platform study.
- **macOS native:** Experimental building blocks without a validated native
  end-to-end product path.
- **RDP:** Research adapter with mock/offline evidence.
- **Citrix:** Pixel-only remote-display analog; not validated against ICA/HDX,
  real charts, lock screens, latency, DPI, or synthetic-input controls.

Review [What works today](../get-started/what-works-today.md) and the engine's
[published limits](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md)
before selecting a workflow.
