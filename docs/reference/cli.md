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
| [`replay`](#replay) | Replay a bundle, locally and deterministically | 0 on success, 1 on failure |
| [`lint`](#lint) | Report a bundle's coverage gaps | nonzero by severity |
| [`certify`](#certify) | Enforce a safety policy, refuse the bundle if it fails | 2 on failure |
| [`disambiguate`](#disambiguate) | Surface and resolve compile-time ambiguities | 2 if a consequential ambiguity is unresolved |
| [`bench`](#bench) | Replay a bundle N times against the sample app and aggregate | 0 if all pass |
| [`benchmark`](#benchmark) | Compare compiled replay vs a computer-use agent | 0 |
| [`emit-skill`](#emit) | Emit an Agent Skills folder for a bundle | 0 |
| [`emit-mcp`](#emit) | Emit a standalone MCP `server.py` for a bundle | 0 |

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

Exits 0 on success and 1 on a halt. The on-prem VLM appliance is engaged only
when [`OPENADAPT_FLOW_VLM_URL`](configuration.md) is set.

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
```

| Flag | Description |
|---|---|
| `bundle` (positional) | Workflow bundle directory |
| `--policy` (required) | Policy YAML path, or a built-in name (`permissive`, `clinical-write`) |

Exits 2 when the bundle fails certification.

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
