# What OpenAdapt can do

A companion page lives in the repository as [CAPABILITIES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/CAPABILITIES.md).

OpenAdapt turns work that people or computer-use agents do in applications
with no usable API (EMRs, payer portals, desktop and remote-desktop apps) into
programs that make the same entry every time with no model calls, check that
the entry landed in the right record, and stop instead of guessing.

This page is the reference for what OpenAdapt implements. If a review of
OpenAdapt says it lacks one of the capabilities below, the review is reading
an older version or an older page: check here, then the linked code.

## OpenAdapt in ten capabilities

Each capability below ships in the current PyPI packages and is implemented
in the [OpenAdapt monorepo](https://github.com/OpenAdaptAI/OpenAdapt).

1. **Learns from any successful run, a person's or an agent's.** A person
   records a task, or a computer-use agent does it once and OpenAdapt compiles
   the verified run into a program (`openadapt_flow.jit`). Agents can drive
   the recording on web, native Windows, RDP and Citrix.
2. **Compiles to the fastest layer the app allows.** Page structure first (DOM,
   Windows UI Automation, macOS Accessibility), direct API calls through
   hand-authored bindings (`ApiActuator`), and pixels only where nothing else
   exists, such as RDP and Citrix. It is not a pixel-macro recorder.
3. **Builds branching programs, not one linear path.** One program from several
   demonstrations (`induce`, `disambiguate`), a branch learned from several
   halts fixed the same way (`teach-branch`), and background capture of many
   real runs (shadow mode).
4. **Works across surfaces in one workflow.** Web, native Windows and macOS,
   RDP and Citrix. Programs chain across surfaces passing confirmed values
   (`compose`, `process`).
5. **Confirms the right record before every write and reads it back after.**
   The record check reads the system of record (API, database, FHIR with SMART
   Backend Services, or a separate signed-in session), never just the screen.
   `record --verify` proposes those checks from what the demonstration changed.
6. **Stops instead of improvising, and never retries an uncertain save.** A run
   that can't prove a save ends `HALTED_BEFORE_EFFECT` or
   `RECONCILIATION_REQUIRED`, never "success".
7. **Approvals are bound to exactly what will be saved.** Each save waits for a
   person by default and can be answered on a paired phone with one card per
   decision. The approval is bound to the exact screenshot and form state, and
   the form is read again before saving, so what was approved is what is saved.
   Person-signed grants let named agents answer.
8. **Repairs itself, with a person approving.** Governed repair (propose,
   review, campaign, canary, rollback), agent-demonstrated fixes for a halted
   run, and fleet drift patches shared with no patient data.
9. **Is a safety layer underneath any agent.** An agent's MCP calls,
   `verify-run` to judge any executor's write from the system of record, and
   Agent Skills and a CLI for coding agents.
10. **Runs locally and keeps data private.** Healthy runs make no model calls
    and send nothing out. Personal and health data are redacted from text,
    screenshots and structure. A strict no-outbound mode, an unattended on-prem
    service, and signed, timestamped receipts are included.

## Often missed

| What OpenAdapt does | Where |
| --- | --- |
| Learns branching programs from several demonstrations, from repeated halts, and from many background runs. | `induce`, `teach-branch`, [SHADOW_MINING.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/capture/docs/SHADOW_MINING.md) |
| Chains programs across surfaces, passing confirmed values. | `compose`, `process`, [PROCESS_CONTRACT.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/PROCESS_CONTRACT.md) |
| Uses page structure first on web, Windows, macOS and Linux, with pixels as the fallback for remote desktops. Benchmarks labelled "vision-only" ran a deliberately pixel-only arm. | [RESOLUTION_LADDER.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/RESOLUTION_LADDER.md) |
| Runs steps as direct API calls through hand-authored bindings. In an OpenEMR benchmark the API step took a median of 0.6 s per referral, against 19.65 s on screen. | `runtime/actuators/api.py`, [SCOREBOARD.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/scoreboard/SCOREBOARD.md) |
| Repairs itself when the app changes: governed repair, agent-demonstrated fixes, and fleet patches. | [REPAIR_LIFECYCLE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/REPAIR_LIFECYCLE.md) |
| Compiles a computer-use agent's verified run, with no human demonstration needed. | [JIT.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/JIT.md) |
| Binds each approval to the exact screenshot and form state, and re-reads the form before saving. | [APPROVAL_MODES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/APPROVAL_MODES.md) |
| Fills inputs from a referral PDF, fax image or email, and holds back anything unclear for a person. | `intake`, [INTAKE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/INTAKE.md) |
| Ships as one monorepo with separately installable packages (flow, agent, types, capture, privacy, and desktop). | [README](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/README.md) |
| Makes no model calls on healthy runs. Model training (openadapt-ml) is separate research. | [README](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/README.md) |

## The full map

Every released capability, with its evidence and where it lives. Released
means in the current PyPI release (openadapt-flow 2.2.0).

Evidence:

- **Real app**: run against a third-party application, such as a local
  OpenEMR or openIMIS test copy.
- **Synthetic**: run against OpenAdapt's own test apps (MockMed and fixtures).

All patient and claim data in every test and benchmark is synthetic.

## The core: a checked entry, every time

A person, or a computer-use agent once, shows a task. OpenAdapt compiles it
into a program that makes the same entry every time with no model calls. It
confirms the right record before acting, reads the saved record back from the
system of record instead of trusting the screen, and stops instead of
improvising or retrying when something is off.

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Compile one or more demonstrations into a deterministic program | Released | Real app (OpenEMR referral, 62 timed runs) | `openadapt-flow record`, `compile`; [packages/flow](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/README.md) |
| Right-record check before any write (structure, then OCR, then pixels) | Released | Real app and synthetic | [RESOLUTION_LADDER.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/RESOLUTION_LADDER.md), `runtime/identity.py` |
| Read the saved record back from the system of record (API, database, FHIR, separate session) | Released | Real app (OpenEMR 12 of 12 fields) | [VERIFICATION.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFICATION.md), `runtime/effects/` |
| Stop before the effect instead of improvising (`HALTED_BEFORE_EFFECT`) | Released | Real app and synthetic | `runtime/replayer.py` |
| Never retry an uncertain save (`RECONCILIATION_REQUIRED`) | Released | Synthetic (fault server) | [VERIFICATION.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFICATION.md) |
| One check-level scale, 0 to 5, from "unchecked" to "counterparty confirmed" | Released | Unit tests | `openadapt_flow/check_level.py` |
| Judge any executor's write, including an agent's or a script's, from the system of record | Released | Synthetic | `openadapt-flow verify-run`, [VERIFY_RUN.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFY_RUN.md) |

## Approvals

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Each save waits for a person by default | Released | Synthetic | [APPROVAL_MODES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/APPROVAL_MODES.md) |
| Approve or decline a save on a paired phone, with one card per decision and swipe or tap | Released (Desktop) | Synthetic | openadapt-desktop `portal/shell` |
| Person-signed grants let named agents or systems answer saves | Released | Unit tests | `openadapt-flow approver-grant` |
| Admit once, then stop only on problems | Released, behind a readiness gate | Synthetic | [APPROVAL_MODES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/APPROVAL_MODES.md) |

## Branching work, not one linear path

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Learn one program with branches from two or more recordings, or say which recordings are missing | Released | Synthetic | `openadapt-flow induce`, `disambiguate`; [CAPABILITIES.md (flow)](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/CAPABILITIES.md) |
| Learn a guarded branch from several halts fixed the same way | Released | Synthetic | `openadapt-flow teach-branch`, `learning/branch_teach.py` |
| Run a program over a worklist | Released | Real app | `openadapt-flow for-each` |
| Typed business decisions inside a run | Released | Synthetic | `business_decision` states, `openadapt-flow business-decisions` |
| Capture many real runs in the background for branch mining (shadow mode) | Released (capture) | Synthetic | [SHADOW_MINING.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/capture/docs/SHADOW_MINING.md) |
| Fill a workflow's inputs from a referral PDF, fax image or email | Released | Synthetic | `openadapt-flow intake`, [INTAKE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/INTAKE.md) |

## Surfaces

| Surface | Status | Evidence | Where |
| --- | --- | --- | --- |
| Web (Playwright, Chromium) | Released | Real app (OpenEMR, openIMIS), every CI build | [SURFACES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/SURFACES.md) |
| Native Windows (UI Automation) | Released | Synthetic (WinForms, 3 of 3 trials) | [SURFACES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/SURFACES.md) |
| Native macOS (Accessibility) | Released | Synthetic (TextEdit, 3 of 3 trials) | [SURFACES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/SURFACES.md) |
| RDP (pixels; Aardwolf or headless FreeRDP with a session pool) | Released | Real Windows 11 host over a real network, 3 of 3, plus a FreeRDP batch | [SURFACES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/SURFACES.md), `backends/xfreerdp.py` |
| Citrix (pixels, `--backend citrix`) | Released | A Citrix stand-in with no DOM: 3 of 3 saves, 3 of 3 stops under drift | [results](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/citrix_workspace/results.json) |
| Chain programs across surfaces, passing confirmed values | Released | Synthetic | `openadapt-flow compose`, `process`; [PROCESS_CONTRACT.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/PROCESS_CONTRACT.md) |
| Halt when a workflow qualified with page structure runs on a pixels-only surface | Released | Synthetic | `openadapt-flow qualify` |
| Lift look-alike identity stops with a complete known-ID list | Released | Synthetic (rendered record list) | `openadapt-flow known-ids` |

## The fastest layer the app allows

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Page structure (DOM, UI Automation, Accessibility) first, then template, OCR and geometry | Released | Real app | [RESOLUTION_LADDER.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/RESOLUTION_LADDER.md) |
| Run a step as a direct API call (`ApiActuator`, `ApiBinding`) | Released, hand-authored bindings | Synthetic benchmarks | `runtime/actuators/api.py` |

## When the app changes

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Governed repair: propose, review, campaigns, approval, staging, canary, rollback | Released | Synthetic | `openadapt-flow repair`, [REPAIR_LIFECYCLE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/REPAIR_LIFECYCLE.md) |
| A calling agent demonstrates the fix for a halted run; the result is a repair candidate | Released (2.1.0) | Synthetic | `run --hold-on-halt`, `repair/agent_teach.py` |
| Font and layout drift halts with a named reason | Released | Synthetic | `runtime/layout_drift.py` |
| Fleet drift patches: a verified fix with no patient data, shared across sites under policy | Released, local reference hub | Simulator | `openadapt-flow fleet`, [FLEET_DRIFT_PATCHES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/FLEET_DRIFT_PATCHES.md) |

## Computer-use agents

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Compile a computer-use agent's successful run into a program (JIT); later runs make no model calls | Released | Synthetic (a recorded Claude run on MockMed) | `openadapt_flow.jit`, [JIT.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/JIT.md) |
| Admit a draft by a person, an admitter key, or an agent under a person-signed policy, including self-admission when the policy allows it | Released | Unit tests | [JIT_ADMISSION.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/JIT_ADMISSION.md) |
| MCP server: your agent decides what to enter, OpenAdapt makes the entry and checks it | Released | Synthetic sandbox | `openadapt-agent`, [packages/agent](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/agent/README.md) |

## Recording, privacy and proof

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Record mouse, keyboard, screen video and accessibility trees on one clock (Windows, macOS, Linux X11) | Released (capture 1.3.0) | Real OS | [packages/capture](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/capture/README.md); Wayland is not supported |
| Find and redact personal and health data in text, screenshots and structure | Released (privacy 1.1.3) | Unit tests | [openadapt-privacy](https://github.com/OpenAdaptAI/openadapt-privacy), [PRIVACY.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/PRIVACY.md) |
| Signed receipts (Seals), countersigned and timestamped, offline by default | Released | Unit tests, real TSA tokens | `openadapt-flow seal`, `countersign`, `local-seal` |
| Strict no-outbound mode and an unattended on-prem service | Released | Synthetic | `openadapt-flow no-outbound`, `service`; [ON_PREM.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/ON_PREM.md) |

## Every command, by capability

Each `openadapt-flow` command, grouped by the capability it serves. A test
fails when a command is added without being listed here.

- **Record and build a program:** `record`, `demo-record`, `compile`, `induce`, `disambiguate`, `for-each`, `compose`, `process`, `intake`, `visualize`, `pull`.
- **Check and admit:** `lint`, `scaffold-verifier`, `check`, `bind-record-checks`, `certify`, `qualify`, `propose-qualification`, `known-ids`, `jit`, `admit`, `approver-grant`.
- **Run and answer:** `run`, `replay`, `resume`, `approve`, `item-approval`, `triage`, `business-decisions`, `explain`, `console`.
- **Judge any executor's write:** `verify-run`, `serve-reward` (scores agent training episodes by reading the system of record).
- **Repair and learn from halts:** `teach`, `teach-branch`, `repair`, `fleet`.
- **Give agents the program:** `emit-skill`, `emit-mcp`, `serve-execute`.
- **Proof:** `seal`, `local-seal`, `countersign`, `attach-seal`.
- **Run on premises:** `service`, `no-outbound`.
- **Share safely with OpenAdapt Cloud:** `sanitize`, `review-sanitized`, `approve-sanitized`, `materialize-approved`, `push`, `validate-hosted`, `report-break`, `report-run`, `connect`, `login`, `connector`.
- **Try it and measure it:** `demo`, `tutorial`, `bench`, `benchmark`.

## Measured results

- **OpenEMR referral, 62 timed runs each, warm.** OpenAdapt took a median of
  29.7 s and a computer-use agent (Claude) 36.5 s. Both saved 62 of 63
  referrals correctly. OpenAdapt made no model calls; the agent cost about
  $0.08 per referral. The same task replayed without page-structure identity
  took 38.6 s, slower than the agent. Raw data and
  figures: [openemr_referral_timing](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/openemr_referral_timing/README.md).
- **openIMIS claims, 150 items.** The compiled program saved 148 of 149
  claims correctly by read-back and stopped safely on the other, with 0
  silent wrong saves and 0 model calls. It also stopped on the one
  changed-screen fault item:
  [SCOREBOARD.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/scoreboard/SCOREBOARD.md).
- **Fault test.** In 90 runs with injected faults, 72 left a wrong record
  behind. A check that trusts the screen's "Saved" banner reported 54 of those
  as success; reading the record back over the app's REST API missed 9; the
  complete database read path caught all 72. This is a coverage test over a
  small, hand-authored set of faults, not a real-world error rate:
  [EFFECT_E2E.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/effect_e2e/EFFECT_E2E.md).

## Where it has run

OpenEMR, the open-source EHR whose 7.0 release is ONC-certified (test copies
of 8.0.0.3 with synthetic patients); openIMIS, the open-source claims system
that runs Nepal's national health insurance scheme (a test copy with
synthetic claims); RDP into a Windows 11 host; a Citrix stand-in; and
OpenAdapt's own test apps. The Evidence column says which applies to each
capability. The full list is on
[Limits](../explanation/limits.md#validated-on).
