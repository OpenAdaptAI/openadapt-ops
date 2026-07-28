# The `openadapt flow` CLI

Record a workflow once, compile it into a deterministic vision-anchored script,
replay it locally, and resolve, repair, or halt under drift. Every command below
is a subcommand of `openadapt flow`.

!!! note "Command form"
    The primary form is `openadapt flow <verb>`. If you installed the standalone
    engine package, the same verbs are available as `openadapt-flow <verb>`
    (drop the space), with identical flags.

## Verbs at a glance

| Verb | What it does | Exit code |
|---|---|---|
| [`record`](#record) | Record your own app on any [substrate](#backend) (browser via `--url`; Windows, macOS, Linux, RDP, or Citrix via `--backend`) | 0 |
| [`demo-record`](#demo-record) | Serve the sample app and record the canonical demo | 0 |
| [`compile`](#compile) | Compile a recording into a workflow bundle | 0 |
| [`induce`](#induce) | Induce a parameterized program from **multiple** recordings | 0 if certified, 2 if underdetermined |
| [`for-each`](#for-each) | Author a data-driven **loop** bundle: run one demonstration once per worklist record | 0 on success, nonzero on a mapping error |
| [`replay`](#replay) | Replay a bundle, locally and deterministically | 0 on success, 1 on failure |
| [`run`](#run) | Execute a bundle through the fail-closed deployment gate | 0 success, 1 execution halt, 2 refusal |
| [`resume`](#resume) | Resume a durably-paused run from its last checkpoint | 0 on success, 1/3 otherwise |
| [`approve`](#approve) | Mark a durably-paused run's escalation approved | 0 on success, 1 if none |
| [`teach`](#teach) | Resolve a halted run from a fix demonstration, governed | 0 if promoted, 1 if refused, 2 on bad inputs |
| [`lint`](#lint) | Report a bundle's coverage gaps | nonzero by severity |
| [`certify`](#certify) | Enforce a safety policy, refuse the bundle if it fails | 2 on failure |
| [`seal`](#seal) | Copy, encrypt, integrity-check, and atomically publish a deployment candidate | 0 on success, 2 on refusal |
| [`qualify`](#qualify) | Review, test, explain, and certify a versioned qualification project | nonzero on refusal |
| [`disambiguate`](#disambiguate) | Surface and resolve compile-time ambiguities | 2 if a consequential ambiguity is unresolved |
| [`connect`](#connect) | Pair this computer to a Cloud workspace (launcher command, needs OpenAdapt 1.7+) | 0/1 |
| [`login`](#login) | Validate a hosted ingest token and remember the host | 0/1 |
| [`runtime-keygen`](#runtime-keygen) | Create one Ed25519 runner key and print its public Cloud trust entry | 0/1 |
| [`push`](#push) | Explicitly upload a recording or bundle to a control plane | 0/1 |
| [`validate-hosted`](#validate-hosted) | Bind local validation evidence to a one-time hosted challenge | 0/1 |
| [`report-break`](#report-break) | Send a scrubbed, schema-minimized halt descriptor | 0/1 |
| [`visualize`](#visualize) | Render a bundle's program graph (steps, ladder, gates, halts) | 0 |
| [`bench`](#bench) | Replay a bundle N times against the sample app and aggregate | 0 if all pass |
| [`benchmark`](#benchmark) | Compare compiled replay vs a computer-use agent | 0 |
| [`emit-skill`](#emit) | Emit an Agent Skills folder for a bundle | 0 |
| [`emit-mcp`](#emit) | Emit a standalone MCP `server.py` for a bundle | 0 |

!!! tip "One config wires a real deployment"
    `record`, `compile`, `certify`, `replay`, `run`, and `resume` all accept
    `--config deployment.yaml`, which wires the backend, effect verification, API
    actuation, durable runtime, and policy in one place. See the
    [deployment configuration](deployment-config.md) reference. Direct flags
    below override individual fields.

## Choosing a backend {#backend}

`record`, `replay`, `run`, and `resume` all accept a **backend selector** that
chooses what the workflow drives: a browser, native Windows/macOS/Linux
desktop, RDP session, or Citrix Workspace window. It overrides the `backend` section of a
[`--config`](deployment-config.md). With no flag the default is `web`, which
reproduces the historical browser behavior. See
[Backends, where it runs](../concepts/backends.md) for the substrate model.

| Flag | Description |
|---|---|
| `--backend {web,windows,macos,linux,rdp,citrix}` | Select the released adapter: browser, Windows UIA, exact native macOS window, exact Linux AT-SPI window, RDP transport/window, or the dedicated Citrix Workspace-window preset. |
| `--agent-url URL` | Base URL of the in-guest Windows (WAA) agent for `--backend windows` (e.g. `http://localhost:5001`). Overrides `backend.agent_url` |
| `--macos-app APP` | Exact owner application for `--backend macos` (for example `TextEdit`). |
| `--macos-window-title TITLE` | Window-title substring for `--backend macos`; ambiguous matches are refused. |
| `--linux-app APP` | Exact AT-SPI application name for `--backend linux` (for example `gedit`). |
| `--linux-window-title TITLE` | Exact top-level window title for `--backend linux`; zero or multiple matches are refused. |
| `--linux-allow-physical-input` | Explicitly allow window-bound X11 pointer/keyboard fallback when native AT-SPI actuation is unavailable. |
| `--rdp-host HOST` | RDP host/IP for `--backend rdp` (network RDP). For a local client window use `--rdp-window` instead. |
| `--rdp-window OWNER` | Exact local remote-display window owner/process for `rdp` or `citrix` (`Citrix Viewer` on macOS; `wfica32` on Windows by default for Citrix). |
| `--rdp-window-title TITLE` | Exact local RDP/Citrix client-window title used to disambiguate multiple owner matches. |
| `--rdp-readiness-text TEXT` | Stable text that must be visible before input. Required for governed Citrix `run`. |

```bash
# Drive a native Windows app through the in-session agent
openadapt flow replay bundle --backend windows --agent-url http://localhost:5001

# Drive one exact native Linux application window through AT-SPI
openadapt flow replay bundle --backend linux \
  --linux-app gedit --linux-window-title 'Patient notes'

# Drive network RDP
openadapt flow run bundle --backend rdp --rdp-host 10.0.0.5 --config deployment.yaml

# Drive a bound Citrix Workspace window and refuse a locked/not-ready frame
openadapt flow run bundle --backend citrix \
  --rdp-window-title 'Ward A' --rdp-readiness-text 'Appointments' \
  --config deployment.yaml
```

!!! note "Selecting a backend"
    `web`, `windows`, `macos`, `linux`, `rdp`, and `citrix` are released
    adapters behind one backend protocol, running the same bundle, resolution
    ladder, identity gate, and effect verification. Every workflow is qualified
    in its real environment. See the
    [backend support table](../concepts/backends.md#status-at-a-glance) and
    [Qualification evidence](../get-started/what-works-today.md).

## record

Record what you do on your own app. The [backend selector](#backend) chooses the
substrate: `--backend web` (the default) opens a headed browser on the app at
`--url`; the native and remote selectors record Windows, macOS, Linux, RDP, or
Citrix through their exact target flags. The example below records the web
substrate.

```bash
openadapt flow record --url https://your.app --out rec
```

| Flag | Description |
|---|---|
| `--url` | URL of the app to record against. **Required for `--backend web`** (the default); other substrates target through the [backend selector](#backend) instead. |
| `--out` (required) | Recording output directory |
| `--secret FIELD` | Mark a typed field (by name or id) as a **secret**: never persisted, injected at replay from `OPENADAPT_FLOW_SECRET_<FIELD>`. `input[type=password]` is always secret. Repeatable. |
| `--param FIELD` | Record a typed field as a **parameter**: its demonstrated value becomes the default, overridable at replay with `--param`. Repeatable. |
| `--headless` | Run the browser headless (scripted or CI recording) |

## demo-record

Serve the bundled sample app locally and record the canonical triage demo. Good
for the [five-minute tour](../get-started/index.md).

```bash
openadapt flow demo-record --out rec
```

| Flag | Description |
|---|---|
| `--out` (required) | Recording output directory |
| `--note-text` | Note text typed during the demo (recorded as a parameter) |
| `--param-name` | Parameter name for the note (default `note`) |
| `--drift` | Comma-separated drift modes to record against |
| `--headed` | Run the browser headed |
| `--record-video DIR` | Opt-in: capture a WebM of the recording session (default off) |

## compile

Compile a recording directory into a workflow bundle.

```bash
openadapt flow compile rec --out bundle --name my-task
```

| Argument / flag | Description |
|---|---|
| `recording` (positional) | Recording directory produced by `record` |
| `--out` (required) | Output bundle directory |
| `--name` (required) | Workflow name |

## induce

Induce a parameterized **program** bundle from **two or more** recordings (or
already-compiled bundles) of the same task: infer the shared parameters, loops,
and branches. It **refuses** (writes no bundle, exits nonzero) when intent is
underdetermined, rather than guessing a branch. See
[Induce a program from multiple traces](../guides/induce-a-program.md).

```bash
openadapt flow induce rec-1 rec-2 rec-3 --out program --name my-program --held-out
```

| Argument / flag | Description |
|---|---|
| `recording ...` (positional, 2+) | Recording or bundle directories of the same task |
| `--out` (required) | Output program-bundle directory (written **only** when certified) |
| `--name` | Name for the induced workflow (default `induced-program`) |
| `--held-out` | Also run leave-one-out held-out validation and print per-fold reproduction scores (needs 2+ traces) |

Exits `0` when the program is **certified** (bundle written) and `2` when it is
**not certified** (no bundle written; the uncertainties are printed).

## for-each

Author a data-driven **loop** from a single demonstration. `for-each` takes one
compiled linear bundle and a worklist (CSV or JSON) and emits a `program: true`
bundle whose loop runs the demonstrated body once per record, binding each
record's columns to the workflow's parameters. Every iteration keeps the linear
bundle's gates: identity checks and effect verification run per record, the loop
is bounded by a hard `--max-iterations` cap, and a refuted or ambiguous write
halts the run instead of skipping the record. See
[Run a workflow for each record](../guides/data-driven-loops.md).

```bash
openadapt flow for-each bundle --records worklist.csv --out queue-bundle \
  --map mrn=patient_id --map note=note_text
```

| Argument / flag | Description |
|---|---|
| `bundle` (positional) | The compiled linear bundle to wrap in a loop |
| `--records` (required) | Worklist file: a `.csv` whose header names the columns, or a `.json` list of row objects. One record is one iteration. |
| `--out` (required) | Output program-bundle directory |
| `--map COLUMN=PARAM` | Map a worklist column to a workflow parameter (repeatable). Omit to map each column to the parameter of the same name. |
| `--relation` | Name of the emitted loop relation (default `worklist`) |
| `--max-iterations` | Hard fail-safe bound on iterations (default `1000`). A longer worklist is refused at authoring time and halts at run time. |
| `--loop-var` | Optional human label for the loop variable (reports only) |
| `--name` | Name for the looped workflow (default `<body>-for-each`) |

The column-to-parameter mapping is explicit and validated. An unmapped column, a
mapping onto an unknown or secret parameter, a bound parameter with no column and
no demonstrated default, a ragged worklist, or a worklist longer than the bound
all **fail loudly** and write no bundle. Once authored, drive the loop with
[`replay --worklist`](#replay) or [`run --worklist`](#run).

## replay

Replay a bundle against the substrate chosen by the [backend selector](#backend).
On the default `web` backend, `--url` names the target app and, with no `--url`,
replay serves the bundled sample app. For Windows, macOS, Linux, RDP, or Citrix,
select its backend and exact target flags instead of `--url`. The example below
replays the web substrate.

```bash
openadapt flow replay bundle --url https://your.app --param note="Follow-up"
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--url` | Target app URL for the `web` backend (default: serve the bundled sample app). Non-web substrates target through the [backend selector](#backend) instead. |
| `--drift` | Comma-separated drift modes (`theme,move,rename,modal`) to demonstrate self-healing on the bundled web demo; only valid **without** `--url` |
| `--run-dir` | Run output directory (default: `runs/replay-<UTC timestamp>`) |
| `--param K=V` | Parameter substitution. Repeatable. |
| `--save-healed-to DIR` | Write the healed bundle to this directory |
| `--headed` | Run the browser headed |
| `--record-video DIR` | Opt-in: capture a WebM of the replay session (default off) |
| `--worklist [RELATION=]FILE` | CSV/JSON worklist of parameter rows driving a **program** bundle's loop over a relation (repeatable). `RELATION=FILE` binds a named relation; a bare `FILE` binds the sole loop relation. Refused on a linear bundle. |

**Deployment-wiring flags** (shared with [`run`](#run) / [`resume`](#resume);
default off, so an unconfigured replay behaves exactly as before):

| Flag | Description |
|---|---|
| `--config YAML` | [Deployment config](deployment-config.md) wiring backend / actuation / effects / runtime / policy. Flags below override individual fields. |
| `--effects-kind` | System-of-record verifier: `none`, `rest`, `fhir`, `document-hash`. Verifies consequential writes against the real record, not the screen. |
| `--effects-base-url` | Base URL for the `rest` / `fhir` verifier |
| `--effects-root` | Document-store root for the `document-hash` verifier |
| `--api-actuator` | Perform a step carrying an `ApiBinding` via the API ($0, no GUI), confirmed by the effect verifier |
| `--api-base-url` | Base URL for the API actuator (implies `--api-actuator`) |
| `--durable` | Enable the Tier-3 [durable runtime](../concepts/durable-runtime.md): checkpoint each verified step, durably pause on halt, resumable via `resume` |
| `--allow-model-grounding` | **Model-egress opt-in** (PHI audit REM-3): permit wiring an off-box model grounder / identity-VLM / state-verifier; screenshots may leave the box. Off by default: replay makes no model-service calls; target and effect-verifier traffic stays deployment-defined. |

Exits 0 on success, 1 on a halt. With no model component wired, replay makes no
model-service calls; target and effect-verifier traffic follows the deployment
config. The on-prem VLM appliance engages only when `--allow-model-grounding` is
passed **and** [`OPENADAPT_FLOW_VLM_URL`](configuration.md) is set.

## run

The same executor as [`replay`](#replay), behind a fail-closed admission gate:
the bundle must pass policy, identity coverage, effect coverage, approval,
encryption, and manifest-integrity checks before any action executes. Backend,
effect verification, API actuation, durable runtime, and policy come from
`--config`. The demo-only `--drift` teaching aid is not offered here. See
[Run a deployment](../guides/run-a-deployment.md).

```bash
openadapt flow run bundle --config deployment.yaml
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--url` | Target app URL (default: `backend.url` from `--config`) |
| `--run-dir` | Run output directory (default `runs/replay-<UTC timestamp>`) |
| `--param K=V` | Parameter substitution. Repeatable. |
| `--save-healed-to DIR` | Write the healed bundle to this directory |
| `--headed` | Run the browser headed |
| `--policy NAME-OR-PATH` | Certifying policy (default: config policy, then `clinical-write`). |
| `--approve-unverified-writes` | Approve writes whose declared effects cannot be independently verified in this deployment. |
| `--strict-templates` | Refuse rather than warn when template/screenshot assets are unsealed. |
| `--allow-unencrypted` | Dev escape hatch: disables the default encryption-at-rest refusal. |
| `--pin-digest SHA256` | Refuse unless the sealed content digest matches. |
| `--pin-version VERSION` | Refuse unless the compiler version matches. |
| `--dry-run`, `--explain` | Print the gate report and exit without executing. |

Accepts every [deployment-wiring flag](#replay) above (`--config`,
`--effects-*`, `--api-*`, `--durable`, `--worklist`, `--allow-model-grounding`).
Exits `2` on admission refusal, `0` after successful execution, and `1` if an
admitted execution later halts.

## resume

Resume a durably-paused run from its last verified checkpoint, never re-running
an already-confirmed write. Rebuilds a live backend, re-binds the run's
parameters, and continues. See
[Durable runtime](../concepts/durable-runtime.md).

```bash
openadapt flow resume runs/replay-20260712-140233 --require-approval
```

| Flag | Description |
|---|---|
| `run_dir` (positional) | The paused run directory (holds the checkpoints) |
| `--url` | Target app URL to rebuild a live backend (default: `backend.url` from `--config`) |
| `--headed` | Run the browser headed |
| `--require-approval` | Refuse to resume unless the pending escalation is `approved` (see [`approve`](#approve)) |

Also accepts the deployment-wiring flags (`--config`, `--effects-*`, `--api-*`,
`--durable`). Exits `1` when there is no pending escalation to resume, `3` when
`--require-approval` is set and the escalation is not approved, and `0`/`1` on
the resumed run's success/halt.

## approve

Mark a durably-paused run's pending escalation `approved`, so
[`resume --require-approval`](#resume) will continue it.

```bash
openadapt flow approve runs/replay-20260712-140233
```

| Flag | Description |
|---|---|
| `run_dir` (positional) | The paused run directory (holds the escalation) |

Exits `0` on success (or if already approved) and `1` when there is no pending
escalation.

!!! note "Approval scope today"
    Approval is recorded as auditable metadata on the escalation, and
    `resume --require-approval` gates on it. A full approval store (who, when,
    signature) is on the durable roadmap. See
    [Durable runtime](../concepts/durable-runtime.md).

## teach

Resolve a halted run: demonstrate the fix once, and `teach` compiles it back
into the workflow through the governed induction path so that state never halts
again. It induces the correction as a guarded exception branch, gates it against
a regression check and a held-out canary, and writes an updated bundle **only**
on pass. See [The halt-learn loop](../concepts/halt-learn-loop.md).

```bash
openadapt flow teach runs/replay-20260712-140233 \
    --fix recordings/dismiss-the-dialog \
    --bundle bundles/patient-intake \
    --out bundles/patient-intake-v2
```

| Flag | Description |
|---|---|
| `run_dir` (positional) | The HALTED run directory (holds `report.json` with a `halt`) |
| `--fix` (required) | The fix demonstration: a **recording directory** of just the corrective actions (e.g. dismiss the dialog), or a `.json` correction spec (`resolution_steps`, optional `tail_intents` / `facts` / `params`) |
| `--bundle` (required) | The base bundle that halted (seeds the skill's active version) |
| `--out` (required) | Output directory for the UPDATED bundle, written **only** when the correction is promoted |
| `--skill-id` | Skill id in the versioned library (default: the run's workflow name) |
| `--library` | Directory for the versioned skill library holding the promotion lineage (default: `<out>.skills`) |

Deterministic and `$0` on the shipped path: the resolution is induced by the
model-free reference inducer. Exits `0` when a verified revision is promoted (the
updated bundle is at `--out`), `1` on a **governed refusal** (the correction was
underdetermined or would weaken a safety invariant; nothing is written and the
base bundle stays halting), `2` when inputs are unusable (no halt in the report,
no base bundle, or a malformed fix).

## lint

Report a bundle's coverage gaps (unarmed clicks, vacuous postconditions,
under-classified risk), each with a severity.

```bash
openadapt flow lint bundle
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--strict` | Exit nonzero on warnings too (default: only on errors) |

Exits nonzero once a finding reaches `error` (an unarmed or vacuous
*irreversible* step).

## certify

Enforce a policy on a bundle and refuse it (nonzero exit) if it fails. This makes
"runnable" distinct from "certified safe."

```bash
openadapt flow certify bundle --policy clinical-write
# or read the policy from a deployment config:
openadapt flow certify bundle --config deployment.yaml
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--policy` | Policy YAML path, or a built-in name (`permissive`, `clinical-write`). Defaults to `policy.policy` from `--config`. |
| `--config YAML` | [Deployment config](deployment-config.md) to read the policy from when `--policy` is omitted, so one file both certifies and runs the bundle |

Provide `--policy` or a `--config` that sets `policy.policy`; certify errors if
neither supplies a policy. Exits 2 when the bundle fails certification.

## seal

Copy a reviewed bundle into a new encrypted deployment candidate without
modifying the source. The key comes only from `OPENADAPT_BUNDLE_KEY`, so it does
not leak through process arguments. `seal` refuses symlinks, an invalid source,
or an existing destination; verifies the encrypted result before atomic
publication; and invalidates any certification inherited from the source so the
exact sealed bytes must pass certification before deployment.

```bash
export OPENADAPT_BUNDLE_KEY='<inject from your secret manager>'
openadapt flow seal bundle-v2 --out bundle-prod
openadapt flow certify bundle-prod --config deployment.yaml
```

| Argument / flag | Description |
|---|---|
| `source` (positional) | Existing workflow bundle directory. It is validated and never modified. |
| `--out`, `-o` (required) | New destination directory. It must not already exist. |

Exits `0` after verified publication and `2` on refusal. Key custody and
rotation remain deployment responsibilities.

## qualify

Create and operate a versioned qualification project for one compiled workflow,
application, execution surface, and environment. The commands below are the
scriptable counterpart of the Desktop qualification cockpit: they review action
risk, bind identity and effect contracts, run representative and fault cases,
explain refusals, and issue certification for the exact reviewed revision.

```bash
openadapt flow qualify init bundle \
  --target citrix \
  --application Accuro \
  --application-version 2026.1 \
  --environment-digest "$QUALIFIED_ENVIRONMENT_SHA256" \
  --minimum-tier 3

openadapt flow qualify inspect bundle --policy clinical-write
openadapt flow qualify explain bundle --policy clinical-write
openadapt flow qualify certify bundle \
  --policy clinical-write \
  --evidence-root qualification-evidence
```

| Subcommand | What it does |
|---|---|
| `schema` | Print the machine-readable qualification project schema. |
| `init` | Bind a bundle to its target surface, application/version, environment, runtime, required runner capabilities, and minimum verification tier. |
| `inspect` | Show graph, action inventory, coverage, case state, requalification conditions, and certification readiness. |
| `set-risk` | Assign `read_only`, `state_changing`, `consequential`, or `irreversible` to one action, with an explanation. |
| `set-identity` | Arm an action with the canonical identity ladder or explicit signals, regions, matching rules, and quorum. |
| `set-effect` | Set the required verification tier for one declared effect. |
| `trust-runner` | Trust a qualification runner's signing key for imported case receipts. |
| `add-case` | Add a representative or fault case and its expected precise outcome. |
| `run` | Import and validate signed case-result receipts against the current workflow revision and environment. |
| `add-requalification` | Record an application, environment, workflow, policy, runtime, expiry, or operator-triggered requalification condition. |
| `explain` | Explain every certification refusal and the action needed to resolve it. |
| `report` | Generate the qualification report, including versions, action/risk inventory, identity and effect coverage, cases, exclusions, capabilities, hashes, and requalification conditions. |
| `certify` | Certify the exact project revision when its required contracts and cases pass. |

`init --target` accepts `web`, `windows`, `macos`, `linux`, `rdp`, or
`citrix`. `add-case --kind` accepts `representative`, `ambiguity`,
`wrong_identity`, `stale_identity`, `weak_effect`, or `missing_effect`; its
expected outcome is one of `verified`, `completed_unverified`, `halted`,
`failed`, or `rolled_back`. Use each subcommand's `--help` for its complete
identity-signal, screen-region, effect, and runner-signing options.

Qualification does not copy secret values into the bundle. Case inputs and raw
evidence remain in the local evidence root; imported receipts are accepted only
when their signatures, environment, revision, capabilities, and evidence hashes
match the project. See [Qualify a workflow](../guides/qualify-a-workflow.md) for
the complete Desktop and CLI journey.

## disambiguate

Surface the compile-time multiple-choice questions an ambiguous demonstration
raises, and apply the answers as guards or parameters. Ask, don't guess.

```bash
openadapt flow disambiguate bundle --interactive --write
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--interactive` | Prompt for each question on the terminal |
| `--answers FILE` | JSON file mapping question id to chosen option key |
| `--write` | Save the resolved workflow back into the bundle |

Exits 2 if a consequential (must-answer) ambiguity is left unresolved.

## connect

Pair this computer to a Cloud workspace with a one-time code generated in the
dashboard. This is a command of the **`openadapt` launcher** (invoked as
`openadapt connect`, not `openadapt flow connect`) and ships from **OpenAdapt
1.7 onward**. On an older build it fails with `No such command 'connect'` (see
[troubleshooting](../guides/troubleshooting.md#connect-no-such-command)).

```bash
openadapt connect --pairing oap_… --host https://app.openadapt.ai
```

| Flag | Description |
|---|---|
| `--pairing` | One-time pairing code from **Connect local OpenAdapt** in Cloud settings. Expires after five minutes and is single-use. |
| `--host` | Control-plane base URL. Defaults to `https://app.openadapt.ai`. |

The resulting workspace credential is stored in the OS keychain and revocable in
Cloud settings. For a scripted install or a second machine, use
[`login`](#login) with a reusable ingest token instead.

## login

Validate a hosted ingest token. The CLI stores the token in the OS keychain when
available and stores only the non-secret host in its config. Plaintext token
storage requires an explicit fallback flag. This is a connectivity command, not
a hosted-runner entitlement.

```bash
openadapt flow login --token <ingest-token>
```

| Flag | Description |
|---|---|
| `--token` | Ingest token. Falls back to `OPENADAPT_INGEST_TOKEN`, the OS keychain, then an existing config migration token. |
| `--host` | Control-plane base URL. Defaults to the configured host, then `https://app.openadapt.ai`. |
| `--no-save` | Validate without writing the host/token to the config file. |

## runtime-keygen

Create the Ed25519 key that identifies one customer-controlled qualification
runner to an organization. The command refuses an existing output path. It
prints the public trust entry for Cloud and keeps the private key file inside
the runner boundary.

```bash
openadapt flow runtime-keygen \
  --out /secure/runner-ed25519.key \
  --key-id clinic-runner-2026-07 \
  --runner-id clinic-runner-01 \
  --org-id 00000000-0000-4000-8000-000000000001
```

| Flag | Description |
|---|---|
| `--out` | New private-key file. It must not exist. On POSIX, Flow creates it owner-only. |
| `--key-id` | Stable public key identifier in the Cloud trust map. |
| `--runner-id` | Exact runner identity that Cloud binds to this key. |
| `--org-id` | Exact Cloud organization UUID that trusts this runner. |

## validate-hosted

Acquire an expiring, one-time Cloud challenge and create a signed operator
attestation over strict lint, policy certification, and a successful local
replay. Both inputs must be reviewed, approved sanitized derivatives. The bundle
must be compiled from the exact approved recording, and bundle sanitation must
preserve execution-bearing bytes.

```bash
openadapt flow validate-hosted \
  --recording recording.sanitized \
  --bundle bundle.sanitized \
  --run-dir runs/triage-validation \
  --policy clinical-write \
  --risk-class consequential \
  --environment validation/mock-emr-v1 \
  --target-kind web \
  --target-url https://validation.example/login \
  --allowed-host cdn.validation.example \
  --signing-key-id clinic-runner-2026-07 \
  --signing-runner-id clinic-runner-01 \
  --signing-private-key-file /secure/runner-ed25519.key \
  --out triage.runtime-validation.json
```

| Flag | Description |
|---|---|
| `--recording` | Approved sanitized recording derivative used to compile the bundle. |
| `--bundle` | Approved sanitized bundle derivative whose exact archive will upload. |
| `--run-dir` | Successful, non-halted local replay directory containing `report.json`. |
| `--policy` | Named or file-backed policy that must pass again during validation. |
| `--risk-class` | `low` or `consequential`; must match the risk derived from the compiled steps and be allowed by Cloud. |
| `--environment` | Non-PHI validation-environment identifier; only its SHA-256 is included. |
| `--target-kind` | Optional expected substrate: `web`, `windows`, `macos`, `linux`, `rdp`, or `citrix`. The report supplies the signed value; this flag can only cross-check it. |
| `--target-url` | Exact non-PHI HTTPS entry URL. The report must bind the same requested URL and its actual browser origin; credentials, query strings, and fragments are refused. |
| `--allowed-host` | Additional exact hostname allowed during hosted execution. Repeatable; the target hostname is included automatically. |
| `--signing-key-id` | Cloud-trusted Ed25519 key ID for the v3 attestation. |
| `--signing-runner-id` | Exact Cloud-trusted runner ID bound to the key. |
| `--signing-private-key-file` | Local raw or canonical-base64 32-byte Ed25519 private key file. |
| `--legacy-hmac-v2` | Emit HMAC-only v2 during a bounded migration. Do not use it for new trust. |
| `--compiler-config` | Optional JSON object; its digest must match compiler provenance already sealed in the bundle. |
| `--out` | Attestation JSON path. |
| `--destination-kind`, `--trusted-host` | Destination policy for managed or exact-allowlisted customer endpoints. |
| `--host`, `--token` | Override the configured control plane and token used for the challenge and separate ingest MAC. |

The attestation binds the exact recording and bundle archive hashes, compiler
identity/configuration, parameter schema, target/host execution boundary,
lint/certification evidence, replay report, validation environment, policy,
risk class, and challenge. The client also verifies the run report's workflow,
bundle digest, source-recording provenance, parameter schema, and actual browser
origin. Cloud verifies the organization-bound runner signature, its configured
exact policy, risk-class, and deployed compiler-version allowlists, and consumes
the organization/token-bound challenge once when the bundle is accepted. It
rechecks current signer trust and the deployment allowlists before dispatch.

This is operator self-attestation, not an independent test or certification.
The Ed25519 signature binds the trusted runner. The separate ingest-token MAC
binds the one-time submission. Neither proves that Cloud or an auditor observed
the local replay. `certify` only evaluates the selected policy. For independent
certification, use independent evidence custody and a separately controlled
evaluator.

## push

Create or verify a sanitized derivative, enforce its review/approval and
destination policy, and upload its immutable approved archive to `/api/ingest`.
Uploading does **not** itself run the workflow.

Sanitation does not establish runnability. Recording push registers the exact
approved source and returns the next validation state; it does not create a
runnable workflow. Compile that derivative locally, run strict lint,
certification, and successful replay, then sanitize, review, and approve the
bundle, run `validate-hosted`, and push the exact bundle with its one-time
attestation.

```bash
openadapt flow sanitize recording --kind recording --out recording.sanitized
openadapt flow review-sanitized recording.sanitized --original recording
openadapt flow approve-sanitized recording.sanitized \
  --original recording --reviewer alice@example.com
openadapt flow push recording.sanitized --kind recording --name "Triage"
```

Calling `push` with a raw path performs the first sanitation step and normally
returns `pending_review` plus the local viewer command. After approval, run
`push` on the derivative directory.

| Flag | Description |
|---|---|
| `path` | Recording or bundle directory. Defaults to the most recent recording in the current directory. |
| `--kind` | `recording` (default) or `bundle`. |
| `--name` | Workflow name. |
| `--workflow-id` | Existing hosted workflow UUID to receive a validated replacement bundle. Valid only with `--kind bundle`. |
| `--resolves-run-id` | Exact halted-run UUID repaired by this replacement. Requires `--kind bundle` and `--workflow-id`; the halt resolves only after atomic activation. |
| `--deployment-kind` | Execution lane: `cloud`, `byoc`, or `regulated`. Independent of destination trust; every lane requires a verified derivative. |
| `--destination-kind` | `openadapt-managed`, `customer-managed`, or `local`. The OpenAdapt origin is recognized automatically. |
| `--trusted-host` | Exact HTTPS origin allowed for a customer-managed endpoint; repeatable. |
| `--sanitized-out` | Destination for the derivative created from a raw path. |
| `--auto-approve` | Administrator policy approval for a stable derivative with complete type coverage. Human review is the default. |
| `--validation-attestation` | Required challenge-bound `validate-hosted` JSON when `--kind bundle`; it must match the exact approved bundle archive. |
| `--attest-non-phi` | Deprecated and refused. A declaration cannot bypass sanitation, review, or exact-hash approval. |
| `--host`, `--token` | Override the configured control plane and token. |

Remote artifact upload requires an approved sanitized derivative. The pipeline
inventories and transforms a copy, rescans it, records unresolved findings and
tool versions in a manifest, and binds operator approval to the derivative hash.
Unknown, symlinked, unsupported, or unresolved content aborts the upload instead
of being copied unchanged. The destination is evaluated separately: a verified
customer endpoint may accept data its policy permits; an unknown endpoint is
refused. Compilation alone is never a de-identification claim.

## sanitize, review-sanitized, approve-sanitized

`sanitize` creates a separate derivative and `openadapt.sanitization/v1`
manifest without modifying the source. `review-sanitized` serves a loopback-only
original-versus-derivative viewer with no remote assets. `approve-sanitized`
records the reviewer and freezes an immutable archive; later modification
invalidates the approval.

```bash
openadapt flow sanitize PATH --kind recording --out DERIVATIVE
openadapt flow review-sanitized DERIVATIVE --original PATH
openadapt flow approve-sanitized DERIVATIVE --original PATH --reviewer IDENTITY
```

| Command/flag | Description |
|---|---|
| `sanitize --kind` | Required artifact type: `recording` or `bundle`. |
| `sanitize --redactions FILE` | Additional local JSON text/image redactions. |
| `sanitize --overwrite` | Replace an existing derivative; never modifies the source. |
| `review-sanitized --original` | Sensitive source shown only by the loopback viewer. |
| `review-sanitized --no-open` | Print the local URL rather than opening a browser. |
| `approve-sanitized --original` | Required sensitive source used to verify derivative provenance. |
| `approve-sanitized --reviewer` | Required identity written into the approval record. |

A bundle whose sanitation changed load-bearing identity evidence is not accepted
as executable. Parameterize the sensitive value before compilation, or execute
the original inside its trusted runtime boundary.

## report-break

Read a halted run's `report.json` and emit a scrubbed, schema-minimized halt
descriptor. The recording stays local. A PHI/PII-boundary rejection retries with a
harder scrub and can fall back to local-only.

```bash
openadapt flow report-break runs/<halted-run> \
  --workflow-id <id> --deployment-kind byoc
```

| Flag | Description |
|---|---|
| `run_dir` | Halted run directory containing `report.json`. |
| `--workflow-id` | Required hosted workflow id returned by `push` or the dashboard. |
| `--deployment-kind` | `cloud` (default) or `byoc`; routes the teaching target. |
| `--org-id` | Optional organization id. |
| `--host`, `--token` | Override the configured control plane and token. |

See [Hosted browser execution](../guides/hosted.md) for the launch candidate,
sanitation protocol, and destination-aware boundary.

## visualize

See what a demonstration compiled **into**, before it runs. `visualize` reads a
bundle and renders its program graph: the ordered steps, the resolution ladder
each step will try, where an identity gate is armed, which writes carry an effect
check, and every point the run can halt. It writes one of three formats from the
same graph spec, so the CLI, Cloud, and desktop surfaces all show the same thing.
See [Visualize a compiled program](../concepts/program-visualizer.md).

```bash
openadapt flow visualize bundle -o graph.html     # self-contained page
openadapt flow visualize bundle --format mermaid  # flowchart source, to stdout
openadapt flow visualize bundle --format json      # the shared graph spec
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--format {html,mermaid,json}` | `html` (default): a self-contained, offline-openable page. `mermaid`: flowchart source for Markdown and docs. `json`: the shared program-graph spec every surface renders. |
| `-o`, `--out FILE` | Write to a file instead of stdout (parent directories are created) |

Reading is offline and side-effect-free: `visualize` never runs the workflow, so
it is safe to point at any bundle, including one that would refuse to certify.

## bench

Replay a bundle N times against the sample app and aggregate the results.

```bash
openadapt flow bench bundle --n 100 --run-root runs/bench
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--n` | Number of iterations (default 3) |
| `--drift` | Comma-separated drift modes forwarded to the sample-app URL |
| `--run-root` (required) | Directory for per-iteration runs |
| `--param K=V` | Parameter substitution. Repeatable. |
| `--headed` | Run the browser headed |

## benchmark

Compare compiled replay against a computer-use agent on the sample triage task.

!!! warning "The agent arm costs real money"
    The agent arm calls a hosted model and incurs API cost. The compiled arm is
    $0. Run the agent arm only with cost caps in place.

```bash
openadapt flow benchmark --n-compiled 100 --n-agent 20 --out benchmark/
```

| Flag | Description |
|---|---|
| `--n-compiled` | Compiled-replay iterations (default 100) |
| `--n-agent` | Agent iterations (default 20) |
| `--out` | Output directory for results and chart |
| `--note-text` | Note text both arms enter |
| `--headed` | Run the browsers headed |

## emit-skill / emit-mcp {#emit}

Emit a compiled bundle as an Agent Skills folder or a standalone MCP server, so
other agents can invoke the workflow as a tool.

```bash
openadapt flow emit-skill bundle --out skills/
openadapt flow emit-mcp   bundle --out server.py
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--out` (required) | Output folder (skill) or file path (MCP `server.py`) |
