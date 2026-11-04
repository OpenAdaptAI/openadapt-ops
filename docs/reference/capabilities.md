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
   the recording through the web, native Windows, RDP and Citrix backends.
2. **Compiles to the fastest layer the app allows.** Page structure first (DOM,
   Windows UI Automation, macOS Accessibility), direct API calls through
   hand-authored bindings (`ApiActuator`), and pixels only where nothing else
   exists, such as a remote desktop. It is not a pixel-macro recorder.
3. **Builds branching programs, not one linear path.** One program from several
   demonstrations (`induce`, `disambiguate`), a branch learned from several
   halts fixed the same way (`teach-branch`), and background capture of many
   real runs (shadow mode).
4. **Works across surfaces in one workflow.** Backends for web, native Windows
   and macOS, Linux, RDP and Citrix. Programs chain across surfaces passing confirmed values
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
| Runs steps as direct API calls (`ApiActuator`). In an OpenEMR benchmark, an API step compiled from the recording's network traffic took a median of 0.6 s per referral, against 19.65 s on screen. | `runtime/actuators/api.py`, [SCOREBOARD.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/scoreboard/SCOREBOARD.md) |
| Repairs itself when the app changes: governed repair, agent-demonstrated fixes, and fleet patches. | [REPAIR_LIFECYCLE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/REPAIR_LIFECYCLE.md) |
| Compiles a computer-use agent's verified run, with no human demonstration needed. | [JIT.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/JIT.md) |
| Binds each approval to the exact screenshot and form state, and re-reads the form before saving. | [APPROVAL_MODES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/APPROVAL_MODES.md) |
| Fills inputs from a referral PDF, fax image or email, and holds back anything unclear for a person. | `intake`, [INTAKE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/INTAKE.md) |
| Ships as one monorepo with separately installable packages (flow, agent, types, capture, privacy, and desktop). | [README](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/README.md) |
| Makes no model calls on healthy runs. Model training (openadapt-ml) is separate research. | [README](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/README.md) |

## The full map

Every released capability, with its evidence and where it lives. Released
means in the current releases: `openadapt` 1.19.0 and openadapt-flow 2.5.0 on
PyPI, and Desktop 0.25.0 for Desktop rows. [CAPABILITIES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/CAPABILITIES.md)
also lists what has merged since, which installs from source.

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
| Check one write from Python, without the CLI: one API (`openadapt_flow.verifier`: `begin_write`, `verify_write`; 2.4.1's `capture` form still works, deprecated) with one outcome (`CONFIRMED`, `REFUTED`, `UNCERTAIN`), the receipt, which parts were checked, and the result's scope (read path, stores read, time window, what it doesn't cover) | Released | Synthetic (SQLite; MockMed's fault server over real HTTP) | `openadapt_flow/verifier.py`, [VERIFIER_API.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFIER_API.md) |
| Never send a write twice while its outcome is unknown: an append-only ledger on local disk (pluggable backend), keyed by the write's identity, that every adapter, the MCP tools and the CLI consult before sending; a read-back against the attempt's own baseline resolves it, and a refuted write waits for a person (`openadapt verify ledger list`, `reconcile`, `release`) | Released | Synthetic (MockMed's fault server: a worker killed between the send and the read-back, killed during a timed-out send, killed before the send, a late write, and two worker processes started together on one write) | `openadapt_flow/write_ledger.py`, [VERIFIER_API.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFIER_API.md#the-uncertain-write-ledger) |
| Catch a write that lands after the verdict (a background job, a trigger, a delayed side record): a `CONFIRMED` with a recheck due is provisional (`provisional`, `recheck_due_at`); the recheck reads the whole database again and refutes the earlier result when a change since the post-save read has no explanation, and a recheck that doesn't confirm holds the write in the ledger. Run it from Python (`verifier.recheck`) or MCP (`verify_recheck`). A write after the recheck's read is not seen (`frame.database.recheck_after_s`, no default window) | Released ([#1639](https://github.com/OpenAdaptAI/OpenAdapt/pull/1639)); provisional result, MCP tool and ledger hold ([#1669](https://github.com/OpenAdaptAI/OpenAdapt/pull/1669)) | Real app (Dolibarr 21 and EspoCRM 10 on MariaDB 11.4, 180 s window: 4 of 4 planted late writes at 125 to 130 s refuted at the recheck, correct writes confirmed; EspoCRM's cron daemon needs its job tables declared; Redmine 6.1 on PostgreSQL 17, 180 s window: the first-contact study's late writes F19 and F20 refuted at the recheck, correct writes confirmed); synthetic (SQLite); opt-in live OpenEMR test | `openadapt_flow/verifier.py`, `runtime/effects/late_write.py`, [VERIFY_RUN.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFY_RUN.md#writes-that-land-later) |
| Diff the whole database for the frame (`frame.database`) on SQLite, MySQL, MariaDB and PostgreSQL. On MySQL and MariaDB every column type is read exactly (binary strings, `BIT`, geometries and vectors as hex, `FLOAT` widened to `DOUBLE`, `JSON` as stored text, decimals at full precision). On PostgreSQL every column type is read as text by a declared rule in a session pinned to UTC and exact float output, and a type without a rule, a table the account can't read in full, or an unreadable sequence is refused. So a row the save adds, changes or removes outside the declared records, such as an extra planned call or a stream note, is refuted unless a declared effect, a side record, an attributed concurrent write or an allow-listed bookkeeping table explains it | Released ([#1661](https://github.com/OpenAdaptAI/OpenAdapt/pull/1661)); PostgreSQL ([#1673](https://github.com/OpenAdaptAI/OpenAdapt/pull/1673)) | Real app (Dolibarr 21 on MariaDB 11.4: all 387 tables read where the frame raised `TypeError`; EspoCRM on MariaDB 11.4: the first-contact study's extra call and stream note refuted, correct opportunities verified; Redmine 6.1 on PostgreSQL 17: 58 tables read, a stray upload in a table the contract doesn't read refuted, correct writes verified); live MariaDB and PostgreSQL type tests | [VERIFY_RUN.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFY_RUN.md#the-whole-database), `runtime/effects/db_snapshot.py` |
| Catch a lost update: another user saves a change to the record while the agent works, and the agent saves its stale copy over it. Before and after look like a correct update, so `frame.versions` reads the target's versions (FHIR or SQL version history, a version column, or the app's audit or action-history table) before and after the write. A version by another author, or more than one version step when no author is read, refutes the write; a version that can't be read or attributed stops it | Released ([#1662](https://github.com/OpenAdaptAI/OpenAdapt/pull/1662)) | Real app (HAPI FHIR and EspoCRM, first-contact study fault scripts: both lost updates refuted, correct updates verified, every other case's verdict unchanged) | [VERIFY_RUN.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFY_RUN.md#lost-updates), `runtime/effects/versions.py` |
| Guarded save: a safety layer any agent wraps around one write (check the record, hold for approval, read back) | Released ([#1258](https://github.com/OpenAdaptAI/OpenAdapt/pull/1258)) | Synthetic | `GUARDED_SAVE.md` |
| Judge an "ensure the record exists" write (found, created once with every value, or needs review) through a FHIR server's read path only: searches, AuditEvent and `_history`, never the database; the coverage claim names that read path. An agent's own correction of the record it created counts as one write when the audit trail and history show only that agent, no other reader, and the same record in every version | Released ([#1640](https://github.com/OpenAdaptAI/OpenAdapt/pull/1640), corrections [#1655](https://github.com/OpenAdaptAI/OpenAdapt/pull/1655)) | Real app (Medplum 5.2.8; three blind fault suites: 17/18, 17/20, 19/20; no fault passed in the last two. Corrections, on 15 blind cases and the 37 public ones: false stops 8 to 2 and 9 to 4 for Claude, no harm passed that the old rule caught) | `openadapt_flow/ensure_record.py`, [ENSURE_RECORD.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/ENSURE_RECORD.md) |
| Check a patient registration on a commercial EHR through its public FHIR sandbox: Epic (open.epic, R4), read through FHIR search and read with SMART backend auth; the frame is the search set, since the sandbox has no AuditEvent or `_history` | Released ([#1656](https://github.com/OpenAdaptAI/OpenAdapt/pull/1656)) | Real app (Epic public sandbox, August 2026 release; blind round 12/13 with none passed as verified, the miss a false refusal fixed in the contract; caught Epic dropping the phone on a 201 create) | `benchmark/commercial_ehr/`, [FINDINGS.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/commercial_ehr/FINDINGS.md) |

## Approvals

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Each save waits for a person by default | Released | Synthetic | [APPROVAL_MODES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/APPROVAL_MODES.md) |
| Approve or decline a save on a paired phone, with one card per decision and swipe or tap | Released (Desktop) | Synthetic | openadapt-desktop `portal/shell` |
| Person-signed grants let named agents or systems answer saves | Released | Unit tests | `openadapt-flow approver-grant` |
| Admit once, then stop only on problems | Released, behind a readiness gate | Synthetic | [APPROVAL_MODES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/APPROVAL_MODES.md) |
| A person's approval in Desktop is signed with a key kept behind Touch ID on a Mac: one-prompt setup in the app, a prompt for every answer, and Flow never sees the key | Released ([#1500](https://github.com/OpenAdaptAI/OpenAdapt/pull/1500)) | Unit tests; opt-in test on a real Secure Enclave | `packages/desktop/openadapt_desktop/approver_keychain.py`, [APPROVAL_MODES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/APPROVAL_MODES.md#the-approver-key) |
| Review stops: every stop as one card with the evidence side by side (the item next to each possible match, field by field), answered with one key or tap on the computer or a paired phone, signed with the approver key, with batches for similar stops. The queue presents and collects; a changed or expired card changes nothing | Released ([#1519](https://github.com/OpenAdaptAI/OpenAdapt/pull/1519)) | Unit tests; a keystroke-level estimate on 20 soak stops (26.7 s to 8.2 s to decide, a model, not a person) | `packages/desktop/openadapt_desktop/stop_queue.py`, [benchmark/stop_queue](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/desktop/benchmark/stop_queue/README.md) |

## Branching work, not one linear path

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Learn one program with branches from two or more recordings, or say which recordings are missing | Released | Synthetic | `openadapt-flow induce`, `disambiguate`; [CAPABILITIES.md (flow)](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/CAPABILITIES.md) |
| Learn a guarded branch from several halts fixed the same way | Released | Synthetic | `openadapt-flow teach-branch`, `learning/branch_teach.py` |
| Run a program over a worklist | Released | Real app | `openadapt-flow for-each` |
| Typed business decisions inside a run | Released | Synthetic | `business_decision` states, `openadapt-flow business-decisions` |
| Capture many real runs in the background for branch mining (shadow mode) | Released (capture) | Synthetic | [SHADOW_MINING.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/capture/docs/SHADOW_MINING.md) |
| Fill a workflow's inputs from a referral PDF, fax image or email | Released | Synthetic | `openadapt-flow intake`, [INTAKE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/INTAKE.md) |
| Learn a worklist loop from recordings that search a record, open it, work it and go back to the list, even when the last row skips the return or rows differ (a field some rows lack, a write some rows get behind a screen check a person accepts). Each pass selects the row's own record by its values, verifies it, and checks that row's write. Certified and governed runs refuse it until qualification covers it | Released ([#1435](https://github.com/OpenAdaptAI/OpenAdapt/pull/1435)) | Synthetic (held-out rows run through the interpreter against an in-memory app) | `openadapt-flow induce`; `Step.target_param` |

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
| Capture a recording's network traffic and compile a clean save into an API step, with the same record check | Released ([#1269](https://github.com/OpenAdaptAI/OpenAdapt/pull/1269)) | Synthetic patients on a local OpenEMR test copy | network capture, `ApiBinding` |
| Run a worklist on several workers at once, one signed-in session each, each item claimed once, with a stop on any worker stopping all | Released ([#1296](https://github.com/OpenAdaptAI/OpenAdapt/pull/1296)) | Synthetic patients on a local OpenEMR test copy | `--workers`, [THROUGHPUT.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/THROUGHPUT.md) |

## When the app changes

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Governed repair: propose, review, campaigns, approval, staging, canary, rollback | Released | Synthetic | `openadapt-flow repair`, [REPAIR_LIFECYCLE.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/REPAIR_LIFECYCLE.md) |
| A calling agent demonstrates the fix for a halted run; the result is a repair candidate | Released (2.1.0) | Synthetic | `run --hold-on-halt`, `repair/agent_teach.py` |
| Font and layout drift halts with a named reason | Released | Synthetic | `runtime/layout_drift.py` |
| Fleet drift patches: a verified fix with no patient data, shared across sites under policy | Released, local reference hub | Simulator | `openadapt-flow fleet`, [FLEET_DRIFT_PATCHES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/FLEET_DRIFT_PATCHES.md) |
| Self-repair: an agent proposes a fix for one halted click, Flow probes it up to the save without saving, a person approves | Released ([#1265](https://github.com/OpenAdaptAI/OpenAdapt/pull/1265)) | Synthetic (MockMed redesign) | `run --self-repair`, [#1265](https://github.com/OpenAdaptAI/OpenAdapt/pull/1265) |

## Computer-use agents

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Compile a computer-use agent's successful run into a program (JIT); later runs make no model calls | Released | Synthetic (a recorded Claude run on MockMed) | `openadapt_flow.jit`, [JIT.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/JIT.md) |
| Admit a draft by a person, an admitter key, or an agent under a person-signed policy, including self-admission when the policy allows it | Released | Unit tests | [JIT_ADMISSION.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/JIT_ADMISSION.md) |
| MCP server: your agent decides what to enter, OpenAdapt makes the entry and checks it | Released | Synthetic sandbox | `openadapt-agent`, [packages/agent](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/agent/README.md) |
| Verify any agent's own writes: `openadapt verify` reads the system of record before and after a write, against a contract the operator owns (REST, FHIR, SQL, GraphQL), and returns a verified receipt (`openadapt.effect-receipt/v1`) or a refusal (`REFUTED`, `UNCERTAIN`), never an unverified success. Python SDK (`openadapt.verify`, which is `openadapt_flow.verifier`: `begin_write`, `verify_write`, `verified_write`) wraps a write in any agent framework; the MCP server (`openadapt verify serve`) offers `verify_begin`, `verify_check` and `verify_recheck` to any MCP client | Released ([#1589](https://github.com/OpenAdaptAI/OpenAdapt/pull/1589)) | Synthetic (MockMed's fault server over real HTTP: correct write, wrong record, not saved, saved twice, unreadable store) | `openadapt verify`, [VERIFY_WRITES.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/VERIFY_WRITES.md) |
| Verified write tools for agent frameworks: `verified(tool, contract=...)` wraps a Claude Agent SDK, OpenAI Agents SDK, LangGraph or CrewAI write tool in one line. The contract and any values the operator pins come from the operator, never the agent's arguments; the store is read before and after; the agent gets a receipt or a refusal, and a refused write is held instead of retried | Released | Synthetic (each framework's own agent loop with a scripted model, writing through the example app's order form over real HTTP: verified save, a save the app drops, a save it keeps twice); one real-model run per framework, opt-in | `openadapt_flow.integrations.agents`, extras `claude-agent-sdk`, `openai-agents`, `langgraph` (CrewAI: install `crewai` beside it); [AGENT_FRAMEWORKS.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/AGENT_FRAMEWORKS.md) |

## Recording, privacy and proof

| Capability | Status | Evidence | Where |
| --- | --- | --- | --- |
| Record mouse, keyboard, screen video and accessibility trees on one clock (Windows, macOS, Linux X11) | Released (capture 1.3.0) | Real OS | [packages/capture](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/capture/README.md); Wayland is not supported |
| Find and redact personal and health data in text, screenshots and structure | Released (privacy 1.1.3) | Unit tests | [openadapt-privacy](https://github.com/OpenAdaptAI/openadapt-privacy), [PRIVACY.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/PRIVACY.md) |
| Signed receipts (Seals), countersigned and timestamped, offline by default | Released | Unit tests, real TSA tokens | `openadapt-flow seal`, `countersign`, `local-seal` |
| Strict no-outbound mode and an unattended on-prem service | Released | Synthetic | `openadapt-flow no-outbound`, `service`; [ON_PREM.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/ON_PREM.md) |
| Anchor an offline Seal in the public Sigstore Rekor transparency log (opt-in; sends one digest and the public key), and verify the anchor offline from the stored inclusion proof | Released ([#1394](https://github.com/OpenAdaptAI/OpenAdapt/pull/1394)) | Unit tests against a simulated Rekor log; real public Rekor entries and Sigstore TSA tokens for the landing demo's referral runs, verified offline in tests; Ed25519ph matches the RFC 8032 test vector | `openadapt-flow local-seal anchor`, `local-seal verify --require-anchor`; [OFFLINE_SEALS.md](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/OFFLINE_SEALS.md#optional-anchor-a-seal-in-a-public-transparency-log) |

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
