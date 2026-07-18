# What works today

OpenAdapt compiles demonstrated GUI workflows into deterministic, locally
executable programs. Healthy runs make no model calls. When an interface
drifts, the runtime can re-resolve a target deterministically or use an
explicitly configured model tier; it records any repair and halts when the
configured identity, postcondition, effect, or policy checks cannot verify the
run.

That is the canonical product description. A bounded hosted recorder has passed
a live-provider record-to-compile qualification for public, non-regulated
browser targets. The complete paid account-to-run lifecycle remains a **Beta
launch candidate** pending production acceptance. That does **not** mean every
recorded workflow is safe or every backend is production-ready.

## Maturity labels

| Label | Meaning |
|---|---|
| **Beta** | Implemented and exercised end to end in the stated environment, but still requires workload-specific validation. Public delivery may have a separate production-qualification gate. |
| **Experimental** | Implemented and tested in a bounded environment; interfaces or operating assumptions may change. |
| **Research spike** | Demonstrates an adapter or mechanism, usually with mocks or an analog environment; not a validated integration. |
| **Prototype** | Code or a deployment scaffold exists, but required production controls are incomplete. |
| **Target-state** | Designed or planned; do not treat it as available. |
| **Deprecated** | Kept for compatibility or history; do not build new integrations on it. |

No surface is labelled **Stable** yet.

Buyer-facing availability is narrower than these engineering lifecycle labels
and is reported distinctly from evidence. **Partner qualification** means teams
may apply to qualify one exact workflow, not that access or acceptance is
already granted. **Design partner needed** means OpenAdapt needs the customer's
real environment before any support claim can be made.

## Integrated product matrix

| Surface | Status | What is actually demonstrated | Important boundary |
|---|---|---|---|
| `openadapt` installer and `openadapt flow` dispatcher | **Beta** | Installs the compiler and exposes the unified command surface. | The standalone `openadapt-flow` package remains the canonical engine and may be installed directly. |
| Record -> compile -> lint -> certify -> replay -> report on a browser | **Beta / reference path** | Runs end to end in CI against the bundled app; the browser path is also the only backend exercised end to end against a real third-party app. | A clean run is not automatically safe. Identity coverage, risk classification, postconditions, and effect contracts must be audited per bundle. |
| Deterministic target re-resolution and saved heal diffs | **Beta on the reference path** | Theme, movement, and rename drift are covered by the bundled drift matrix. | Scale/reflow and tenant-specific state can still halt. The base bundle is not silently promoted; save and review a healed bundle explicitly. |
| `lint` and `certify` | **Beta** | Report coverage gaps and refuse bundles that violate the selected policy. | Certification is opt-in and only enforces what the policy names. An uncertified bundle remains runnable with `replay`. |
| Fail-closed `run` admission gate | **Experimental** | The shipped gate checks certification, identity/effect coverage, approval fallback, encryption, and manifest integrity before executing. | Development escape hatches exist, and passing the gate does not validate the backend or prove a workflow safe. |
| Identity verification | **Experimental, opt-in by step coverage** | Structured identity works on armed browser steps; UIA and pixel/OCR tiers are implemented and adversarially tested. | Unarmed clicks have no identity check. Pure-pixel ambiguity intentionally over-halts, and coverage varies by workflow. |
| System-of-record effect verification | **Experimental** | REST, FHIR, and document-hash verifiers run in the live replay path and halt on refuted or indeterminate declared effects. | The compiler does not infer effects. A deployment must author effects and configure the matching verifier; otherwise screen checks remain the oracle. |
| `teach` halt-to-correction loop | **Experimental** | The deterministic reference inducer covers the optional-dialog correction class behind regression and canary gates. | Arbitrary UI corrections are not generally learned. Unsafe or underdetermined revisions are refused. |
| Workflow-program IR, branches, loops, and multi-trace induction | **Experimental** | Implemented against synthetic fixtures, including refusal for underdetermined programs. | No real recording exercises the full Phase-2 program path yet. |
| Windows UIA backend | **Partner qualification; scoped acceptance passed** | The counted `20260717-candidate-56759c8-v2` in-tree WinForms matrix completed 3/3 trials; an independent SQLite oracle confirmed 3/3 effects; stale-target and ambiguous-target controls each refused 3/3; there were 0 silent incorrect successes, 0 over-halts, and 0 model calls. [Review the immutable report at the merged Flow commit](https://github.com/OpenAdaptAI/openadapt-flow/blob/defafbae758a75c8e149d9693f2cffe1f2264b8c/benchmark/windows_uia/results.json) and [Flow PR #132](https://github.com/OpenAdaptAI/openadapt-flow/pull/132). | The report also preserves earlier rejected diagnostic runs; their failures are not counted acceptance trials. The result qualifies only the named workflow and Windows 11 ARM VM snapshot, not arbitrary Windows applications, clean-machine support, or hosted desktop availability. |
| Native macOS backend | **Partner qualification; scoped TextEdit evidence accepted** | On one macOS 15.7.3 arm64 host, candidate `b1b61a5` completed 3/3 exact-byte TextEdit trials and refused a two-window ambiguity without changing either file; there were 0 silent incorrect successes and 0 over-halts. [Review the hash-bound adjudication at immutable evidence commit `ca1b522`](https://github.com/OpenAdaptAI/openadapt-flow/blob/ca1b522cad215875f7471782283f8f8bb8e6c998/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json) and [Flow PR #135](https://github.com/OpenAdaptAI/openadapt-flow/pull/135). | The counted candidate is `b1b61a5`; `ca1b522` preserves its reports and adjudication but is not the current PR head. The immutable original report remains `status: failed` because graceful-close cleanup warnings were classified as batch failure. The separate adjudication preserves that result, verifies the exact harness PIDs and temporary root were absent, and accepts only the action-effect and ambiguity-refusal evidence. This is not clean-machine, design-partner, production, broad-app, or general macOS acceptance evidence. |
| RDP backend | **Partner qualification; scoped RDP evidence accepted** | On one Parallels Windows 11 VM at 1280x800 with Aardwolf 0.2.14, candidate `82a658a` completed 3/3 trials that created a unique file through the Windows Run dialog over network RDP. Independent guest-tools readback confirmed the exact file contents. Trial latencies were 51.845s, 10.467s, and 7.477s; there were 0 failures, 0 silent incorrect successes, 0 over-halts, and 0 model calls. [Review the immutable sanitized report at evidence commit `6610d24`](https://github.com/OpenAdaptAI/openadapt-flow/blob/6610d24cebba27918b8ea507b2f05a094057ac85/benchmark/rdp/results_82a658a_20260718.sanitized.json) and [Flow PR #142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142). | Cleanup deleted only the batch-owned snapshot, restored the exact eight-snapshot inventory, left the VM suspended, and returned the current pointer without resume to the unchanged original base. This qualifies only the named task, VM snapshot, transport, and oracle—not arbitrary RDP applications, record-level identity, clean-machine or production support, hosted RDP, or Citrix ICA/HDX. Earlier rejected batches remain evidence and are not counted as acceptance trials. |
| Citrix backend | **Design partner needed; no ICA/HDX evidence** | The generic remote-window safety floor can begin qualification. | There is no validated Citrix integration. The actual client, latency, compression, DPI, lock-screen, input, identity, and effect behavior require a partner environment. |
| Desktop authoring GUI and tray | **Experimental** | Native artifacts for the targeted platforms and their tag-gated release pipeline have been built and qualified; the surfaces follow the record -> compile -> replay -> teach loop. | No complete native prerelease is published yet. Signing, permissions, updater behavior, and the full operator lifecycle still require platform validation. |
| Hosted CLI connectivity | **Beta / launch component** | `login`, exact-hash artifact preparation/upload, one-time runtime validation, bound replacement activation, and `report-break` connect the local engine to control-plane endpoints. | Upload requires destination policy and an approved sanitized derivative; checkout never bypasses an egress refusal. Public paid acceptance remains pending. |
| Artifact sanitation and local review | **Beta / launch gate** | The sanitized-derivative pipeline inventories, transforms, rescans, manifests, hashes, and supports local review/approval. | The raw original remains sensitive; unknown or unresolved content is refused; runtime observations can reintroduce PHI. |
| Cross-engine hosted validation | **Beta / launch gate** | `validate-hosted` binds an approved recording and bundle, compiler provenance, strict lint, policy certification, derived risk class, and successful replay report to a one-time Cloud challenge. | It is operator self-attestation signed with the ingest token, not an independently observed certification. Exact deployment policy, risk-class, and deployed compiler-version allowlists still apply. |
| Hosted browser recorder and runtime health | **Beta / bounded launch component** | A non-simulated Modal session on `openadapt-flow` 1.8.0 produced PNG frames and retained input evidence, assembled a compileable recording, finalized one workflow idempotently, enforced resource limits, and cleaned up ephemeral qualification data. Authenticated live health probes also qualified the exact-version replay and compiler service identities. | Explicitly initiated, public-HTTPS, non-regulated authoring only. Raw observations remain private inside the declared hosted boundary. Health proves deployed service identity and reachability, not a paid checkout-to-run lifecycle or successful managed replay. |
| Hosted dashboard/control plane | **Beta launch candidate** | Authentication, organizations, exact-hash bundle ingest, immutable run admission, browser runner orchestration, structural reports, replacement activation, billing, and metering form the candidate launch lifecycle. | Local governed authoring and repair remain available. Production must explicitly use live dependencies; mock mode remains visibly synthetic development behavior. The current paid lifecycle has not passed clean-account acceptance. |
| Hosted execution | **Beta launch candidate** | The implementation routes Stripe Checkout through onboarding to managed browser execution; the runner verifies exact admitted bundle bytes and callbacks. | This is not yet a public availability claim. The configured offer covers browser workflows, not Windows, RDP, or Citrix by implication. Checkout does not create an SLA or certification. The full paid production lifecycle remains pending. |
| Air-gapped on-prem package | **Experimental** | A local queue, systemd unit, minimized hash-chained audit log, and air-gap checks are provided. | Full-disk encryption and operational hardening remain operator/deployment responsibilities. |
| BYOC / customer-controlled execution | **Experimental / scoped deployment** | A connector and customer-storage contract support keeping the data plane inside an approved customer boundary. | Qualify the actual substrate and destination; PHI-bearing runtime data must not cross into a shared boundary. |
| Hosted desktop runner | **Experimental** | A Windows runner contract and implementation path exist. | Not included in the browser launch candidate and not a validated broad desktop/Citrix service. |

## Before using consequential data

Treat the matrix as a starting point, not an authorization. For each workflow:

1. Inspect `lint` findings and identity-armed coverage.
2. Review every risk classification and write-shaped action.
3. Declare effects and configure an independent verifier where a real system of
   record exists.
4. Certify against a workload-specific policy.
5. Exercise expected drift and failure cases with repeated trials.
6. Review the PHI boundary, storage encryption, logs, model egress, updates,
   rollback, and operator approval design.
7. If an artifact crosses a boundary, inspect its sanitation manifest and
   approve the exact derivative hash required by policy.

The complete, evidence-linked failure inventory is maintained in
[`openadapt-flow/docs/LIMITS.md`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).
