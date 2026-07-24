# Deployment configuration

A compiled bundle is portable, but *running it in production* needs
deployment-specific wiring the bundle deliberately omits: which GUI to drive,
which system of record to verify writes against, whether an API actuation tier
exists, whether the run is durable, and which policy certifies it.
`deployment.yaml` is the documented schema for that wiring.

`record`, `compile`, `certify`, `replay`, `run`, and `resume` all read it (via
`--config`), so one file drives every stage. Direct CLI flags override individual
fields.

!!! note "Every section is optional"
    An empty file is a valid deployment: fully local, GUI-only, no effect
    verification, non-durable, no model-service calls. Add only the sections you
    need. The loader validates the YAML against the schema and fails loudly on an
    unknown field or a missing required value, rather than wiring a broken run.

## The full schema

```yaml
name: mockmed-triage-demo          # audit / logs only

# -- backend: where/how to drive the target application's GUI ---------------
backend:
  kind: web                       # web | windows | macos | linux | rdp | citrix
  url: http://localhost:8080       # GUI under automation; omit to use the
                                   # command's default (replay serves MockMed)
  headed: false                    # true => a visible browser (demo/debugging)

# -- actuation: the API/tool tier (top of the capability ladder) ------------
# When api=true, a step carrying an ir.ApiBinding is PERFORMED via the API
# (deterministic, $0, no GUI) and confirmed by the effects verifier below.
actuation:
  api: false
  base_url: http://localhost:8080  # base for relative ApiBinding url_templates
  timeout_s: 5.0

# -- effects: the system of record consequential writes verify against ------
# kind: none | rest | fhir | document-hash
effects:
  kind: rest

  # rest (JSON REST system of record, e.g. MockMed /api/db)
  base_url: http://localhost:8080
  records_path: /api/db
  records_key: records

  # fhir (FHIR R4 search, e.g. OpenEMR), used when kind: fhir
  # base_url: https://openemr.example.org/apis/default/fhir
  # resource_type: Observation
  # search_params: { patient: "Patient/123", category: vital-signs }
  # field_paths: { note: "valueString" }
  # access_token: "${OPENEMR_FHIR_TOKEN}"     # supply via env in production
  # verify_tls: true

  # document-hash (filesystem document store), used when kind: document-hash
  # root: /var/lib/exports
  # glob: "**/*.pdf"

  timeout_s: 5.0
  poll_interval_s: 0.2

# -- runtime: durability + model-egress posture -----------------------------
runtime:
  durable: true                    # checkpoint each verified step; durably
                                   # PAUSE on halt; resume via `resume`
  allow_model_grounding: false     # EGRESS OPT-IN (PHI audit REM-3). Off =>
                                   # no model-service egress. Target and effect-
                                   # verifier traffic remains deployment-defined.

# -- policy: the safety policy that certifies this bundle -------------------
policy:
  policy: clinical-write           # a YAML path, or a built-in name
                                   # (permissive, clinical-write)
```

## Sections

### `backend`

`kind` selects the substrate the runner drives; every substrate runs the same
bundle, resolution ladder, and gates behind one
[backend protocol](../concepts/backends.md). `url` and `headed` are **web-only**;
each other substrate targets through its own field in place of `url`.

| Field | Default | Meaning |
|---|---|---|
| `kind` | `web` | Substrate to drive: `web` (Playwright/Chromium), `windows` (native Windows via the in-session agent), `macos` (a native macOS app window), `linux` (an exact AT-SPI app window), `rdp` (network RDP or a bound local remote-display window), or `citrix` (the dedicated Citrix Workspace/Viewer window backend). |
| `url` | `null` | **`web` only.** The GUI URL under automation. `null` lets the command choose its default (`replay`/`run` serve the bundled MockMed demo). |
| `headed` | `false` | **`web` only.** Run the browser visible (demo / debugging). |
| `agent_url` | `null` | **`windows`.** Base URL of the in-guest agent (e.g. `http://localhost:5001`). Required for `kind: windows`. `agent_token` / `agent_tls_pin` authenticate and pin it. |
| `macos_app` | `null` | **`macos`.** Owner application name or substring. Required for `kind: macos`; `macos_window_title` disambiguates a multi-window app. |
| `linux_app` | `null` | **`linux`.** Exact AT-SPI application name. Required for `kind: linux`, along with `linux_window_title`. |
| `linux_window_title` | `null` | **`linux`.** Exact AT-SPI top-level window title. Required for `kind: linux`; zero or multiple matches are refused. |
| `linux_allow_physical_input` | `false` | **`linux`.** Explicitly permits window-bound X11 input when native AT-SPI actuation is unavailable. |
| `rdp_host` | `null` | **`rdp` network mode.** Host/IP for a network RDP session. Required for network `kind: rdp`; never use it with `kind: citrix`. |
| `rdp_username` / `rdp_password` / `rdp_domain` | `null` | **`rdp` network mode.** Credentials passed to the RDP transport. Keep secrets out of committed YAML and inject them at the deployment boundary. |
| `rdp_port` | `3389` | **`rdp` network mode.** Remote Desktop port. |
| `rdp_window` | `null` | **`rdp` local-window or `citrix`.** Exact local client owner/process. Citrix defaults to the host OS's Workspace/Viewer owner, but a deployment can pin it explicitly. |
| `rdp_window_title` | `null` | **`rdp` local-window or `citrix`.** Exact client-window title used to bind one session. Zero or multiple matches are refused. Pin this in a governed deployment when more than one session can exist. |
| `rdp_max_frame_age_s` | `10.0` | **`rdp` or `citrix`.** Maximum age of the captured frame that established a coordinate/input lease. A stale frame halts before input. Choose and qualify a deliberate positive value for the deployment. |
| `rdp_readiness_text` | `null` | **`rdp` or `citrix`.** Stable text that must be visible on the current frame before input. Governed Citrix `run` and `resume` require a nonblank value and refuse before actuation when it is absent. |
| `rdp_readiness_min_ratio` | `0.85` | **`rdp` or `citrix`.** OCR similarity threshold for the readiness marker, from `0.0` to `1.0`. |

### Citrix Workspace configuration

Citrix is a dedicated backend, not an alias for generic RDP. Set
`kind: citrix` so Flow constructs `CitrixWorkspaceBackend`, binds the local
Workspace/Viewer window, and carries that closed target through governed run,
halt, and durable resume.

```yaml
backend:
  kind: citrix
  rdp_window: wfica32                         # Windows; host default is used if omitted
  rdp_window_title: Claims - Citrix Workspace # exact session binding
  rdp_max_frame_age_s: 3.0                   # refuse stale coordinate leases
  rdp_readiness_text: Claims queue            # required by governed run/resume
  rdp_readiness_min_ratio: 0.90
```

On macOS, the default Citrix owner is `Citrix Viewer`; on Windows it is
`wfica32`. An explicit owner is optional when the platform default is correct.
For a governed deployment, use an exact title whenever multiple Workspace
sessions can exist, set the required readiness marker to stable application
chrome (not record-specific data), and qualify the frame-age and OCR thresholds
against the actual session. `kind: citrix` rejects `rdp_host`; use `kind: rdp`
for a network RDP transport.

!!! important "Governed Citrix deployment profile"
    Treat `rdp_window_title`, `rdp_max_frame_age_s`, and
    `rdp_readiness_text` as required deployment safety inputs: the exact title
    binds the intended session, the positive frame-age limit refuses stale
    coordinates, and the stable readiness marker rejects lock, login,
    disconnect, or wrong-application screens. Flow enforces a nonblank
    readiness marker for governed Citrix `run` and `resume`; deployment review
    must also pin and qualify the title and frame-age value before writes.

### `actuation`

The API/tool tier, the top of the [capability ladder](../concepts/capability-ladder.md).
When `api: true`, a step carrying an `ApiBinding` performs its write via the API
(deterministic, `$0`, no GUI) and confirms it with the effect verifier, skipping
the GUI resolve/act for that step. Its safe fallback is always the GUI.

| Field | Default | Meaning |
|---|---|---|
| `api` | `false` | Wire the API actuator. |
| `base_url` | `""` | Base URL for relative `ApiBinding.url_template`s. |
| `timeout_s` | `5.0` | Per-call timeout. |

### `effects`

Which [system of record](../concepts/effect-verification.md) consequential
writes are verified against. `kind: none` (the default) wires no verifier: a
bundle declaring no effects replays as before, but a step that **does** declare
effects then **halts**. An unverifiable consequential write is never silently
accepted.

| `kind` | System of record | Required fields |
|---|---|---|
| `none` | (no verifier) | none |
| `rest` | a JSON REST endpoint | `base_url` (plus `records_path`, `records_key`) |
| `fhir` | a FHIR R4 API | `base_url` (plus `resource_type`, `search_params`, optional `field_paths`, `access_token`, `verify_tls`) |
| `document-hash` | a filesystem document store | `root` (plus `glob`) |

Shared: `timeout_s` (default `5.0`), `poll_interval_s` (default `0.2`).

### `runtime`

| Field | Default | Meaning |
|---|---|---|
| `durable` | `false` | The Tier-3 [durable runtime](../concepts/durable-runtime.md): checkpoint each verified step, durably pause on halt, resume via `resume`. |
| `allow_model_grounding` | `false` | **Model-egress opt-in** (PHI audit REM-3). Off => no model-service calls; target and effect-verifier traffic remains deployment-defined. On => permit wiring an off-box model grounder / identity-VLM / state-verifier; screenshots may leave the box. |

### `policy`

| Field | Default | Meaning |
|---|---|---|
| `policy` | `null` | A policy YAML path, or a built-in name (`permissive`, `clinical-write`). `certify` reads this when `--policy` is omitted, so one file both certifies and runs the bundle. |

## Flags override the file

Direct CLI flags override individual fields, so a config sets the baseline and a
flag tweaks one run:

```bash
# config supplies backend.url, effects, policy; flag forces a durable run
openadapt flow run bundle --config deployment.yaml --durable
```

The overrides: `--backend` / `--url` / `--headed` / `--agent-url` /
`--macos-app` / `--macos-window-title` / `--linux-app` /
`--linux-window-title` / `--linux-allow-physical-input` / `--rdp-host` /
`--rdp-window` / `--rdp-window-title` / `--rdp-readiness-text` (backend),
`--effects-kind` /
`--effects-base-url` / `--effects-root` (effects), `--api-actuator` /
`--api-base-url` (actuation), `--durable` and `--allow-model-grounding`
(runtime). See the [CLI reference](cli.md#run) and the
[Run a deployment](../guides/run-a-deployment.md) guide.
