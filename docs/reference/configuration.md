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

Browser support has two intentionally separate layers. Install the Playwright
driver only for web workflows with `pip install 'openadapt[browser]'`. The
matching Chromium build downloads lazily on the first web action. Native
desktop, RDP, and Citrix commands neither import Playwright nor trigger a
browser download.

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

## The mobile decision portal

These govern where the [attended decision portal](../concepts/halt-learn-loop.md#where-a-halt-goes-the-attended-decision)
listens and what URL it advertises to a paired phone.

| Variable | Default | Purpose |
|---|---|---|
| `OPENADAPT_PORTAL_INGRESS_MODE` | `loopback` | `loopback` (this computer only) or `customer_ingress` (published through your own HTTPS/VPN ingress). |
| `OPENADAPT_PORTAL_PUBLIC_ORIGIN` | *(unset)* | The exact `https://` origin your reverse proxy, VPN, or ZTNA hostname publishes for this runner. Required for `customer_ingress`. |
| `OPENADAPT_PORTAL_INGRESS_ACKNOWLEDGED` | `false` | Explicit record that your organization operates that ingress and has reviewed protected evidence reaching phones. Required for `customer_ingress`. |
| `OPENADAPT_PORTAL_BIND_HOST` | *(unset)* | Optional **literal IP address** to bind, for when your ingress is not on this host. Left unset, the portal stays on `127.0.0.1` behind a same-host reverse proxy. |
| `OPENADAPT_PORTAL_PORT` | `0` | `0` selects an ephemeral port. |
| `OPENADAPT_PORTAL_CONSOLE_PORT` | `7863` | Loopback port for the supervised attended console the portal relays to. |

!!! warning "Loopback is the default, and a phone cannot reach it"
    Unconfigured, the portal binds `127.0.0.1` and advertises a loopback URL.
    That is a complete, working configuration *on that computer* — the pairing
    screen says a phone cannot reach it rather than minting a link that fails on
    your network. Serving a phone is an explicit decision you make by standing up
    trusted TLS in front of the runner. See
    [Deploy on-prem](../guides/deploy-on-prem.md#reaching-the-decision-portal-from-a-phone).

Every widening step fails closed, and the portal **does not start** on an invalid
combination rather than falling back to something more exposed:

- A wildcard bind address (`0.0.0.0`, `::`, empty, `*`) is refused in **every**
  mode. There is no "bind everything for testing" switch.
- The public origin must be a bare `https://` origin — no plaintext, no path,
  no query, no embedded credentials, and no self-signed bypass.
- `OPENADAPT_PORTAL_BIND_HOST` must be a literal IP, not a hostname, and never
  an unspecified or multicast address.
- `customer_ingress` requires **both** a public origin and the acknowledgement.
- Setting a public origin or bind host while the mode is still `loopback` is an
  error, so a half-finished rollout cannot look configured when it is not.

## Benchmark (agent arm only)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required only for the **agent** arm of `openadapt flow benchmark`. The compiled arm and all normal replay make **no** model calls and need no key. |

!!! warning "The agent arm costs money"
    Only the benchmark's agent arm calls a hosted model. Run it with cost caps.
    Nothing on the product's replay path requires an API key or incurs per-run
    cost.
