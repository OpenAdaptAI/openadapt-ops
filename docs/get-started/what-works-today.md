# What works today

OpenAdapt compiles demonstrated GUI workflows into deterministic, locally
executable programs. Healthy runs make no model calls. When an interface
drifts, the runtime can re-resolve a target deterministically or use an
explicitly configured model tier; it records any repair and halts when the
configured identity, postcondition, effect, or policy checks cannot verify the
run.

That is the canonical product description. Hosted browser execution is
launching now, but that does **not** mean every recorded workflow is safe or
every backend is production-ready.

## Maturity labels

| Label | Meaning |
|---|---|
| **Beta** | Shipped and exercised end to end, but still requires workload-specific validation before consequential use. |
| **Experimental** | Implemented and tested in a bounded environment; interfaces or operating assumptions may change. |
| **Research spike** | Demonstrates an adapter or mechanism, usually with mocks or an analog environment; not a validated integration. |
| **Prototype** | Code or a deployment scaffold exists, but required production controls are incomplete. |
| **Target-state** | Designed or planned; do not treat it as available. |
| **Deprecated** | Kept for compatibility or history; do not build new integrations on it. |

No surface is labelled **Stable** yet.

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
| Windows UIA backend | **Experimental** | A local Windows-on-ARM VM demonstrated record -> compile -> replay and database-ground-truth checking; adapter tests run against mocks. | Evidence is small-N and not a native-x86 or broad application study. |
| Native macOS backend | **Target-state** | macOS capture/input primitives exist for the remote-display analog harness. | There is no validated native macOS AX backend integration today. |
| RDP backend | **Research spike** | The adapter conforms to the backend protocol and is mock/offline tested. | No published live RDP validation establishes latency, coordinate, input, identity, or effect behavior. |
| Citrix backend | **Research spike** | A pixel-only remote-display analog was exercised against a VM window. | It is **not** a validated Citrix/ICA/HDX integration. Real latency, compression, DPI, lock screens, input acceptance, and clinical identity behavior remain unmeasured. |
| Desktop authoring GUI and tray | **Experimental** | The desktop and tray surfaces are aligned to the record -> compile -> replay -> teach loop. | Installer, updater, permissions, and full operator lifecycle still require platform validation. |
| Hosted CLI connectivity | **Beta / launch path** | `login`, exact-hash artifact preparation/upload, one-time runtime validation, bound replacement activation, and `report-break` connect the local engine to control-plane endpoints. | Upload requires destination policy and an approved sanitized derivative; checkout never bypasses an egress refusal. Production provider qualification remains pending. |
| Artifact sanitation and local review | **Beta / launch gate** | The sanitized-derivative pipeline inventories, transforms, rescans, manifests, hashes, and supports local review/approval. | The raw original remains sensitive; unknown or unresolved content is refused; runtime observations can reintroduce PHI. |
| Cross-engine hosted validation | **Beta / launch gate** | `validate-hosted` binds an approved recording and bundle, compiler provenance, strict lint, policy certification, derived risk class, and successful replay report to a one-time Cloud challenge. | It is operator self-attestation signed with the ingest token, not an independently observed certification. Exact deployment policy, risk-class, and deployed compiler-version allowlists still apply. |
| Hosted dashboard/control plane | **Beta / browser launch** | Authentication, organizations, exact-hash bundle ingest, immutable run admission, browser runner orchestration, structural reports, replacement activation, billing, and metering form the launch lifecycle. | Authoring and repair validation remain local. Production must explicitly use live dependencies; mock mode remains visibly synthetic development behavior. |
| Hosted execution | **Beta / browser launch** | Stripe Checkout routes subscriptions into onboarding for managed browser execution; the runner verifies exact admitted bundle bytes and callbacks. | The configured offer covers browser workflows, not Windows, RDP, or Citrix by implication. Checkout does not create an SLA or certification. Production provider qualification remains pending. |
| Air-gapped on-prem package | **Experimental** | A local queue, systemd unit, minimized hash-chained audit log, and air-gap checks are provided. | Full-disk encryption and operational hardening remain operator/deployment responsibilities. |
| BYOC / customer-controlled execution | **Experimental / scoped deployment** | A connector and customer-storage contract support keeping the data plane inside an approved customer boundary. | Qualify the actual substrate and destination; PHI-bearing runtime data must not cross into a shared boundary. |
| Hosted desktop runner | **Experimental** | A Windows runner contract and implementation path exist. | Not included in the launched browser offer and not a validated broad desktop/Citrix service. |

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
