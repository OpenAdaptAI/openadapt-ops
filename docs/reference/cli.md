# The `openadapt flow` CLI

Record a workflow once, compile it into a deterministic vision-anchored script,
replay it locally, and heal it on drift. Every command below is a subcommand of
`openadapt flow`.

!!! note "Command form"
    The primary form is `openadapt flow <verb>`. If you installed the standalone
    engine package, the same verbs are available as `openadapt-flow <verb>`
    (drop the space). The flags are identical.

## Verbs at a glance

| Verb | What it does | Exit code |
|---|---|---|
| [`record`](#record) | Record your own app (`--url`) in a headed browser | 0 |
| [`demo-record`](#demo-record) | Serve the sample app and record the canonical demo | 0 |
| [`compile`](#compile) | Compile a recording into a workflow bundle | 0 |
| [`induce`](#induce) | Induce a parameterized program from **multiple** recordings | 0 if certified, 2 if underdetermined |
| [`replay`](#replay) | Replay a bundle, locally and deterministically | 0 on success, 1 on failure |
| [`run`](#run) | Execute a bundle under a deployment config (production) | 0 on success, 1 on failure |
| [`resume`](#resume) | Resume a durably-paused run from its last checkpoint | 0 on success, 1/3 otherwise |
| [`approve`](#approve) | Mark a durably-paused run's escalation approved | 0 on success, 1 if none |
| [`teach`](#teach) | Resolve a halted run from a fix demonstration, governed | 0 if promoted, 1 if refused, 2 on bad inputs |
| [`lint`](#lint) | Report a bundle's coverage gaps | nonzero by severity |
| [`certify`](#certify) | Enforce a safety policy, refuse the bundle if it fails | 2 on failure |
| [`disambiguate`](#disambiguate) | Surface and resolve compile-time ambiguities | 2 if a consequential ambiguity is unresolved |
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

## record

Open a headed browser on your own app and record what you do.

```bash
openadapt flow record --url https://your.app --out rec
```

| Flag | Description |
|---|---|
| `--url` (required) | URL of the app to record against |
| `--out` (required) | Recording output directory |
| `--secret FIELD` | Mark a typed field (by name or id) as a **secret**: its value is never persisted and is injected at replay from `OPENADAPT_FLOW_SECRET_<FIELD>`. `input[type=password]` is always secret. Repeatable. |
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
and branches. It **refuses** — writes no bundle, exits nonzero — when intent is
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

## replay

Replay a bundle. With no `--url`, it serves the bundled sample app.

```bash
openadapt flow replay bundle --url https://your.app --param note="Follow-up"
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--url` | Target app URL (default: serve the bundled sample app) |
| `--drift` | Comma-separated drift modes (`theme,move,rename,modal`) to demonstrate self-healing; only valid **without** `--url` |
| `--run-dir` | Run output directory (default: `runs/replay-<UTC timestamp>`) |
| `--param K=V` | Parameter substitution. Repeatable. |
| `--save-healed-to DIR` | Write the healed bundle to this directory |
| `--headed` | Run the browser headed |
| `--record-video DIR` | Opt-in: capture a WebM of the replay session (default off) |
| `--worklist [RELATION=]FILE` | CSV/JSON worklist of parameter rows driving a **program** bundle's loop over a relation (repeatable). `RELATION=FILE` binds a named relation; a bare `FILE` binds the program's sole loop relation. Refused on a linear bundle. |

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
| `--allow-model-grounding` | **Egress opt-in** (PHI audit REM-3): permit wiring an off-box model grounder / identity-VLM / state-verifier; screenshots may leave the box. Off by default: replay is fully local with zero outbound calls. |

Exits 0 on success and 1 on a halt. With no model component wired, replay is
fully local and makes zero outbound calls; the on-prem VLM appliance is engaged
only when `--allow-model-grounding` is passed **and**
[`OPENADAPT_FLOW_VLM_URL`](configuration.md) is set.

## run

The same executor as [`replay`](#replay), framed for a **real deployment**:
backend, effect verification, API actuation, durable runtime, and policy, all
wired from `--config`. The demo-only `--drift` teaching aid is not offered. See
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

Accepts every [deployment-wiring flag](#replay) above (`--config`,
`--effects-*`, `--api-*`, `--durable`, `--worklist`, `--allow-model-grounding`).
Exits 0 on success and 1 on a halt.

## resume

Resume a durably-paused run from its last verified checkpoint, never re-running
an already-confirmed write. Rebuilds a live backend, re-binds the run's
parameters, and continues from the checkpoint. See
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
if it passes. See [The halt-learn loop](../concepts/halt-learn-loop.md).

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
| `--library` | Directory for the versioned skill library that keeps the promotion lineage (default: `<out>.skills`) |

Deterministic and `$0` on the shipped path: the resolution is induced by the
model-free reference inducer. Exits `0` when a verified revision is promoted (the
updated bundle is at `--out`), `1` on a **governed refusal** (the correction was
underdetermined or would weaken a safety invariant, so nothing is written and the
base bundle stays halting), and `2` when the inputs are unusable (no halt in the
report, no base bundle, or a malformed fix).

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

Enforce a policy on a bundle and refuse it (nonzero exit) if it fails. This is
what makes "runnable" distinct from "certified safe."

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

## disambiguate

Surface the compile-time multiple-choice questions an ambiguous demonstration
raises, and apply the answers as guards or parameters. Ask, do not guess.

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

Emit a compiled bundle as an Agent Skills folder, or as a standalone MCP server,
so other agents can invoke the workflow as a tool.

```bash
openadapt flow emit-skill bundle --out skills/
openadapt flow emit-mcp   bundle --out server.py
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--out` (required) | Output folder (skill) or file path (MCP `server.py`) |
