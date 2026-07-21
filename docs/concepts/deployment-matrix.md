# Deployment and data-boundary matrix

OpenAdapt separates the surface a workflow drives from the boundary it runs in.
Every lane uses the same compiler, bundle format, safety gates, and report
schema. What differs across lanes is data handling, not substrate capability.

## Deployment architecture

| Deployment / substrate | Browser | Windows UIA | Native macOS | RDP | Citrix / VDI |
|---|---|---|---|---|---|
| **OpenAdapt Hosted** | Managed execution, schedules, reports, usage, and billing | Not a public hosted offer; runs in the customer boundary | Not a public hosted offer; runs in the customer boundary | Not a public hosted offer; runs in the customer boundary | Not a public hosted offer; runs in the customer boundary |
| **Customer cloud / BYOC** | Customer runner and storage with managed governance | Customer runner and storage | Customer runner and storage | Customer runner and storage | Customer runner and storage |
| **Self-hosted / on-prem** | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail |

Every substrate is a first-class target of the shared compiler, runner, and
safety gates. Where each lane is available today differs, and the matrix states
that plainly rather than implying uniform hosted availability. The public
$500/month self-serve subscription runs the browser substrate in OpenAdapt's
cloud. Windows, native macOS, RDP, and Citrix/VDI run in the customer boundary:
self-hosted or on-prem today, and control-plane-managed in the customer's own
cloud (BYOC) as that Experimental lane opens. An in-our-cloud desktop runner
exists only as an internal, licensing-gated lane, and multi-tenant hosting of the
desktop substrate in OpenAdapt's cloud is deferred; neither is part of any public
offer. Between the customer-boundary lanes the difference is a per-workflow
qualified commercial order rather than a capability gap, and none of these
substrates is an entitlement of the browser subscription. The matrix describes
the product architecture; the
[qualification appendix](../get-started/what-works-today.md) and commercial terms
define the accepted workload and entitlement.

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

## OpenAdapt Hosted

The managed browser path comprises:

- Stripe Checkout for the public subscription;
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

The hosted recorder passed its bounded, non-simulated live-provider
qualification on a Flow 1.8.0 worker. Authenticated live health qualified the
exact-version replay and compiler service identities, and three independent
pre-payment trials verified tenant-bound live Checkout and refusal before
entitlement. The first genuine paid subscription extends that operational
evidence through webhook activation, managed execution, usage, portal, and
cancellation.

Stripe is the commercial source of truth for pricing. This matrix does
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

## Backend evidence

Every substrate is a first-class execution target and every workflow is
qualified in its real environment. The published qualification evidence to date:

- **Browser:** Local engine and public managed substrate, exercised end to end
  against a real third-party application in the published engine evidence.
- **Windows UIA:** The counted
  `20260717-candidate-56759c8-v2` in-tree WinForms matrix passed 3/3 trials with 3/3 independent SQLite effects,
  3/3 stale-target refusals, 3/3 ambiguity refusals, 0 silent incorrect
  successes, 0 over-halts, and 0 model calls. Earlier rejected diagnostic
  matrices remain in the report and are not counted acceptance trials. Review [Flow PR #132](https://github.com/OpenAdaptAI/openadapt-flow/pull/132)
  and its [immutable report](https://github.com/OpenAdaptAI/openadapt-flow/blob/defafbae758a75c8e149d9693f2cffe1f2264b8c/benchmark/windows_uia/results.json).
- **macOS native:** On one macOS
  15.7.3 arm64 host, candidate `b1b61a5` completed 3/3 exact-byte TextEdit
  trials and refused a two-window ambiguity without changing either file, with
  0 silent incorrect successes and 0 over-halts. The immutable batch report
  remains failed because cleanup warnings were classified as batch failure; a
  SHA-256-bound adjudication verified actual cleanup and accepts the action
  effect and ambiguity refusal. Review [Flow PR #135](https://github.com/OpenAdaptAI/openadapt-flow/pull/135)
  and the [exact adjudication](https://github.com/OpenAdaptAI/openadapt-flow/blob/ca1b522cad215875f7471782283f8f8bb8e6c998/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json).
- **RDP:** Candidate `82a658a`
  passed 3/3 unique-file trials on one Parallels Windows 11 VM over network RDP;
  exact guest-tools readback confirmed every effect. Trial latencies were
  51.845s, 10.467s, and 7.477s, with 0 failures, 0 silent incorrect successes,
  0 over-halts, and 0 model calls. Exact snapshot cleanup passed. Review
  [Flow PR #142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142)
  and the [immutable sanitized report](https://github.com/OpenAdaptAI/openadapt-flow/blob/6610d24cebba27918b8ea507b2f05a094057ac85/benchmark/rdp/results_82a658a_20260718.sanitized.json).
- **Citrix / VDI:** Driven pixel-first through the same remote-display adapter
  and the same identity gate and effect verification as every other substrate.
  Each Citrix/VDI workflow is qualified in its real ICA/HDX environment: the
  client, latency, compression, DPI, lock-screen, and synthetic-input behavior
  are exercised against the actual application, the same real-environment
  qualification step every substrate goes through.

Review [Qualification evidence](../get-started/what-works-today.md) and the engine's
[published limits](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md)
before selecting a workflow.
