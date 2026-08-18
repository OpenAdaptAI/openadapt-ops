# Deployment and data-boundary matrix

OpenAdapt separates the surface a workflow drives from the boundary it runs in.
Every lane uses the same compiler, bundle format, safety gates, and report
schema. What differs across lanes is data handling, not substrate capability.

## Deployment architecture

| Deployment / substrate | Browser | Windows UIA | Native macOS | Native Linux | RDP | Citrix / VDI |
|---|---|---|---|---|---|---|
| **OpenAdapt Hosted** | Managed execution, schedules, reports, usage, and billing | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud | Customer-controlled runtime connected to Cloud |
| **Customer cloud / bring your own cloud (BYOC)** | Customer runner and storage with managed governance | Customer runner and storage | Customer runner and storage | Customer runner and storage | Customer runner and storage | Customer runner and storage |
| **Self-hosted / on-prem** | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail | Local runner and audit trail |

Every substrate is a first-class target of the shared compiler, runner, and
safety gates. Where each lane is available today differs, and the matrix states
that plainly rather than implying uniform hosted availability. The public
$500/month self-serve subscription runs the browser substrate in OpenAdapt's
cloud. Windows, native macOS, native Linux, RDP, and Citrix/VDI run in a local,
self-hosted, or customer-controlled boundary and can connect to Cloud for
governed operation. An in-our-cloud desktop runner
exists only as an internal, licensing-gated lane, and multi-tenant hosting of the
desktop substrate in OpenAdapt's cloud is deferred; neither is part of any public
managed-runner offer. None of these native or remote substrates is silently
moved into the shared managed-browser boundary or included as a managed-runner
entitlement. The matrix describes the product architecture; the
[qualification appendix](../get-started/what-works-today.md) and commercial terms
define the accepted workload and entitlement.

In the existing BYOC connector and configuration, a runner and storage inside a
customer-owned cloud boundary execute the workflow. OpenAdapt Cloud can send
bounded authorization and control metadata and receive the declared result and
evidence permitted by the data boundary. Other customer-controlled deployments
can run on a workstation, server, or on-premises virtual machine without being
BYOC. See the [glossary](../reference/glossary.md#byoc).

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
| PHI/PII-bearing runtime frame | Outside the shared hosted boundary unless a specific regulated service is configured. | Remains inside customer boundary. | Remains local. |
| Minimized control metadata | Allow by schema and destination policy. | Allow by schema and destination policy. | Optional/no egress. |
| Secret value | Never browser-visible or serialized into enqueue payloads. | Resolve inside customer runner. | Resolve locally. |

## Sanitized derivatives

“Scrubbed” means the source was inventoried, a separate copy was transformed,
the result was rescanned, unresolved content was refused, and a manifest binds
the policy and approval to the exact derivative hash. It does not mean the
source was modified or that every future run is PHI/PII-free.

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

The retained hosted-recorder qualification used a Flow 1.8.0 worker. The
current Cloud managed-runtime manifest pins Flow <!-- version-claim:hosted-runner-managed-runtime-pin -->1.31.0<!-- /version-claim:hosted-runner-managed-runtime-pin --> at release commit
`2d225dea9a0ad29ca84ce1b037cc0ac671367e28`. Its wheel SHA-256 is
`81133db1528ad1bb1f26e3fcb6aea61b0651db6d905cf2e4943e8383c1f3d29c` and
its source SHA-256 is
`cf1fc356d14d267df82be188de3e9a3575734f18f46ef91ac8075438cc731540`.
The pin proves configured artifact identity. It does not prove that the build is
deployed or that a hosted workflow passed acceptance. Public readiness checks
live mode, authentication, database, private storage, runner, compiler,
runtime-validation trust, runtime boundary, bundle protection, recorder,
callbacks, scheduler, human-decision Web Push, retention, security events,
secret encryption, validation policy, and billing dependencies. Readiness is
configuration and service-identity evidence, not a customer workflow
qualification or SLA.

Stripe is the commercial source of truth for pricing. This matrix does
not create a price, quota, SLA, certification, or backend entitlement.

## Customer-controlled regulated execution

Use a customer-controlled boundary when a live workflow necessarily displays
PHI/PII or other regulated data. Sanitized authoring derivatives and minimized
metadata may cross approved endpoints; PHI/PII-bearing live frames and values stay
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

Consequential RDP and Citrix actions share a two-phase remote contract: a fresh
frame is resolved and identity-checked, then a one-shot input lease refuses
changed session/window context, focus where applicable, geometry, readiness, or
pixels before delivery.

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
- **Linux native:** Required current-main `linux-atspi-x11` at exact Flow commit
  `3de5fc67` confirmed 3/3 exact-file effects, 3/3 ambiguity refusals, and
  3/3 stale-target refusals on the in-tree GTK3/X11 fixture, with 0 silent
  incorrect successes, 0 over-halts, 0 operator interventions, and 0 model
  calls. Review the [exact required CI job](https://github.com/OpenAdaptAI/openadapt-flow/actions/runs/30059807758/job/89378981573).
- **RDP:** Candidate `82a658a` passed 3/3 unique-file trials on one Parallels
  Windows 11 VM over Aardwolf network RDP with exact guest-tools readback. A
  separate full governed lifecycle over a real FreeRDP3 round trip passed 3/3
  healthy effects and 3/3 drift safe-halts with zero model calls, silent
  incorrect successes, false completions, drift writes, or healthy over-halts.
  Review [Flow PR #142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142),
  [Flow PR #177](https://github.com/OpenAdaptAI/openadapt-flow/pull/177), the
  [Aardwolf report](https://github.com/OpenAdaptAI/openadapt-flow/blob/6610d24cebba27918b8ea507b2f05a094057ac85/benchmark/rdp/results_82a658a_20260718.sanitized.json),
  and the [FreeRDP report](https://github.com/OpenAdaptAI/openadapt-flow/blob/affedc5f1f0de533a0744deaa8e30a203c91c6b3/benchmark/rdp_ladder/results.json).
- **Citrix / VDI:** The released dedicated `--backend citrix` binds the exact
  Workspace window, gates readiness, and preserves the target through durable
  resume. Its accepted no-DOM artifact records 3/3 healthy effects and 3/3
  drift safe-halts with zero model calls, silent writes, false completions, or
  healthy over-halts. It also explicitly records `ica_hdx_accepted: false`:
  this is bounded evidence for the shipped backend contract over a no-DOM
  stand-in, not a counted real ICA/HDX batch. Review [Flow PR #183](https://github.com/OpenAdaptAI/openadapt-flow/pull/183)
  and the [immutable report](https://github.com/OpenAdaptAI/openadapt-flow/blob/f6faac5b900b78cbda5980de0e983a9f987285ac/benchmark/citrix_workspace/results.json).

Review [Qualification evidence](../get-started/what-works-today.md) and the engine's
[published limits](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md)
before selecting a workflow.
