# Configuration and environment variables

OpenAdapt is configured mostly through environment variables. The deterministic
replay path needs none; they enable secrets, scrubbing, the optional model
appliance, and effect verification.

## Secrets

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_SECRET_<FIELD>` | Injects a secret field's value at replay. `<FIELD>` is the recorded field name, upper-cased. A field marked `--secret` (and any `input[type=password]`) is never persisted, so its value **must** be supplied here at replay, or the run fails fast. |

```bash
export OPENADAPT_FLOW_SECRET_PASSWORD='...'
```

See [Parameters and secrets](../guides/parameters-and-secrets.md).

## Privacy and scrubbing

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_SCRUB` | `on` runs the PHI/PII sanitizer over `REPORT.md` and console logs on the persist and log path. Missing dependencies, invalid config, and processing errors fail closed. Requires the `privacy` extra (`pip install 'openadapt[privacy]'`) and the allowlisted spaCy model. |

The compiled bundle and `report.json` keep literal identifiers behind a
documented boundary and are **not** scrubbed by this flag; they are the identity
check and the audit trail. Sanitizer success is no proof that detectors found
every identifier, so review artifacts before egress. See
[Deploy on-prem](../guides/deploy-on-prem.md).

## Encryption at rest

| Variable | Purpose |
|---|---|
| `OPENADAPT_BUNDLE_KEY` | Passphrase used by encrypted bundle saves/loads and durable checkpoints. `run` requires an encrypted bundle by default. |

Encryption is opt-in: inject the key and run `openadapt flow seal SOURCE --out
DESTINATION`; normal compile output is plaintext. The same key encrypts durable
checkpoints written during run/resume. OpenAdapt provides the AEAD mechanism,
not key custody, rotation, or recovery. See the [security and deployment
review](../guides/security-review.md).

## The on-prem VLM appliance

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_VLM_URL` | Points the runtime at an on-prem VLM appliance. Unset (the default): no model tiers exist and the ladder has no grounder rung. Set: the grounding rung, identity veto, and state verifier come online, all fail-safe to halt. |

The appliance is designed not to call external model services; enforce and test
egress for the deployed image. See
[The on-prem VLM appliance](../concepts/vlm-appliance.md).


## Browser provisioning

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_NO_AUTO_INSTALL` | Disables automatic browser provisioning. Set it when you manage the browser yourself (e.g. you ran `playwright install chromium` ahead of time in a controlled image). |

## Hosted connectivity

| Variable | Purpose |
|---|---|
| `OPENADAPT_INGEST_TOKEN` | Token used by `login`, `push`, `validate-hosted`, and `report-break` when no `--token` is passed. The OS keychain is the next preferred token source. |
| `OPENADAPT_FLOW_DEPLOYMENT_KIND` | Default execution lane: `cloud`, `byoc`, or `regulated`. Independent of destination trust. |
| `OPENADAPT_FLOW_DESTINATION_KIND` | Destination trust class: `openadapt-managed`, `customer-managed`, or `local`. |
| `OPENADAPT_FLOW_TRUSTED_HOSTS` | Comma-separated exact HTTPS origins allowed for customer-managed upload. |
| `OPENADAPT_FLOW_AUTO_APPROVE_SANITIZED` | Administrator policy switch for fully covered, stable derivatives. Human review remains the default. |
| `OPENADAPT_FLOW_HOSTED_WORKFLOW_ID` | Opts a halting `replay`/`run` into the best-effort `report-break` hook for this workflow id. Off by default. |
| `OPENADAPT_FLOW_ORG_ID` | Optional organization id carried by the break-report hook. |

Every remote upload requires the approved immutable archive from the sanitation
pipeline. `--attest-non-phi` is deprecated and refused; a declaration is not a
privacy control. Customer-owned endpoints must be HTTPS and exact-origin
allowlisted. Unknown destinations fail closed.

These variables configure the client boundary for OpenAdapt Hosted. See
[Hosted browser execution](../guides/hosted.md).

The hosted control plane separately requires three server-side, comma-separated
allowlists: `RUNTIME_VALIDATION_POLICIES`, `RUNTIME_VALIDATION_RISK_CLASSES`, and
`RUNTIME_VALIDATION_COMPILER_VERSIONS`. The risk-class allowlist normally admits
one or both engine-derived values, `low` and `consequential`; the
compiler-version allowlist must name versions the runner actually deploys. Exact
membership is required. An operator attestation cannot introduce a new policy,
risk class, or compiler version.

## Effect verification against a live system of record

| Variable | Purpose |
|---|---|
| `OPENEMR_FHIR_BASE_URL` | Base URL of a FHIR R4 API for the `FhirEffectVerifier` to read the system of record. |
| `OPENEMR_FHIR_TOKEN` | Bearer token for that FHIR API. |

These enable [effect verification](../concepts/effect-verification.md) against a
real FHIR server. The verifier is selected in a
[deployment config](deployment-config.md) (`effects.kind: fhir`) or with the
`--effects-kind` / `--effects-base-url` flags on `replay` / `run`; these
variables supply its endpoint and credentials, keeping them out of the YAML.

## The desktop in-session agent

| Variable | Purpose |
|---|---|
| `OAFLOW_AGENT_TOKEN` | Optional bearer token for the [desktop in-session agent server](../concepts/backends.md#the-in-session-agent-the-session-0-problem). Its `/execute_windows` channel is remote code execution by contract; the server binds to loopback by default, and a token makes every request authenticate. Set it in any PHI/PII deployment that exposes the agent beyond loopback. |

## Benchmark (agent arm only)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required only for the **agent** arm of `openadapt flow benchmark`. The compiled arm and all normal replay make **no** model calls and need no key. |

!!! warning "The agent arm costs money"
    Only the benchmark's agent arm calls a hosted model. Run it with cost caps.
    Nothing on the product's replay path requires an API key or incurs per-run
    cost.
