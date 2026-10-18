---
description: >-
  The deployment file's sections and the environment variables OpenAdapt
  reads, with what each one controls.
---

# Configuration

## The deployment file

One YAML file wires a deployment. `certify`, `replay`, `run`, and `resume`
all read it with `--config deploy.yaml`. Command-line options override single
fields. Every section is optional: an empty file is a valid deployment that
runs locally, checks no records, and makes no outbound calls.

Start from a draft bound to one bundle:

```bash
python -m openadapt_flow.cli_config init bundle --out deploy.yaml
```

`certify` and `run` refuse the draft until every field listed under
`unresolved` is filled. The complete annotated example is
[`deployment.example.yaml`](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/deployment.example.yaml).

Credentials are always the names of environment variables, never values.

### `backend`

Where the app is and how to drive it.

```yaml
backend:
  url: https://app.example.org
  headed: false
  # kind: web | windows | macos | linux | rdp | citrix
```

The surface fields match the command-line surface options in the
[command reference](cli.md#surface-options), for example `macos_app`,
`linux_app`, `rdp_window`, and `browser_cdp_endpoint`.

#### Remote sessions and Citrix

For `kind: rdp` with a local client window, and for `kind: citrix`, these
fields bind the session and guard each input:

| Field | Default | Meaning |
|---|---|---|
| `rdp_window` | none | The exact local client process. Citrix defaults to `Citrix Viewer` on macOS and `wfica32` on Windows. |
| `rdp_window_title` | none | The exact client window title. No match, or more than one, is refused. |
| `rdp_max_frame_age_s` | `10.0` | The oldest screen capture an input may rely on. An older one stops the run before input. |
| `rdp_readiness_text` | none | Stable text that must be on screen before input, such as a menu label. |
| `rdp_readiness_min_ratio` | `0.85` | How closely the text read from the screen must match the readiness text, from `0.0` to `1.0`. |
| `rdp_host`, `rdp_port` (`3389`) | none | A network RDP session instead of a local window. Only for `kind: rdp`. |

Citrix is its own backend, not an alias for RDP. `kind: citrix` makes Flow
build `CitrixWorkspaceBackend`, which binds the local Workspace or Viewer
window and keeps that exact window through a run, a halt, and a resume.

```yaml
backend:
  kind: citrix
  rdp_window: wfica32                         # optional on Windows; the default
  rdp_window_title: Claims - Citrix Workspace # bind one session
  rdp_max_frame_age_s: 3.0
  rdp_readiness_text: Claims queue
  rdp_readiness_min_ratio: 0.90
```

`kind: citrix` rejects `rdp_host`; use `kind: rdp` for a network session.
Governed Citrix `run` and `resume` require a nonblank `rdp_readiness_text`
and refuse before any input without one. Choose text from the application's
own frame, not from a record, so a lock screen, sign-in page, or other
application doesn't match. Pin the window title and qualify the frame age and
match ratio against the real session before any saves.

### `actuation`

Whether a step that has an API binding performs its save through the app's
API instead of the screen. The record check still confirms it.

```yaml
actuation:
  api: false
  base_url: https://app.example.org
  timeout_s: 5.0
```

### `effects`

Where record checks read the saved record. `kind` is one of:

| `kind` | Reads | Main fields |
|---|---|---|
| `none` | Nothing. Standard and Regulated refuse saves. | |
| `rest` | A JSON records document over HTTP | `base_url`, `records_path`, `records_key`, `auth`, `path_params` |
| `graphql` | One read-only GraphQL query | `graphql_query`, `graphql_variables`, `graphql_records_path` |
| `fhir` | A FHIR R4 search | `base_url`, `resource_type`, `search_params`, `search_param_exprs`, `access_token_env` |
| `sql` | One read-only `SELECT` | `sql_query`, `sql_query_params`, `sqlite_database` or `sql_driver` and `sql_connect_args`, `sql_password_env` |
| `file` | A file or SFTP drop | `root`, `file_pattern`, `file_min_size`, `file_mtime_window_s`, `file_content_probe` |
| `email` | A maildir or SMTP capture folder | `root`, `mail_pattern`, `file_mtime_window_s`, `file_content_probe` |
| `document` | A report file whose contents are parsed | `root`, `file_pattern`, `document_format`, `document_field_paths` |
| `document-hash` | A document store, by exact SHA-256 | `root`, `glob` |
| `ui_readback` | The app's record page in a separate, signed-in, read-only browser session | `ui_readback.record_url`, `sign_in`, `row_selector`, `fields`, `identity` |

`auth` takes exactly one of `bearer_env`, `header` with `value_env`, or
`basic_env`. Values that come from run inputs are written
`{param: name}`; fixed values are `{literal: value}`. Any kind can also set
`evidence_redact_fields` or `evidence_keep_fields` to keep field values out
of the evidence, and `timeout_s` and `poll_interval_s`.

Which kinds count as strong enough for each profile is explained in
[How a save is checked](../explanation/verification.md).

### `runtime`

```yaml
runtime:
  profile: regulated          # demo | standard | regulated
  durable: true               # on by default under standard and regulated
  approval_mode: each_item    # each_item | problems_only | not_gated
  allow_model_grounding: false
  pixel_verify_enabled: false
  grounding_model:
    enabled: false
    provider: openai_compatible   # or anthropic
    base_url: "http://vllm.internal:8000/v1"
    model: "qwen2.5-vl-7b-instruct"
    api_key_env: "OPENADAPT_FLOW_GROUNDING_API_KEY"
  phi_grounding_allowlist: ["vllm.internal"]
  phi_egress_attested: false
```

- `allow_model_grounding` is the only switch that lets a model component
  receive screenshots. Configuring `grounding_model` doesn't turn it on.
- When patient-data mode is on, a model endpoint is refused unless its host is
  in `phi_grounding_allowlist`. Public model APIs stay blocked unless
  `phi_egress_attested` is true.
- `pixel_verify_enabled` lets the pixel right-record check confirm a match,
  not only refuse one. Leave it off unless that check was validated for your
  screens.

### `human_decisions`

```yaml
human_decisions:
  remote:
    enabled: false
    # tenant_id: ...
    # runner_id: ...
    # context_tier: remote_closed_context   # or remote_identifiers
```

Off by default, so decisions on paused runs are made at the computer. When
enabled with both ids, the attended console started with `--remote-decisions`
relays a signed decision task with no screenshot and no patient data to
OpenAdapt Cloud, where a signed-in member answers it from a phone.
`context_tier` sets how much the task says about why the run stopped; neither
value can carry an image. See [Answer a halt from a phone](../how-to/answer-from-a-phone.md).

### `policy`

```yaml
policy:
  policy: clinical-write    # clinical-write | permissive | a path to a policy file
```

## Environment variables

| Variable | What it controls |
|---|---|
| `OPENADAPT_FLOW_SECRET_<FIELD>` | The value of a secret field at run time |
| `OPENADAPT_BUNDLE_KEY` | The key for encrypted bundles and checkpoints; required under Regulated |
| `OPENADAPT_FLOW_SCRUB` | Scrubbing of identifiers from saved text: `auto` (default), `on`, or `off`. `on` stops with an error if the scrubber isn't installed. |
| `OPENADAPT_FLOW_PHI_MODE` | Turns patient-data mode on; `OPENADAPT_FLOW_SCRUB=on` also does |
| `OPENADAPT_FLOW_VLM_URL` | The address of an on-site model server |
| `OPENADAPT_FLOW_BROWSER` | Which browser to use: `auto` (default), `chrome`, `msedge`, or `bundled` |
| `OPENADAPT_HOME` | Where OpenAdapt keeps local state (default `~/.openadapt`) |
| `OPENADAPT_AGENT_RUNS_DIR` | The MCP server's runs folder (default `~/.openadapt/runs`) |
| `OAFLOW_AGENT_TOKEN` | The shared token for the Windows agent server |
| `OPENADAPT_INGEST_TOKEN` | The Cloud ingest token, if not in the keychain |
| `OPENADAPT_FLOW_REPORT_RUN` | `1` sends a run summary to Cloud after a successful run, like `--report` |
| `OPENADAPT_CLOUD_EXECUTION_ID`, `OPENADAPT_EXECUTE_API_KEY` | Link a run to a Cloud Execute execution so it can get a Seal |
| `DO_NOT_TRACK=1` or `OPENADAPT_TELEMETRY=0` | Leave the failure signal out of a Cloud connector's run callbacks |
