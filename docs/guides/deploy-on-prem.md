# Deploy on-prem

OpenAdapt is built to run where the data lives. The deterministic replay path
makes zero network calls, and the optional model tiers run on your own
infrastructure. This guide covers the data-handling controls for a regulated,
on-prem deployment.

## The default is already local

A compiled bundle replays deterministically with no model calls and no cloud
dependency. The reference backend is a local headless browser. For most of a
workflow, "on-prem" is simply the default: nothing leaves the machine.

## One config wires the deployment

A production run is wired by a single
[`deployment.yaml`](../reference/deployment-config.md) — the backend URL, the
system of record to verify writes against, an optional API actuation tier, the
durable runtime, and the safety policy — read by `certify`, `run`, and `resume`:

```yaml
backend:  { url: https://emr.internal.example.org }
effects:  { kind: fhir, base_url: https://emr.internal.example.org/apis/default/fhir }
runtime:  { durable: true, allow_model_grounding: false }   # zero outbound calls
policy:   { policy: clinical-write }
```

`runtime.allow_model_grounding` defaults to **false**, so the deterministic path
makes zero outbound calls unless you deliberately opt in and point the runtime at
an on-prem appliance. See [Run a deployment](run-a-deployment.md).

## PHI scrubbing on the persist and log paths

For regulated deployments, PHI scrubbing on the persist and log paths is
provided by the optional `privacy` extra (Presidio-backed):

```bash
pip install 'openadapt[privacy]'
python -m spacy download en_core_web_trf
export OPENADAPT_FLOW_SCRUB=on          # scrub REPORT.md + logs, fail closed
```

The shareable `REPORT.md` and console logs are scrubbed. The compiled bundle and
`report.json` keep literal identifiers on purpose: they are the identity check
and the audit trail, and they are protected by a documented boundary rather than
by redaction.

## The on-prem VLM appliance

If you enable the optional model tiers (grounding, identity veto, state
verification), run them as an [on-prem VLM appliance](../concepts/vlm-appliance.md)
on your own hardware:

```bash
export OPENADAPT_FLOW_VLM_URL='http://your-appliance:8000'
```

The appliance makes **zero cloud calls** and retains nothing. Identity crops and
full frames are deliberately **not** scrubbed before the appliance sees them,
because the identity check needs the literal identifier; the control there is
on-prem-only plus no-retention, not redaction. Unset the URL and none of the
model tiers exist.

## What crosses which boundary

| Artifact | Contains identifiers? | Control |
|---|---|---|
| Compiled bundle | Yes, on purpose | Documented boundary; it is the identity check |
| `report.json` | Yes, on purpose | Documented boundary; it is the audit trail |
| `REPORT.md`, console logs | Scrubbed when `OPENADAPT_FLOW_SCRUB=on` | Presidio scrubbing, fail closed |
| Identity crops to the appliance | Yes | On-prem only, no retention |
| Deterministic replay path | n/a | No network calls at all |

## An air-gapped posture

For the strictest deployments: install with the `privacy` extra, run the
appliance locally (or not at all, keeping the deterministic path only), set
`OPENADAPT_FLOW_SCRUB=on`, and keep bundles and reports inside your environment.
The system was designed so that the deterministic path never needs the network,
and the only model that can see a record is one you host.

The repository includes a pilot deployment package with a local directory
queue, systemd path unit, hash-chained PHI-free audit log, and air-gap checks.
Its maturity is uneven: the container topology needs a prebuilt offline
wheelhouse, full-disk encryption is operator-provisioned, and the signed
`install.sh --update` apply path is a documented stub. Do not present update or
rollback as automated until a site-specific procedure has been implemented and
tested. See the [security and deployment review](security-review.md).

For a managed alternative, see [the hosted option](hosted.md).
