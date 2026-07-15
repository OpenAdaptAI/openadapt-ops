# Run a deployment

`replay` is the demo-shaped command: with no `--url` it serves the bundled
sample app, and `--drift` demonstrates governed re-resolution on it. `run` is the same
execution path wired for a **real deployment** — a backend, effect verification,
API actuation, a durable runtime, and a policy — all from one
[`deployment.yaml`](../reference/deployment-config.md). This guide takes a
certified bundle to a governed deployment run. Passing this guide does not make
an experimental backend or workflow production-ready.

## One config wires the whole run

Write a `deployment.yaml` (see the [full schema](../reference/deployment-config.md)):

```yaml
name: clinic-triage
backend:
  url: https://emr.internal.example.org
effects:
  kind: fhir
  base_url: https://emr.internal.example.org/apis/default/fhir
  resource_type: Observation
  access_token: "${OPENEMR_FHIR_TOKEN}"
runtime:
  durable: true
policy:
  policy: clinical-write
```

The same file is read by `certify` and `run`, so the bundle is certified against
the policy it will run under.

## Prepare, inspect, then run

`run` is stricter than `replay`: by default it refuses a plaintext bundle,
uncertified policy, unarmed consequential action, write without an effect
contract, unavailable verifier without explicit approval, or broken manifest.
Normal compilation creates a plaintext bundle, so create a production copy and
seal it with the shipped library API before admission:

```bash
cp -R bundle bundle-prod
export OPENADAPT_BUNDLE_KEY='<inject from your secret manager>'
python -c 'from openadapt_flow.ir import Workflow; w=Workflow.load("bundle-prod"); w.save("bundle-prod", encrypt=True)'

openadapt flow certify bundle-prod --config deployment.yaml
openadapt flow run bundle-prod --config deployment.yaml --dry-run
openadapt flow run bundle-prod --config deployment.yaml
```

The `--dry-run` form prints every admission-gate verdict and never executes,
whether it passes or fails. Once admitted, `run` uses the identical executor as
`replay` (resolution ladder, identity gate, effect verification, durable
checkpoints). The demo-only `--drift` teaching aid is not offered, and the
backend URL, system of record, actuation tier, durability, and policy come from
the config. Direct flags override individual fields for a single run.

There is no dedicated `seal` CLI verb yet. `Workflow.save(..., encrypt=True)`
seals workflow JSON and template crops; the key comes from the environment in
this example. Production key custody, rotation, and recovery are operator
responsibilities.

## Verify writes against the system of record

With `effects` configured, each consequential write is
[verified against the real record](../concepts/effect-verification.md), not the
screen. A CONFIRMED verdict proceeds; REFUTED or INDETERMINATE halts. A step that
declares effects while no verifier is configured is refused by `run` unless the
operator explicitly supplies `--approve-unverified-writes`. That fallback is
auditable approval, not independent verification.

You can also wire effects from flags for a quick run:

```bash
openadapt flow run bundle --url https://app.example.org \
  --effects-kind rest --effects-base-url https://app.example.org
```

## Actuate through the API where one exists

Where the target app exposes a real API, driving its GUI to make the write is the
wrong tool. With `actuation.api: true` (or `--api-actuator` / `--api-base-url`), a
step carrying an `ApiBinding` performs the write by calling the API and confirms
it with the same effect verifier, skipping the GUI. It is an optimization whose
safe fallback is always the GUI.

## Durable runs pause and resume

With `runtime.durable: true` (or `--durable`), the run
[checkpoints each verified step](../concepts/durable-runtime.md) and, on a halt,
writes a pending escalation and stops. Approve and resume it without re-running a
confirmed write:

```bash
openadapt flow approve runs/replay-20260712-140233
openadapt flow resume  runs/replay-20260712-140233 --require-approval
```

`resume` rebuilds a live backend from `backend.url` (or `--url`), re-binds the
run's parameters, and continues from the last verified checkpoint.

## Keep it local by default

Nothing above requires the network beyond your own systems of record. The model
tiers stay off unless you set `runtime.allow_model_grounding: true` (or
`--allow-model-grounding`) and point the runtime at an
[on-prem VLM appliance](../concepts/vlm-appliance.md). Left off, the run is fully
local and makes zero outbound model calls — the report says so explicitly. See
[Deploy on-prem](deploy-on-prem.md) for the data-handling boundaries.
