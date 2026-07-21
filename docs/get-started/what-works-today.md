# Qualification evidence

OpenAdapt compiles demonstrated GUI workflows into deterministic, locally
executable programs. Healthy runs make no model calls. When an interface
drifts, the runtime can re-resolve a target deterministically or use an
explicitly configured model tier; it records any repair and halts when the
configured identity, postcondition, effect, or policy checks cannot verify the
run.

This appendix records qualification evidence and exact deployment boundaries.
It is intentionally more detailed than the product overview so operators and
reviewers can inspect the task, environment, run count, oracle, failure
taxonomy, and caveats behind each supported claim.

OpenAdapt Hosted has a public **$500/month** browser-workflow subscription.
Three independent reversible
production pre-payment trials verified tenant-bound Checkout creation and
confirmed that unpaid sessions grant no entitlement. The first genuine customer
transaction will be observed through signed-webhook activation, managed
execution, usage, portal, and cancellation as continuing production evidence.

## How to read this appendix

Most surfaces below are **Supported**: a first-class product surface you can build
on, backed by the evidence in the "What is actually demonstrated" column. A few
carry a narrower status the Status column names explicitly: **Supported / scoped
deployment** (qualified and ordered as a scoped deployment), **Experimental** or
**Internal only** (built but not a public offer), and **Exploratory** (the
mechanism exists but no real environment has been qualified yet). The
"Important boundary" column states, honestly and per surface, exactly what each
result does and does not cover. Read it before trusting a surface with
consequential work. Public delivery of a given surface may still carry a separate
production-qualification or commercial gate.

Buyer-facing availability is reported distinctly from evidence, and reconciles
to the machine-readable [status manifest](https://openadapt.ai/status.json) that
the website, launcher, and packages also read. **Early access** means the
substrate works and is validated on specific named tasks but is not yet broadly
exercised: it is a first-class execution target ordered as a scoped deployment
and qualified per workflow in its real environment, the same real-environment
qualification step every substrate, including the browser, goes through before
it carries consequential work.

## Integrated product matrix

| Surface | Status | What is actually demonstrated | Important boundary |
|---|---|---|---|
| `openadapt` installer and `openadapt flow` dispatcher | **Supported** | Installs the compiler and exposes the unified command surface. | The standalone `openadapt-flow` package remains the canonical engine and may be installed directly. |
| Record -> compile -> lint -> certify -> replay -> report on a browser | **Supported** | Runs end to end in CI against the bundled app and end to end against a real third-party app. | A clean run is not automatically safe. Identity coverage, risk classification, postconditions, and effect contracts must be audited per bundle. |
| Deterministic target re-resolution and saved heal diffs | **Supported** | Theme, movement, and rename drift are covered by the bundled drift matrix. | Scale/reflow and tenant-specific state can still halt. The base bundle is not silently promoted; save and review a healed bundle explicitly. |
| `lint` and `certify` | **Supported** | Report coverage gaps and refuse bundles that violate the selected policy. | Certification is opt-in and only enforces what the policy names. An uncertified bundle remains runnable with `replay`. |
| Fail-closed `run` admission gate | **Supported** | The shipped gate checks certification, identity/effect coverage, approval fallback, encryption, and manifest integrity before executing. | Development escape hatches exist, and passing the gate does not validate the backend or prove a workflow safe. |
| Identity verification | **Supported, opt-in by step coverage** | Structured identity works on armed browser steps; UIA and pixel/OCR tiers are implemented and adversarially tested. | Unarmed clicks have no identity check. Pure-pixel ambiguity intentionally over-halts, and coverage varies by workflow. |
| System-of-record effect verification | **Supported** | REST, FHIR, and document-hash verifiers run in the live replay path and halt on refuted or indeterminate declared effects. | The compiler does not infer effects. A deployment must author effects and configure the matching verifier; otherwise screen checks remain the oracle. |
| `teach` halt-to-correction loop | **Supported** | The deterministic reference inducer covers the optional-dialog correction class behind regression and canary gates. | Arbitrary UI corrections are not generally learned. Unsafe or underdetermined revisions are refused. |
| Workflow-program IR, branches, loops, and multi-trace induction | **Supported** | Implemented against synthetic fixtures, including refusal for underdetermined programs. | No real recording exercises the full Phase-2 program path yet. |
| Windows UIA backend | **Early access** | The counted `20260717-candidate-56759c8-v2` in-tree WinForms matrix completed 3/3 trials; an independent SQLite oracle confirmed 3/3 effects; stale-target and ambiguous-target controls each refused 3/3; there were 0 silent incorrect successes, 0 over-halts, and 0 model calls. [Review the immutable report at the merged Flow commit](https://github.com/OpenAdaptAI/openadapt-flow/blob/defafbae758a75c8e149d9693f2cffe1f2264b8c/benchmark/windows_uia/results.json) and [Flow PR #132](https://github.com/OpenAdaptAI/openadapt-flow/pull/132). | The report also preserves earlier rejected diagnostic runs; their failures are not counted acceptance trials. Each Windows workflow is qualified in its real environment; the published evidence covers the named workflow and Windows 11 ARM VM snapshot. |
| Native macOS backend | **Early access** | On one macOS 15.7.3 arm64 host, candidate `b1b61a5` completed 3/3 exact-byte TextEdit trials and refused a two-window ambiguity without changing either file; there were 0 silent incorrect successes and 0 over-halts. [Review the hash-bound adjudication at immutable evidence commit `ca1b522`](https://github.com/OpenAdaptAI/openadapt-flow/blob/ca1b522cad215875f7471782283f8f8bb8e6c998/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json) and [Flow PR #135](https://github.com/OpenAdaptAI/openadapt-flow/pull/135). | The counted candidate is `b1b61a5`; `ca1b522` preserves its reports and adjudication but is not the current PR head. The immutable original report remains `status: failed` because graceful-close cleanup warnings were classified as batch failure. The separate adjudication preserves that result, verifies the exact harness PIDs and temporary root were absent, and accepts the action-effect and ambiguity-refusal evidence. Each macOS workflow is qualified in its real environment. |
| RDP backend | **Early access** | On one Parallels Windows 11 VM at 1280x800 with Aardwolf 0.2.14, candidate `82a658a` completed 3/3 trials that created a unique file through the Windows Run dialog over network RDP. Independent guest-tools readback confirmed the exact file contents. Trial latencies were 51.845s, 10.467s, and 7.477s; there were 0 failures, 0 silent incorrect successes, 0 over-halts, and 0 model calls. [Review the immutable sanitized report at evidence commit `6610d24`](https://github.com/OpenAdaptAI/openadapt-flow/blob/6610d24cebba27918b8ea507b2f05a094057ac85/benchmark/rdp/results_82a658a_20260718.sanitized.json) and [Flow PR #142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142). | Cleanup deleted only the batch-owned snapshot, restored the exact eight-snapshot inventory, left the VM suspended, and returned the current pointer without resume to the unchanged original base. Each RDP workflow is qualified in its real environment; the published evidence covers the named task, VM snapshot, transport, and oracle. Earlier rejected batches remain evidence and are not counted as acceptance trials. |
| Citrix / VDI backend | **Exploratory** | The pixel-first mechanism (the same remote-display adapter, identity gate, and effect verification as every substrate) is implemented, but no real Citrix ICA/HDX environment has been qualified yet. | Each Citrix/VDI workflow must be qualified in its real ICA/HDX environment, where the client, latency, compression, DPI, lock-screen, input, identity, and effect behavior are exercised against the actual application, before it carries consequential work. |
| Desktop authoring GUI and tray | **Supported** | The published 0.1.1 prerelease provides install/uninstall-qualified native packages across the six targeted platform/architecture variants. | The current prerelease qualifies packaging and removal; the complete record -> compile -> replay -> teach cockpit remains an integration track. |
| Hosted CLI connectivity | **Supported / public offer** | `login`, exact-hash artifact preparation/upload, one-time runtime validation, bound replacement activation, and `report-break` connect the local engine to the live control plane. | Upload requires destination policy and an approved sanitized derivative; checkout never bypasses an egress refusal. |
| Artifact sanitation and local review | **Supported / launch gate** | The sanitized-derivative pipeline inventories, transforms, rescans, manifests, hashes, and supports local review/approval. | The raw original remains sensitive; unknown or unresolved content is refused; runtime observations can reintroduce PHI/PII. |
| Cross-engine hosted validation | **Supported / launch gate** | `validate-hosted` binds an approved recording and bundle, compiler provenance, strict lint, policy certification, derived risk class, and successful replay report to a one-time Cloud challenge. | It is operator self-attestation signed with the ingest token, not an independently observed certification. Exact deployment policy, risk-class, and deployed compiler-version allowlists still apply. |
| Hosted browser recorder and runtime health | **Supported / bounded launch component** | A non-simulated hosted browser session on `openadapt-flow` 1.8.0 produced PNG frames and retained input evidence, assembled a compileable recording, finalized one workflow idempotently, enforced resource limits, and cleaned up ephemeral qualification data. Authenticated live health probes also qualified the exact-version replay and compiler service identities. | Explicitly initiated, public-HTTPS, non-regulated authoring only. Raw observations remain private inside the declared hosted boundary. Health proves deployed service identity and reachability, not a paid checkout-to-run lifecycle or successful managed replay. |
| Hosted dashboard/control plane | **Supported / public offer** | Authentication, organizations, exact-hash bundle ingest, immutable run admission, browser runner orchestration, structural reports, replacement activation, billing, and metering form the managed lifecycle. | Production uses live dependencies and fails unavailable rather than substituting mock behavior. |
| Hosted execution | **Supported / public offer** | Live Stripe Checkout connects onboarding and subscription entitlements to managed browser execution; the runner verifies exact admitted bundle bytes and authenticated callbacks. | The public subscription covers approved browser workflows. Other substrates use separately scoped deployments and commercial terms. Checkout does not create an SLA or certification. |
| Air-gapped on-prem package | **Supported** | A local queue, systemd unit, minimized hash-chained audit log, and air-gap checks are provided. | Full-disk encryption and operational hardening remain operator/deployment responsibilities. |
| BYOC / customer-controlled execution | **Supported / scoped deployment** | A connector and customer-storage contract support keeping the data plane inside an approved customer boundary. | Qualify the actual substrate and destination; PHI/PII-bearing runtime data must not cross into a shared boundary. |
| Hosted desktop runner | **Supported** | A Windows runner contract and implementation path exist. | Desktop subscriptions and deployments are scoped separately from the public browser offer and qualified per workflow. |

## Before using consequential data

Treat the matrix as a starting point, not an authorization. For each workflow:

1. Inspect `lint` findings and identity-armed coverage.
2. Review every risk classification and write-shaped action.
3. Declare effects and configure an independent verifier where a real system of
   record exists.
4. Certify against a workload-specific policy.
5. Exercise expected drift and failure cases with repeated trials.
6. Review the PHI/PII boundary, storage encryption, logs, model egress, updates,
   rollback, and operator approval design.
7. If an artifact crosses a boundary, inspect its sanitation manifest and
   approve the exact derivative hash required by policy.

The complete, evidence-linked failure inventory is maintained in
[`openadapt-flow/docs/LIMITS.md`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).
