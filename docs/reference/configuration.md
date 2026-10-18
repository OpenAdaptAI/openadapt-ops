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

Credentials are names of environment variables, except the three backend
fields marked below, which hold values. Keep a file that sets them as private
as the credentials.

### `backend`

Where the app is and how to drive it.

```yaml
backend:
  url: https://app.example.org
  headed: false
  # kind: web | windows | macos | linux | rdp | citrix
```

| Field | For | Meaning |
|---|---|---|
| `kind` | all | `web` (default), `windows`, `macos`, `linux`, `rdp`, or `citrix` |
| `url`, `headed` | `web` | The app's address, and whether the browser is visible (default `false`) |
| `browser_cdp_endpoint` | `web` | A loopback DevTools address of a running, signed-in Chrome, such as `http://127.0.0.1:9222`. The run attaches to its one tab on the `url` origin and detaches afterwards. |
| `browser_page_url` | `web` | The exact address of the tab to bind when more than one is on the origin |
| `agent_url` | `windows` | The Windows agent's address. Required. |
| `agent_token` | `windows` | The agent's shared token. A value. |
| `agent_tls_pin` | `windows` | SHA-256 fingerprint of the agent's TLS certificate. Any other certificate fails the connection. |
| `macos_app`, `macos_window_title` | `macos` | The owning app (required), and a title that picks one window. Ambiguous matches are refused. |
| `linux_app`, `linux_window_title` | `linux` | The exact accessibility app name and window title. Both required. |
| `linux_allow_physical_input` | `linux` | Allow pointer and keyboard input bound to the window when the target has no accessibility action (default `false`) |
| `rdp_host`, `rdp_port`, `rdp_domain` | `rdp` | A network RDP session (port default `3389`) |
| `rdp_username`, `rdp_password` | `rdp` | The session's sign-in. Values. |

The same fields are command-line options; see the
[command reference](cli.md#surface-options).

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
| `rdp_application_marker`, `rdp_application_version_marker`, `rdp_environment_marker`, `rdp_session_marker` | none | Stable text read from the session for qualification, such as the application name and version. Compared with the qualified environment, not kept in evidence. |
| `remote_frame_contract` | none | Regions of the session's screen that change on their own, such as a clock, left out when OpenAdapt checks that the screen has settled |

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

A `remote_frame_contract` names the exact frame size and its regions as
`[x, y, width, height]`:

```yaml
backend:
  remote_frame_contract:
    schema_version: openadapt.remote-frame-contract/v1
    frame_width: 1920
    frame_height: 1080
    volatile_regions: [[1780, 1040, 140, 40]]   # the session clock
    protected_regions: []                       # never masked
```

A size that doesn't match the live frame, or a changing region that overlaps
a target, an identity check, or a record check, stops the run before input.

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
| `onscreen` | The saved value on the acting screen, read with OCR | `readback_region`, `readback_min_ratio` (default `0.9`) |
| a plugin kind | Whatever the installed verifier reads | `options`, `option_params`, `secret_env` |

`auth` takes exactly one of `bearer_env`, `header` with `value_env`, or
`basic_env`. Values that come from run inputs are written
`{param: name}`; fixed values are `{literal: value}`. Any kind can also set
`evidence_redact_fields` or `evidence_keep_fields` to keep field values out
of the evidence, and `timeout_s` and `poll_interval_s`.

A plugin's `options` hold plain settings; a key that names a credential,
such as `password`, is refused. Put credentials in `secret_env`, which maps
a slot name to an environment variable name.

To offer more than one read, list them under `candidates` instead of `kind`.
OpenAdapt builds every candidate before input and uses the strongest one; it
never switches to another after the save:

```yaml
effects:
  candidates:
    - kind: file
      root: /exports/claims
      file_pattern: "claim-*.json"
    - kind: document
      root: /exports/reports
      file_pattern: "*.json"
      document_format: json
```

Which kinds count as strong enough for each profile is explained in
[How a save is checked](../explanation/verification.md).

### `identity` and `idempotency`

```yaml
identity:
  require_fresh_frame: true          # check identity on a fresh screen capture
  record_id_env: OPENADAPT_RECORD_ID # the variable that holds the record id
idempotency:
  key_env: OPENADAPT_IDEMPOTENCY_KEY # the variable that holds the run's idempotency key
```

Both name environment variables; the file never holds a record id or a key.

### `runtime`

```yaml
runtime:
  profile: regulated          # demo | standard | regulated
  durable: true               # on by default under standard and regulated
  approval_mode: each_item    # each_item | problems_only | not_gated
  require_settled: false      # forced on under standard and regulated
  layout_drift_check: null    # null: on for rdp and citrix, off elsewhere
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
- `require_settled` waits for a settled screen before every action.
- `layout_drift_check` compares the screen's resolution, fonts, and layout
  with the recording before each recorded click, and stops the run when they
  differ, for example `font_size_changed` or `landmark_missing`. Bundles
  compiled before 2.2.0 carry no fingerprint and need recompiling to use it.
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
value can carry an image. `peer_task_schemas` lists the task versions the
hosted side accepts. See [Answer a halt from a phone](../how-to/answer-from-a-phone.md).

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
| `OPENADAPT_FLOW_VLM_URL`, `OPENADAPT_FLOW_VLM_TOKEN`, `OPENADAPT_FLOW_VLM_TIMEOUT` | The address of an on-site model server, its bearer token, and the request timeout in seconds (default `2.0`) |
| `OPENADAPT_FLOW_BROWSER` | Which browser web runs use: `auto` (default: installed Chrome, then Edge, then Playwright's Chromium), `chrome`, `msedge`, or `bundled` |
| `OPENADAPT_FLOW_NO_AUTO_INSTALL` | `1` skips the Chromium download when no installed browser is used, for computers without internet access |
| `OPENADAPT_FLOW_OCR` | The OCR engine: `auto` (default, RapidOCR), `rapidocr`, or `native` (Apple Vision or Windows OCR, with the `native-ocr` extra) |
| `OPENADAPT_HOME` | Where OpenAdapt keeps local state (default `~/.openadapt`) |
| `OPENADAPT_AGENT_RUNS_DIR` | The MCP server's runs folder (default `~/.openadapt/runs`) |
| `OAFLOW_AGENT_TOKEN` | The shared token for the Windows agent server, and for `openadapt agent serve --windows-agent-url` |
| `OAFLOW_AGENT_CERTFILE`, `OAFLOW_AGENT_KEYFILE` | The Windows agent server's TLS certificate and key |
| `OPENADAPT_AGENT_SANDBOX_DIR` | The MCP server's sandbox folder (default `~/.openadapt/agent-sandbox`) |
| `OPENADAPT_AGENT_BUNDLES_DIR`, `OPENADAPT_AGENT_ALLOW_RUN`, `OPENADAPT_AGENT_ALLOW_ATTENDED_ACTIONS`, `OPENADAPT_AGENT_DEPLOYMENT_CONFIG`, `OPENADAPT_AGENT_POLICY`, `OPENADAPT_AGENT_HEADED`, `OPENADAPT_AGENT_BUNDLE_KEY` | Settings for the MCP server when it's installed as a desktop extension; each maps to the matching `serve` option, and the key to `OPENADAPT_BUNDLE_KEY` |
| `OPENADAPT_APPROVER_WEBHOOK_SECRET` | The key that signs approval requests sent to `--approver-webhook` |
| `OPENADAPT_SEAL_KEYS_PATH`, `OPENADAPT_SEAL_KEYS_JSON` | Pinned Seal keys, as a file or inline JSON (default `~/.openadapt/seal-keys.json`) |
| `OPENADAPT_COUNTERSIGN_VAULT` | Where `countersign` keeps field values and salts (default `~/.openadapt/countersign-vault`) |
| `OPENADAPT_EXCEPTION_RETENTION_DAYS` | How long closed exceptions are kept (default 2,190, at least 183) |
| `OPENADAPT_INGEST_TOKEN` | The Cloud ingest token, if not in the keychain |
| `OPENADAPT_FLOW_REPORT_RUN` | `1` sends a run summary to Cloud after a successful run, like `--report` |
| `OPENADAPT_CLOUD_EXECUTION_ID`, `OPENADAPT_EXECUTE_API_KEY` | Link a run to a Cloud Execute execution so it can get a Seal |
| `DO_NOT_TRACK=1` or `OPENADAPT_TELEMETRY=0` | Leave the failure signal out of a Cloud connector's run callbacks |
