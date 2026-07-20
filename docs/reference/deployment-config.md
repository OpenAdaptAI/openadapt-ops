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

| Field | Default | Meaning |
|---|---|---|
| `url` | `null` | The GUI URL under automation. `null` lets the command choose its default (`replay`/`run` serve the bundled MockMed demo). |
| `headed` | `false` | Run the browser visible (demo / debugging). |

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

The overrides: `--url` / `--headed` (backend), `--effects-kind` /
`--effects-base-url` / `--effects-root` (effects), `--api-actuator` /
`--api-base-url` (actuation), `--durable` and `--allow-model-grounding`
(runtime). See the [CLI reference](cli.md#run) and the
[Run a deployment](../guides/run-a-deployment.md) guide.
