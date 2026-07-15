# Deploy on-prem

OpenAdapt is built to run where the data lives. The deterministic replay path
does not call an OpenAdapt-hosted model or control plane; it still uses the
target application and any configured system-of-record verifier. Optional model
tiers can run on your own infrastructure. This guide covers the data-handling
controls for a regulated, on-prem deployment.

## The default is already local

A compiled bundle replays deterministically with no model calls and no
OpenAdapt cloud dependency. The reference backend is a local headless browser.
Application and verifier traffic still follows the endpoints in the deployment
configuration; enforce its boundary at the host and network layers.

## One config wires the deployment

A production run is wired by a single
[`deployment.yaml`](../reference/deployment-config.md) — the backend URL, the
system of record to verify writes against, an optional API actuation tier, the
durable runtime, and the safety policy — read by `certify`, `run`, and `resume`:

```yaml
backend:  { url: https://emr.internal.example.org }
effects:  { kind: fhir, base_url: https://emr.internal.example.org/apis/default/fhir }
runtime:  { durable: true, allow_model_grounding: false }   # zero model-service calls
policy:   { policy: clinical-write }
```

`runtime.allow_model_grounding` defaults to **false**, so the deterministic path
makes no model-service calls unless you deliberately opt in and point the
runtime at an on-prem appliance. Target and verifier traffic still follows this
deployment configuration. See [Run a deployment](run-a-deployment.md).

## PHI scrubbing on the persist and log paths

For regulated deployments, PHI scrubbing on the persist and log paths is
provided by the optional `privacy` extra (Presidio-backed):

```bash
pip install 'openadapt[privacy]'
python -m spacy download en_core_web_sm
export OPENADAPT_FLOW_SCRUB=on          # scrub REPORT.md + logs, fail closed
```

The sanitizer processes `REPORT.md` and console logs. Missing dependencies,
unsupported configuration, and sanitizer errors fail closed, but detector false
negatives remain possible; review output before it crosses a boundary. The
compiled bundle and `report.json` keep literal identifiers on purpose: they are
the identity check and the audit trail, and they are protected by a documented
boundary rather than by redaction. Production images must stage the allowlisted
spaCy model locally rather than downloading a model at runtime.

## The on-prem VLM appliance

If you enable the optional model tiers (grounding, identity veto, state
verification), run them as an [on-prem VLM appliance](../concepts/vlm-appliance.md)
on your own hardware:

```bash
export OPENADAPT_FLOW_VLM_URL='http://your-appliance:8000'
```

The appliance is designed to make no external model calls and not persist
payloads. Enforce those properties with network policy, process configuration,
and retention tests for the actual deployment. Identity crops and full frames
are deliberately **not** scrubbed before the appliance sees them, because the
identity check needs the literal identifier; the control there is the trusted
local boundary and verified retention behavior, not redaction. Unset the URL
and none of the model tiers exist.

## What crosses which boundary

| Artifact | Contains identifiers? | Control |
|---|---|---|
| Compiled bundle | Yes, on purpose | Documented boundary; it is the identity check |
| `report.json` | Yes, on purpose | Documented boundary; it is the audit trail |
| `REPORT.md`, console logs | Sanitizer applied when `OPENADAPT_FLOW_SCRUB=on` | Processing errors fail closed; review for detector misses before egress |
| Identity crops to the appliance | Yes | Trusted local boundary; verify egress and retention controls |
| Deterministic replay path | n/a | No OpenAdapt-hosted dependency; target and verifier traffic remains |

## An air-gapped posture

For the strictest deployments: install with the `privacy` extra, run the
appliance locally (or not at all, keeping the deterministic path only), set
`OPENADAPT_FLOW_SCRUB=on`, and keep bundles and reports inside your environment.
The deterministic path needs no OpenAdapt-hosted service. Restrict target,
verifier, and optional local-model traffic to the destinations the deployment
policy permits.

The repository includes a pilot deployment package with a local directory
queue, systemd path unit, schema-minimized hash-chained audit log, and air-gap checks.
Its maturity is uneven: the container topology needs a prebuilt offline
wheelhouse, full-disk encryption is operator-provisioned, and the signed
`install.sh --update` apply path is a documented stub. Do not present update or
rollback as automated until a site-specific procedure has been implemented and
tested. See the [security and deployment review](security-review.md).

For a managed alternative, see [the hosted option](hosted.md).
