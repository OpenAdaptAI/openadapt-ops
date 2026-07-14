# Run a deployment

`replay` is the demo-shaped command: with no `--url` it serves the bundled
sample app, and `--drift` teaches self-healing on it. `run` is the same
execution path wired for a **real deployment** — a backend, effect verification,
API actuation, a durable runtime, and a policy — all from one
[`deployment.yaml`](../reference/deployment-config.md). This guide takes a
certified bundle to a governed production run.

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

## Certify, then run

```bash
openadapt flow certify bundle --config deployment.yaml     # gate on the policy
openadapt flow run     bundle --config deployment.yaml      # execute it
```

`run` uses the identical executor as `replay` (resolution ladder, identity gate,
effect verification, durable checkpoints), framed for production: the
demo-only `--drift` teaching aid is not offered, and the backend URL, system of
record, actuation tier, durability, and policy all come from the config. Direct
flags override individual fields for a single run.

## Verify writes against the system of record

With `effects` configured, each consequential write is
[verified against the real record](../concepts/effect-verification.md), not the
screen. A CONFIRMED verdict proceeds; REFUTED or INDETERMINATE halts. A step that
declares effects while no verifier is configured is a configuration error and
halts — an unverifiable write is never silently accepted.

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
