# Configuration and environment variables

OpenAdapt is configured mostly through environment variables. The deterministic
replay path needs none of them; they enable secrets, scrubbing, the optional
model appliance, and effect verification.

## Secrets

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_SECRET_<FIELD>` | Injects the value of a secret field at replay. `<FIELD>` is the recorded field name, upper-cased. A field marked `--secret` (and any `input[type=password]`) is never persisted, so its value **must** be supplied here at replay, or the run fails fast. |

```bash
export OPENADAPT_FLOW_SECRET_PASSWORD='...'
```

See [Parameters and secrets](../guides/parameters-and-secrets.md).

## Privacy and scrubbing

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_SCRUB` | Set to `on` to PHI-scrub `REPORT.md` and console logs on the persist and log path, fail closed. Requires the `privacy` extra (`pip install 'openadapt[privacy]'`) and a spaCy model. |

The compiled bundle and `report.json` keep literal identifiers behind a
documented boundary and are **not** scrubbed by this flag; they are the identity
check and the audit trail. See [Deploy on-prem](../guides/deploy-on-prem.md).

## The on-prem VLM appliance

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_VLM_URL` | Points the runtime at an on-prem VLM appliance. Unset (the default), none of the model tiers exist and the ladder has no grounder rung. Set, the grounding rung, identity veto, and state verifier come online, all fail-safe to halt. |

The appliance makes zero cloud calls. See
[The on-prem VLM appliance](../concepts/vlm-appliance.md).

## Browser provisioning

| Variable | Purpose |
|---|---|
| `OPENADAPT_FLOW_NO_AUTO_INSTALL` | Disables automatic browser provisioning. Set it when you manage the browser yourself (for example, you ran `playwright install chromium` ahead of time in a controlled image). |

## Effect verification against a live system of record

| Variable | Purpose |
|---|---|
| `OPENEMR_FHIR_BASE_URL` | Base URL of a FHIR R4 API for the `FhirEffectVerifier` to read the system of record. |
| `OPENEMR_FHIR_TOKEN` | Bearer token for that FHIR API. |

These enable [effect verification](../concepts/effect-verification.md) against a
real FHIR server. The verifier itself is selected in a
[deployment config](deployment-config.md) (`effects.kind: fhir`) or with the
`--effects-kind` / `--effects-base-url` flags on `replay` / `run`; these
variables supply its endpoint and credentials so they need not sit in the YAML.

## The desktop in-session agent

| Variable | Purpose |
|---|---|
| `OAFLOW_AGENT_TOKEN` | Optional bearer token for the [desktop in-session agent server](../concepts/backends.md#the-in-session-agent-the-session-0-problem). Its `/execute_windows` channel is remote code execution by contract; the server binds to loopback by default, and setting a token requires every request to authenticate. Set it in any PHI deployment that exposes the agent beyond loopback. |

## Connector and runner (target state)

!!! warning "Not yet built"
    These variables belong to the managed runner and the
    [BYOC Connector](../guides/deploy-byoc.md), which are **in progress**. They
    are documented here as the intended surface, not as configuration you can set
    today. See [Connector and runner configuration](connector-config.md).

| Variable | Purpose |
|---|---|
| `OPENADAPT_ENROLL_TOKEN` | One-time enrollment token that binds a BYOC Connector to the control plane (intended). |
| `x-runner-secret` (header, not env) | Shared secret authenticating `enqueue` and `run-callback` between the control plane and a runner (exists for the web runner). |

## Benchmark (agent arm only)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required only for the **agent** arm of `openadapt flow benchmark`. The compiled arm and all normal replay make **no** model calls and need no key. |

!!! warning "The agent arm costs money"
    Only the benchmark's agent arm calls a hosted model. Run it with cost caps.
    Nothing on the product's replay path requires an API key or incurs per-run
    cost.
