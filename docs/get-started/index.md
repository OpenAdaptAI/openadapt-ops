# Get started

OpenAdapt turns a single demonstration into a deterministic, locally-run
workflow. This section takes you from an empty terminal to a compiled workflow
and an illustrated run report in about five minutes. For a real deployment, pair
the workflow with an explicit substrate, identity policy, effect oracle, and
data boundary.

## Install

```bash
pip install 'openadapt[browser]'
```

This walkthrough selects the browser capability explicitly. Playwright is not
part of the lightweight base runtime used by native desktop, RDP, or Citrix
workflows. The first time you record or replay a web app, the matching Chromium
build provisions automatically. To provision it ahead of time:

```bash
playwright install chromium
```

The public package and command path remains `openadapt` followed by `openadapt
flow <verb>`; extras select only the substrate dependencies you need.
Contributors who work on the engine directly can use
the standalone [`openadapt-flow`](https://github.com/OpenAdaptAI/openadapt-flow)
package; it is not a second end-user onboarding path.

For native or remote-only work, keep the base install and add only the selected
driver:

```bash
pip install openadapt
pip install 'openadapt[capture,windows]'  # example: native Windows
pip install 'openadapt[capture,rdp]'      # example: network RDP
```

Neither path installs or downloads Chromium.

## The complete demo journey

```bash
# 1. Record the canonical demo (serves a local sample app, records a triage task)
openadapt flow demo-record --out rec

# 2. Compile the recording into a workflow bundle
openadapt flow compile rec --out bundle --name my-task

# 3. Check it for coverage gaps
openadapt flow lint bundle

# 4. Refuse it if it violates a safety policy
openadapt flow certify bundle --policy clinical-write

# 5. Replay it: local, deterministic, zero model calls
openadapt flow replay bundle --run-dir runs/baseline

# 6. Induce known drift and save the proposed healed bundle separately
openadapt flow replay bundle --drift theme \
  --run-dir runs/theme-drift --save-healed-to bundle-healed

# 7. Inspect the human and machine-readable evidence
less runs/theme-drift/REPORT.md
python -m json.tool runs/theme-drift/report.json | less

# 8. Prove the saved bundle replays cleanly before promoting it
openadapt flow replay bundle-healed --run-dir runs/healed-canary
```

Steps 5, 6, and 8 serve the bundled sample app and write an illustrated
`REPORT.md` plus `report.json` per run. Step 6 injects a theme the workflow has
never seen; deterministic lower rungs re-resolve the targets and write a
candidate to `bundle-healed`. The original `bundle` is not silently promoted, so
review the diff and canary result first. `lint` and `certify` are the pre-deploy
gate that separates "runnable" from "certified under this policy".

## When a real run halts

The bundled theme drift is a deterministic re-resolution demonstration, not a
general teaching demo. When a real, durable run halts on an unhandled state,
record only the corrective actions and feed the halted run to `teach`:

```bash
# 9. Compile a demonstrated correction through the regression/canary gate
openadapt flow teach runs/<halted-run> \
  --fix recordings/<correction> \
  --bundle bundle \
  --out bundle-v2
```

`teach` writes `bundle-v2` only if the correction is promoted. The shipped
deterministic reference inducer covers the optional-dialog correction class; it
does not generalize arbitrary UI changes. An underdetermined or safety-weakening
correction is refused and the original bundle remains halting.

## Move from demo to deployment

A real deployment must replace demo drift flags with explicit backend, effect,
durability, and policy configuration:

```bash
# 10. Seal an encrypted candidate, then inspect and pass the run gate
export OPENADAPT_BUNDLE_KEY='<inject from your secret manager>'
openadapt flow seal bundle-v2 --out bundle-prod
openadapt flow certify bundle-prod --config deployment.yaml
openadapt flow run bundle-prod --config deployment.yaml --dry-run
openadapt flow run bundle-prod --config deployment.yaml
```

Follow [Run a deployment](../guides/run-a-deployment.md), then complete the
[security and deployment review](../guides/security-review.md). Do not promote a
bundle just because the sample-app tour passed. `seal` preserves the source,
refuses symlinks and an existing destination, encrypts the workflow and template
crops, verifies the result, and expires any certification inherited from the
source. Key custody and rotation belong to the deployment.

## Beyond one demonstration

Once the basic loop makes sense, the same $0 runtime carries more:

- **[Induce a program](../guides/induce-a-program.md)** from several recordings
  (`induce`), and loop it over a data source with `replay --worklist`.
- **[Run a real deployment](../guides/run-a-deployment.md)** (`run`) wired by one
  [`deployment.yaml`](../reference/deployment-config.md): a real backend, effect
  verification against the system of record, an API actuation tier, and a policy.
- **[Durable runs](../concepts/durable-runtime.md)** (`--durable`) turn a halt
  into a pause an operator can `approve` and `resume` from the last verified
  checkpoint.

## Where to go next

<div class="grid cards" markdown>

-   [__Your first workflow__](first-workflow.md)

    Record, compile, and replay on your own app step by step, and read the
    run report.

-   [__What you get__](what-you-get.md)

    The bundle, the run report, and what each artifact is for.

-   [__Qualification evidence__](what-works-today.md)

    Accepted substrate results, exact environments, and deployment boundaries.

-   [__Core concepts__](../concepts/index.md)

    Understand the compiler model before you deploy it for real work.

</div>
