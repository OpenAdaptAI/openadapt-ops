---
description: >-
  Every openadapt and openadapt flow command in openadapt 1.23.0 and
  openadapt-flow 3.3.0, what it does, and its main options.
---

# Command reference

`pip install openadapt` installs the `openadapt` command. It has a few
commands of its own and passes two groups through to the engine:

- `openadapt flow ...` runs `openadapt-flow`, the compiler and runtime.
- `openadapt agent ...` runs `openadapt-agent`, the MCP server.

Every command takes `--help`, which is the authority for its options. This
page lists the commands in `openadapt` 1.23.0 and `openadapt-flow` 3.3.0.
[All Flow commands](flow-commands.md) lists every Flow command and subcommand
with its long options, generated from the released package.
[Launcher and agent help](cli-help.md) has the full `--help` text of every
`openadapt` and `openadapt agent` command.

## Launcher commands

| Command | What it does |
|---|---|
| `openadapt quickstart [--break-it] [--watch] [--open] [--out DIR]` | Runs the bundled tutorial: records, compiles, certifies, and runs a save against a test app, then confirms it through the app's API. `--break-it` adds a second run against a backend that fakes success. The browser runs hidden; `--watch` shows its window and `--open` opens the Seal page at the end. See [Quickstart](../tutorials/quickstart.md). |
| `openadapt setup [--client CLIENT] [--dry-run] [--undo]` | Adds the OpenAdapt MCP server and skill to Claude Code, Cursor, Codex, and Gemini CLI, for each one installed. Prints every change; `--undo` reverses them. |
| `openadapt wrap` | Runs an agent task once, then reuses its checked compiled tool. |
| `openadapt verify serve` | Serves write verification to any MCP client: each write an agent makes gets a verified receipt or a refusal. Python agents use `openadapt.verify` instead. `openadapt verify ledger` lists, reconciles, and releases writes whose outcome isn't known yet. |
| `openadapt shadow` | Checks each write an agent makes against the system of record, without blocking it. Same as `openadapt flow shadow`. |
| `openadapt record`, `openadapt compile`, `openadapt run` | Same as `openadapt flow record`, `compile`, and `run`, with the same options. |
| `openadapt pull NAME [--list]` | Downloads a packaged workflow. Same as `openadapt flow pull`. |
| `openadapt bench medplum` | A public benchmark you can rerun: your agent writes to a local Medplum and OpenAdapt checks every write. |
| `openadapt doctor [--backend SURFACE]` | Checks this computer's requirements, for one surface if given. |
| `openadapt deploy [--backend SURFACE] [--secret-ref REF]` | Checks this host and prints the deployment path for a surface. Takes secret references only (`env:NAME` or `keychain:service/item`). |
| `openadapt connect --pairing CODE` | Pairs this computer with an OpenAdapt Cloud workspace. |
| `openadapt verify TARGET` | Checks a receipt offline: a file, a run folder, or a link. Prints who signed it and fails closed on an unknown signer. Same as `openadapt receipt verify`. |
| `openadapt receipt view\|publish\|unpublish\|claim` | Shows a receipt as an offline page, publishes or takes down its public version, and adds published receipts to your Cloud workspace. `openadapt receipt keys pin` and `show` manage the trusted keys. The `openadapt seal` commands still work. See [Receipts](receipts.md). |
| `openadapt version` | Prints installed package versions. |

## Verbs at a glance

`openadapt flow VERB` and `openadapt-flow VERB` are the same command.

| Verb | What it does |
|---|---|
| [`demo`](#try-it) | Shows a checked run and a run where the app fakes success, side by side, on test data. |
| [`tutorial`](#try-it) | The engine side of `openadapt quickstart`. |
| [`demo-record`](#try-it) | Serves the MockMed test app and records the standard triage demonstration. |
| [`record`](#record) | Records a demonstration in a browser, on the desktop, or in an RDP or Citrix client window. |
| [`confirm-surfaces`](#record) | Confirms the windows a cross-window recording used, so the recording can compile. |
| [`browser-accessibility`](#record) | On Linux, starts Chrome, Chromium, Edge, and Brave so `record` can read clicks in them. Writes only your own launcher entries. |
| [`narration`](#record) | Transcribes a recording's spoken narration on this computer, scrubs it, and lines it up with the steps. |
| [`compile`](#build) | Compiles one recording into a bundle. |
| [`induce`](#build) | Learns one program from two or more recordings, or refuses and lists the recordings it needs. |
| [`for-each`](#build) | Wraps a bundle in a loop over a worklist. |
| [`compose`](#build) | Chains bundles from different surfaces, passing confirmed values. |
| [`process`](#build) | Builds a process from separately admitted parts, each with its own admission. |
| [`disambiguate`](#build) | Asks the open questions in an induced program as multiple choice. |
| [`intake`](#build) | Fills a workflow's inputs from a referral PDF, fax image, or email. |
| [`api`](#build) | Shows or admits API steps compiled from a recording's network capture. None runs until a person admits it. |
| [`learn`](#build) | Learns the app's own per-request writes from checked traffic and, after approval, adds them to the contracts. |
| [`variants`](#build) | Builds a variant set: separately admitted variants of one workflow, chosen before the run starts. |
| [`route`](#build) | Shows which admitted variant a variant set would run for one item. Runs nothing. |
| [`sections`](#build) | Shows, renames, merges, or splits a compiled program's named sections. |
| [`visualize`](#inspect) | Draws a bundle as HTML, Mermaid, or JSON. |
| [`lint`](#check) | Lists what the program doesn't cover yet. |
| [`scaffold-verifier`](#check) | Drafts record checks from a recording or bundle, for a person to complete. |
| [`check`](#check) | Records how a person would check a save, then admits that check for a bundle. |
| [`bind-record-checks`](#check) | Attaches reviewed record checks to a compiled bundle, in a new bundle. |
| [`certify`](#check) | Checks a bundle against a policy. |
| [`qualify`](#check) | Manages and runs a bundle's qualification against normal and fault cases. |
| [`propose-qualification`](#check) | Same as `qualify propose`. |
| [`verify-run`](#check) | Reads the system of record and rules on a save that an agent, a script, or a person reported. |
| [`known-ids`](#check) | Admits a system-of-record export as the known-ID list that look-alike identity checks use. |
| [`reconcile`](#check) | Checks that the systems in a prior authorization or claim agree, and reports each mismatch. |
| [`shadow`](#check) | Checks each write an agent makes against the system of record, without blocking it, and writes a report. |
| [`countersign`](#check) | Timestamps, countersigns, and discloses fields of a receipt, and exports a dossier. |
| [`receipt`](#check) | Checks a signed write receipt offline, or exports the keys that check it. |
| [`redact-report`](#check) | Removes session tokens and credentials from a run's `report.json` so it can be signed again. Keeps the original locally. |
| [`local-seal`](#check) | Signs receipts with this computer's key, offline. |
| [`seal`](#check) | Writes an encrypted copy of a bundle using `OPENADAPT_BUNDLE_KEY`. `encrypt` is its new name; `seal` still works. |
| [`admit`](#check) | Reads the public release-admission list. It never signs anything. |
| [`replay`](#run) | Performs every step of a bundle against a real app. Never checks the record. |
| [`run`](#run) | Runs a bundle under a profile, with every gate. |
| [`resume`](#run) | Continues a paused durable run from its last confirmed step. |
| [`approve`](#run) | Records a decision that lets a paused run resume. |
| [`item-approval`](#run) | Lists, approves, or declines the saves a run is waiting on. |
| [`deferred`](#run) | Settles saves that a later report confirms, such as claim acknowledgments or exports. |
| [`approver-grant`](#run) | Signs or checks a grant that lets named agents or systems answer saves. |
| [`explain`](#inspect) | Explains a finished run in plain words, with the next command. |
| [`triage`](#run) | Orders verified saves for review and proposes one batch approval. |
| [`attach-seal`](#run) | Adds Cloud's countersignature to a `VERIFIED` run's receipt. |
| [`bench`](#inspect) | Replays a bundle many times against MockMed and summarizes. |
| [`benchmark`](#inspect) | Compares compiled replay with a computer-use agent on MockMed. The agent side needs an Anthropic API key and costs money. |
| [`silent-saves`](#inspect) | Scores a GUI agent on injected bad saves: how often it reports success while the record is wrong. Runs from a source checkout. |
| [`teach`](#repair) | Turns a fix demonstration for a halted run into a guarded branch. |
| [`teach-branch`](#repair) | Learns a guarded branch from two or more halts fixed the same way. |
| [`teach-authorization`](#repair) | Creates, signs, or checks what a teaching agent may do, signed by a person's approver key. |
| [`repair`](#repair) | Moves a repaired bundle through review, campaigns, approval, staging, canary, and rollback. |
| [`undo`](#repair) | Declares, approves, and runs undo steps for a stopped run, with verification. |
| [`rollback`](#repair) | Qualifies a compensating rollback on a test copy, with a stop before and after every save. |
| [`cleanup`](#repair) | Qualifies the cleanup that leaves a clean screen after a halted item. |
| [`fleet`](#repair) | Sets fleet drift patches, opt-in per app family. |
| [`jit`](#agents) | Reviews, admits, or rejects a draft bundle compiled from a computer-use agent's run. |
| [`compile-agent`](#agents) | Runs a computer-use agent once against `--url`, checks the record it wrote, and compiles the run into a program. It writes to that app, so use a test copy. |
| [`guard`](#agents) | Attaches to an agent's Chromium over CDP, holds each save until the right record is on screen, reads it back, and records the run. |
| [`emit-skill`](#agents) | Writes an Agent Skill for a bundle. |
| [`emit-mcp`](#agents) | Writes a standalone MCP `server.py` for a bundle. |
| [`skill`](#agents) | Binds and qualifies a skill pulled from the registry. |
| [`pull`](#cloud) | Downloads a packaged workflow bundle by name. |
| [`connect`](#cloud) | Claims a pairing and stores the workspace credential in the keychain. |
| [`login`](#cloud) | Checks an ingest token and stores it in the keychain. |
| [`sanitize`](#cloud) | Writes a redacted copy of a recording or bundle. Never changes the original. |
| [`review-sanitized`](#cloud) | Shows the original and the redacted copy side by side in a local viewer. |
| [`approve-sanitized`](#cloud) | Freezes the reviewed copy as an approved archive. |
| [`materialize-approved`](#cloud) | Rebuilds an approved copy from its archive and approval record. |
| [`validate-hosted`](#cloud) | Binds lint, certification, and a local run to a one-time Cloud challenge. |
| [`push`](#cloud) | Uploads an approved archive to Cloud. |
| [`report-break`](#cloud) | Sends a halted run's diagnostic, with no patient data, to Cloud. |
| [`report-run`](#cloud) | Sends a finished run's summary, with no patient data, to Cloud. |
| [`connector`](#cloud) | Enrolls this computer with Cloud and runs Cloud jobs locally. |
| [`console`](#operate) | Serves a local operator page over bundles, runs, and halts. Read-only unless `--allow-actions`. |
| [`business-decisions`](#operate) | Relays typed business decisions on a customer runner. It never resumes or acts. |
| [`serve-execute`](#operate) | Serves the Execute API locally. Its receipts are signed with a local key, not by OpenAdapt Cloud. |
| [`service`](#operate) | Runs the unattended on-prem service, with health checks and restart. |
| [`no-outbound`](#operate) | Lists and edits the allow list for strict no-outbound mode. |
| [`serve-reward`](#operate) | Scores training episodes by reading the system of record. Its receipts are self-signed, not by OpenAdapt Cloud. |

`certify`, `replay`, `run`, and `resume` all accept `--config deploy.yaml`.
`record` and `compile` don't.

## Try it

```bash
openadapt flow demo
openadapt flow tutorial --break-it
openadapt flow demo-record --out rec
```

## Record

```bash
openadapt flow record --url URL --out rec                 # browser
openadapt flow record --out rec                           # this computer's desktop
openadapt flow record --backend citrix --out rec          # Citrix client window
```

With no `--url` and no `--backend`, `record` captures on this OS. Main
options: `--param`, `--secret`, `--identifier`, `--task`, `--window`,
`--window-title`, `--browser-cdp-endpoint`, `--until-cmd`, and the surface
options. See [Record a demonstration](../how-to/record.md).

## Build

```bash
openadapt flow compile rec --out bundle --name NAME [--accept-params A,B | --params-from FILE | --no-confirm-params]
openadapt flow induce rec1 rec2 [...] --out program [--name NAME] [--held-out]
openadapt flow for-each bundle --records FILE --out program [--map COLUMN=PARAM] [--max-iterations N]
openadapt flow compose --child NAME=PATH --child NAME=PATH [--handoff A.x=B.y] [--after NAME=PRED] --out DIR
openadapt flow disambiguate program [--interactive | --answers FILE] [--write]
```

See [Build a program from several demonstrations](../how-to/combine-demonstrations.md).

## Inspect

```bash
openadapt flow visualize bundle [--format html|mermaid|json] [-o FILE] [--profile remote-safe]
openadapt flow explain RUN_DIR
```

`visualize --profile` other than `operator-local` removes recorded text,
values, selectors, and URLs from the view.

## Check

```bash
openadapt flow lint bundle [--strict]
openadapt flow scaffold-verifier rec [-o DIR]
openadapt flow bind-record-checks bundle --binding FILE (--check | -o OUT)
openadapt flow check {mark,show,admit}
openadapt flow verify-run --verify verify.yaml --params task.json --run-record RUN.json --baseline before.json --out DIR
openadapt flow countersign {add,verify,disclose,dossier,timestamp-baseline,exceptions,resolve,close,purge}
openadapt flow certify bundle [--policy clinical-write|permissive|FILE] [--config deploy.yaml]
openadapt flow encrypt bundle -o bundle-encrypted
```

`qualify bundle --verify verify.yaml` runs a whole campaign (`qualify
campaign`). The other `qualify` subcommands: `schema`, `init`, `propose`,
`accept`, `admit-local`, `from-demo`, `inspect`, `explain`, `report`,
`set-identity`, `set-risk`, `trust-runner`, `set-effect`, `label`
(`label list`, `label set`, `label remove`),
`business-decision`, `judgment-cases`, `add-case`, `run`, `run-case`,
`drills`, `add-requalification`, and `certify`. See
[Certify and qualify a workflow](../how-to/certify-and-qualify.md),
[Add record checks](../how-to/record-checks.md), and
[Receipts](receipts.md).

## Run

```bash
openadapt flow replay bundle [--url URL] [--run-dir DIR] [--param K=V]
openadapt flow run bundle --profile standard --config deploy.yaml [--qualification-authority-file FILE]
openadapt flow resume RUN_DIR [--require-approval]
openadapt flow approve RUN_DIR [--approver ID] [--resolution OPTION] [--authorize-uncertain-retry]
openadapt flow item-approval show RUN_DIR
openadapt flow item-approval approve RUN_DIR --request-id ID --request-sha256 SHA --decided-by ID --route ROUTE
openadapt flow item-approval decline RUN_DIR --request-id ID --request-sha256 SHA --decided-by ID --route ROUTE
openadapt flow attach-seal RUN_DIR --execution-id ID
openadapt flow triage {plan,approve-batch,decide,calibrate,estimate,eligibility}
```

Main `run` options: `--profile`, `--config`, `--param`, `--params-file`,
`--worklist`, `--policy`, `--durable`, `--dry-run`, `--approval-mode`,
`--approval-wait`, `--approver-policy`, `--approver-webhook`, `--effects-kind`, `--effects-base-url`,
`--allow-model-grounding`, `--hold-on-halt`, `--browser-cdp-endpoint`,
`--cloud-execution-id`, and the surface options. See
[Run a workflow](../how-to/run.md).

## Repair

```bash
openadapt flow teach RUN_DIR --fix FIX --bundle bundle --out bundle-v2
openadapt flow teach-branch --example RUN_DIR FIX --example RUN_DIR FIX --bundle bundle --out bundle-v2
openadapt flow repair {register,list,show,review,campaign,approve,stage,canary,canary-record,rollback,status}
```

See [Handle a halt](../how-to/handle-a-halt.md).

## Agents

```bash
openadapt flow emit-skill bundle --out DIR
openadapt flow emit-mcp bundle --out server.py
openadapt agent serve [--mode sandbox|attended|production] [--bundles DIR] [--runs-dir DIR] [--config YAML]
openadapt agent emit-skill bundle --out DIR [--include-bundle]
openadapt flow jit {status,review,admit,reject,keygen,register,sign-policy}
```

See [Connect an agent](../how-to/connect-an-agent.md).

## Cloud

```bash
openadapt flow sanitize PATH --kind recording|bundle --out DIR
openadapt flow review-sanitized DIR --original PATH
openadapt flow approve-sanitized DIR --original PATH --reviewer ID
openadapt flow push DIR --kind recording|bundle [--validation-attestation FILE]
openadapt flow pull WORKFLOW [--out DIR] [--list]
```

See [Deploy](../how-to/deploy.md#openadapt-cloud).

## Operate

```bash
openadapt flow connector enroll --control-plane-url URL --enrollment-secret SECRET
openadapt flow connector run --control-plane-url URL
openadapt flow business-decisions serve --runs DIR --runner-config runner.toml --profile production
```

`console` needs the `console` extra, `serve-execute` the `execute` extra,
and `serve-reward` the `reward` extra of `openadapt-flow`.

## Surface options

`record`, `replay`, `run`, `resume`, and `qualify run-case` share these:

| Option | Surface |
|---|---|
| `--backend web\|windows\|macos\|linux\|rdp\|citrix` | Which surface to drive |
| `--url`, `--browser-cdp-endpoint`, `--browser-page-url` | Browser |
| `--agent-url` | Windows, through the Windows agent server (replay and run only) |
| `--macos-app`, `--macos-window-title` | macOS |
| `--linux-app`, `--linux-window-title`, `--linux-allow-physical-input` | Linux (replay and run only) |
| `--rdp-host` | RDP over the network (replay and run only) |
| `--rdp-window`, `--rdp-window-title`, `--rdp-readiness-text` | RDP or Citrix client window |
| `--allow-surface-override` | Run on a different surface than recorded; the report records it |
