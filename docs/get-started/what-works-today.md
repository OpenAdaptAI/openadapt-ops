---
description: >-
  Inspect OpenAdapt qualification evidence by exact workflow, application,
  environment, run count, effect oracle, refusal case, and execution surface.
---

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

Every substrate below is implemented in the released compiler and governed
runtime. The Status column describes product availability; the "What is actually
demonstrated" and "Important boundary" columns separately record the exact
bounded evidence. Availability never turns one fixture or qualification batch
into a broad application-support claim. Before consequential use, qualify the
exact workflow, application, environment, identity contract, effect oracle, and
deployment boundary.

The [interactive status viewer](https://openadapt.ai/artifacts/json?source=%2Fstatus.json)
presents the same release, availability, evidence, and deployment dimensions;
the [raw JSON](https://openadapt.ai/status.json) remains available for tools.
For a visual tour, the [OpenAdapt website](https://openadapt.ai/how-it-works) and
[public Cloud demo](https://app.openadapt.ai/demo#footage) share the same real
application choices and presentation vocabulary: **Recorded demonstration**,
outcome-bound **Verified replay**, exact retained **Fail-safe halt** footage
where available, and **Guided view** versus immutable **Raw footage**. Guided
targets are bound to an exact decoded frame rather than inferred by the viewer.
Cloud then adds the openIMIS graph, contracts, six Standard-profile results, and
byte-inventoried evidence links; media is never presented as proof by itself.
The public managed runner executes approved browser workflows. Native desktop,
RDP, and Citrix/VDI workflows execute locally or in a self-hosted or
customer-controlled runtime connected to the same governance model.

## Integrated product matrix

| Surface | Status | What is actually demonstrated | Important boundary |
|---|---|---|---|
| `openadapt` installer and `openadapt flow` dispatcher | **Supported** | Installs the compiler and exposes the unified command surface. | The standalone `openadapt-flow` package remains the canonical engine and may be installed directly. |
| Record -> compile -> lint -> certify -> replay -> report on a browser | **Supported** | Runs end to end in CI against the bundled app and end to end against a real third-party app. The local attach recorder also passes 3 real Chromium record-and-compile trials with source-time password exclusion and external-browser survival checks. | A clean run is not automatically safe. Identity coverage, risk classification, postconditions, and effect contracts must be audited per bundle. Attach mode is loopback-only Chromium and requires a dedicated browser process started with remote debugging. The custom Capture extension remains a prototype. |
| Deterministic target re-resolution and saved heal diffs | **Supported** | Theme, movement, and rename drift are covered by the bundled drift matrix. | Scale/reflow and tenant-specific state can still halt. The base bundle is not silently promoted; save and review a healed bundle explicitly. |
| `lint` and `certify` | **Supported** | Report coverage gaps and refuse bundles that violate the selected policy. | Certification is opt-in and only enforces what the policy names. An uncertified bundle remains runnable with `replay`. |
| Fail-closed `run` admission gate | **Supported** | The shipped gate checks certification, identity/effect coverage, approval fallback, encryption, and manifest integrity before executing. | Development escape hatches exist, and passing the gate does not validate the backend or prove a workflow safe. |
| Identity verification | **Supported, opt-in by step coverage** | Structured identity works on armed browser steps; UIA and pixel/OCR tiers are implemented and adversarially tested. | Unarmed clicks have no identity check. Pure-pixel ambiguity intentionally over-halts, and coverage varies by workflow. |
| System-of-record effect verification | **Supported** | REST, FHIR, and document-hash verifiers run in the live replay path and halt on refuted or indeterminate declared effects. | The compiler does not infer effects. A deployment must author effects and configure the matching verifier; otherwise screen checks remain the oracle. |
| `teach` halt-to-correction loop | **Supported** | The deterministic reference inducer covers the optional-dialog correction class behind regression and canary gates. | Arbitrary UI corrections are not generally learned. Unsafe or underdetermined revisions are refused. |
| Workflow-program IR, branches, loops, and multi-trace induction | **Supported** | Implemented against synthetic fixtures, including refusal for underdetermined programs. | No real recording exercises the full Phase-2 program path yet. |
| Windows UIA backend | **Supported** | The counted `20260717-candidate-56759c8-v2` in-tree WinForms matrix completed 3/3 trials; an independent SQLite oracle confirmed 3/3 effects; stale-target and ambiguous-target controls each refused 3/3; there were 0 silent incorrect successes, 0 over-halts, and 0 model calls. The native authoring handoff now retains Capture 1.1 action-time UIA observations and compiles the nearest actionable node, including window-scoped recordings. Review the [immutable qualification report](https://github.com/OpenAdaptAI/openadapt-flow/blob/defafbae758a75c8e149d9693f2cffe1f2264b8c/benchmark/windows_uia/results.json), [Flow PR #132](https://github.com/OpenAdaptAI/openadapt-flow/pull/132), and the [capture-to-compiler contract in Flow PR #239](https://github.com/OpenAdaptAI/openadapt-flow/pull/239). | The qualification report preserves earlier rejected diagnostic runs; their failures are not counted acceptance trials. The UIA handoff contract covers `recording.db -> CaptureSession -> convert -> compile`, not a new arbitrary-app reliability matrix. RDP and Citrix recordings suppress local client UIA and remain pixel-only. Each Windows workflow is qualified in its real environment; the published task evidence covers the named workflow and Windows 11 ARM VM snapshot. |
| Native macOS backend | **Supported** | On one macOS 15.7.3 arm64 host, candidate `b1b61a5` completed 3/3 exact-byte TextEdit trials and refused a two-window ambiguity without changing either file; there were 0 silent incorrect successes and 0 over-halts. [Review the hash-bound adjudication at immutable evidence commit `ca1b522`](https://github.com/OpenAdaptAI/openadapt-flow/blob/ca1b522cad215875f7471782283f8f8bb8e6c998/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json) and [Flow PR #135](https://github.com/OpenAdaptAI/openadapt-flow/pull/135). | The counted candidate is `b1b61a5`; `ca1b522` preserves its reports and adjudication but is not the current PR head. The immutable original report remains `status: failed` because graceful-close cleanup warnings were classified as batch failure. The separate adjudication preserves that result, verifies the exact harness PIDs and temporary root were absent, and accepts the action-effect and ambiguity-refusal evidence. Each macOS workflow is qualified in its real environment. |
| Native Linux backend | **Supported** | Required current-main job [`linux-atspi-x11`](https://github.com/OpenAdaptAI/openadapt-flow/actions/runs/30059807758/job/89378981573) at exact Flow commit `3de5fc67acf3024a621f812c5a6ed9be07fac335` ran one fresh GTK3 process per trial on Ubuntu 24.04 X11/AT-SPI. It confirmed 3/3 exact-file effects, 3/3 ambiguous-target refusals, and 3/3 stale-target refusals, with 0 silent incorrect successes, 0 over-halts, 0 operator interventions, and 0 model calls. | Native receipts prove AT-SPI delivery only; independent exact file bytes or confirmed absence prove effects. This is bounded to the in-tree GTK3 fixture and CI Xvfb image; it does not establish Wayland or arbitrary third-party application support. |
| RDP backend | **Supported** | Two bounded results exercise complementary RDP paths. Aardwolf 0.2.14 over a Parallels Windows 11 VM completed 3/3 Windows Run-dialog file effects with independent guest-tools readback. The accepted full governed lifecycle at mechanism commit `6031fde` recorded, compiled, and replayed a synthetic note workflow through real FreeRDP3-transported pixels/input: 3/3 healthy effects and 3/3 drift safe-halts, with zero model calls, silent incorrect successes, false completions, drift writes, or healthy over-halts. Consequential remote actions now acquire a fresh frame, re-resolve target and identity, and use a one-shot input lease that refuses changed session context, pixels, dimensions, or readiness before delivery. Review the [Aardwolf/Windows report](https://github.com/OpenAdaptAI/openadapt-flow/blob/6610d24cebba27918b8ea507b2f05a094057ac85/benchmark/rdp/results_82a658a_20260718.sanitized.json), the [FreeRDP lifecycle report](https://github.com/OpenAdaptAI/openadapt-flow/blob/affedc5f1f0de533a0744deaa8e30a203c91c6b3/benchmark/rdp_ladder/results.json), [Flow PR #142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142), [Flow PR #177](https://github.com/OpenAdaptAI/openadapt-flow/pull/177), and [Flow PR #238](https://github.com/OpenAdaptAI/openadapt-flow/pull/238). | The Windows batch qualifies its exact task, snapshot, transport, and oracle. The FreeRDP batch qualifies a synthetic Linux Tk task over a real RDP round trip; it is not Aardwolf, a Windows-app qualification, Citrix ICA/HDX, or WAN-captured drift. The two-phase mechanism is separately covered by runtime and backend refusal tests; it does not enlarge those bounded application results. |
| Citrix / VDI backend | **Supported** | The dedicated `--backend citrix` path selects the exact Citrix Workspace/Viewer owner, optionally binds an exact title, requires a readiness marker for governed `run`, carries the closed target into durable resume, and uses the shared pixel identity, effect, policy, and halt contracts. Consequential input reacquires the exact client window, focus, geometry, readiness, fresh pixels, resolved target, and record identity, then refuses any change before the first input edge. The accepted no-DOM qualification completed 3/3 healthy effects and 3/3 severe-drift safe-halts with 0 model calls, silent incorrect successes, false completions, healthy over-halts, or drift writes. Review the [immutable report](https://github.com/OpenAdaptAI/openadapt-flow/blob/f6faac5b900b78cbda5980de0e983a9f987285ac/benchmark/citrix_workspace/results.json), [Flow PR #183](https://github.com/OpenAdaptAI/openadapt-flow/pull/183), and [Flow PR #238](https://github.com/OpenAdaptAI/openadapt-flow/pull/238). | The accepted artifact explicitly records `code_readiness_accepted: true` and `ica_hdx_accepted: false`. It qualifies the shipped Citrix Workspace-window backend contract over a no-DOM canvas stand-in, not a counted real ICA/HDX batch. The exact ICA/HDX client, codec, latency, DPI, lock/readiness, input, identity, and effect matrix is a separate per-deployment qualification boundary. |
| Desktop authoring GUI and tray | **Supported / Beta** | Public `desktop-v0.15.0` provides Windows MSI/NSIS, macOS arm64/x64 DMG, and Linux AppImage/DEB installers. All six installer paths were installed, launched, and uninstalled in the native release workflow; the release includes `SHA256SUMS`, a CycloneDX SBOM, per-platform metadata, and build-provenance attestations. | Windows/Linux remain unsigned and macOS is ad-hoc signed, so verify checksums and provenance before overriding the OS publisher warning. The app and CLI drive the same released compiler/runtime. |
| Hosted CLI connectivity | **Supported / public offer** | `login`, exact-hash artifact preparation/upload, one-time runtime validation, bound replacement activation, and `report-break` connect the local engine to the live control plane. | Upload requires destination policy and an approved sanitized derivative; checkout never bypasses an egress refusal. |
| Artifact sanitation and local review | **Supported / launch gate** | The sanitized-derivative pipeline inventories, transforms, rescans, manifests, hashes, and supports local review/approval. | The raw original remains sensitive; unknown or unresolved content is refused; runtime observations can reintroduce PHI/PII. |
| Cross-engine hosted validation | **Supported / launch gate** | `validate-hosted` binds an approved recording and bundle, compiler provenance, strict lint, policy certification, derived risk class, and successful replay report to a one-time Cloud challenge. | It is operator self-attestation signed with the ingest token, not an independently observed certification. Exact deployment policy, risk-class, and deployed compiler-version allowlists still apply. |
| Hosted browser recorder and runtime health | **Supported / bounded launch component** | A retained non-simulated hosted session on `openadapt-flow` 1.8.0 produced frames and input evidence, assembled a compileable recording, finalized one workflow idempotently, enforced resource limits, and cleaned up ephemeral qualification data. The current managed-runtime manifest pins the Flow 1.31.0 runner/compiler artifact identity. Authenticated live health separately checks live mode, auth, database, storage, runner, compiler, runtime-validation trust, runtime boundary, bundle protection, recorder, callbacks, scheduler, human-decision Web Push, retention, security events, secrets, validation policy, and billing. | Explicitly initiated, public-HTTPS, non-regulated authoring only. Raw observations remain private inside the declared hosted boundary. A runtime pin does not prove live deployment or hosted acceptance. Readiness proves deployed dependencies and service identity, not a customer workflow qualification or SLA. |
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
