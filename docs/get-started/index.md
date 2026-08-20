---
description: >-
  Install OpenAdapt, complete a verified local tutorial, and choose the next
  guide for browser, desktop, RDP, Citrix, or production use.
---

# Get started

Start with one complete local result. You do not need to understand the package
layout first. The tutorial records a demonstration, compiles it into a program,
runs the program, and verifies the saved result.

![OpenAdapt records, compiles, and replays a demonstrated workflow](../assets/showcase/demo.gif)

## First success: two commands

You need no account, target application, API key, or operating-system
automation permission:

```bash
python -m pip install --upgrade 'openadapt[browser]'
openadapt quickstart
```

The command records the bundled synthetic MockMed task, compiles its observed
[effect contract](../reference/glossary.md#effect-contract), certifies it with
the shipped clinical-write [policy](../reference/glossary.md#policy), and runs
it under the Standard [profile](../reference/glossary.md#profile). A separate
read-only API confirms the saved record outside the screen that performed the
write. The healthy run returns
[`VERIFIED`](../reference/run-outcomes.md) with no model or Cloud call. OpenAdapt writes all artifacts to
`openadapt-quickstart/` and refuses to overwrite that directory.

You now have:

- `openadapt-quickstart/recording/`: the demonstration and retained target
  evidence;
- `openadapt-quickstart/bundle/`: the inspectable compiled workflow; and
- `openadapt-quickstart/run/REPORT.md`: the ordered actions, evidence, outcome,
  and any halt reason.
- `openadapt-quickstart/run/receipt.json`: a local, privacy-safe summary of the
  synthetic verified run.

Open the report, then inspect the program and its deployment gaps:

```bash
less openadapt-quickstart/run/REPORT.md
openadapt flow visualize openadapt-quickstart/bundle --out graph.html
openadapt flow lint openadapt-quickstart/bundle
```

After the first run, choose the path that matches your goal:

| Goal | Next guide |
|---|---|
| Record one real browser workflow | [Your first workflow](first-workflow.md) |
| Use the Desktop application | [Install Desktop](../desktop/install.md) |
| Use native desktop, RDP, or Citrix | [Install a different execution surface](#install-a-different-execution-surface) |
| Prepare a qualified production run | [Move from demo to deployment](#move-from-demo-to-deployment) |

!!! important "A tutorial result is not production certification"
    The bundled fixture proves that the local product path and its Standard
    verification gates work. It certifies only this bundled synthetic task,
    application, and local system of record. A customer workflow must bind its
    own application, execution surface, action risks, identity checks,
    independent effect verifier, fault cases, and deployment policy.

## See each stage

`openadapt quickstart` runs these five stages for you:

1. It starts the bundled application and its local persistence boundary.
2. It records the synthetic task and observes the record state before and after
   each action.
3. It compiles the observed delta into an explicit effect contract.
4. It applies the shipped `clinical-write` policy and the Standard run gate.
5. It replays the task, confirms the saved record through the independent API,
   and writes the local receipt.

The same gate stops when the required evidence is missing or disagrees with the
screen.

## See a fail-safe halt

Use the compiled tutorial bundle in an ordinary Demo-profile replay. This path
has no independent verifier, so OpenAdapt must not reuse the Standard
`VERIFIED` result:

```bash
openadapt flow replay openadapt-quickstart/bundle \
  --drift modal \
  --run-dir openadapt-quickstart-halt
```

!!! note "Why this command exits 1"
    The command expects a [halt](../reference/glossary.md#halt), so it exits
    `1`. The compiled program has no approved branch for the changed screen
    state and refuses to act. If you see `Replay HALTED`, open
    `openadapt-quickstart-halt/REPORT.md` to see the retained evidence. Do not
    retry a possibly dispatched write; reconcile it against an independent
    system of record first. Every outcome is defined in
    [Run outcomes and halt reasons](../reference/run-outcomes.md).

## Install a different execution surface

The browser extra is only for the browser tutorial. It does not form part of
the lightweight base runtime for native desktop, RDP, or Citrix workflows.

For native or remote-only work, install the selected driver:

```bash
pip install openadapt
pip install 'openadapt[capture,windows]'  # example: native Windows
pip install 'openadapt[capture,rdp]'      # example: network RDP
```

Neither path installs or downloads Chromium. The public command remains
`openadapt flow <verb>` for every surface. The standalone
[`openadapt-flow`](https://github.com/OpenAdaptAI/openadapt-flow) package is for
engine contributors. It is not a second end-user path.

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

!!! note "Why certification can exit 2"
    A failed certification exits `2` and prints each violated requirement.
    OpenAdapt refuses the bundle before deployment. Close the gaps it names (see
    [Write and enforce a policy](../guides/policy-and-certification.md)), then
    re-run `certify` and continue.

Follow [Run a deployment](../guides/run-a-deployment.md), then complete the
[security and deployment review](../guides/security-review.md). Do not promote a
bundle just because the sample-app tour passed. `seal` preserves the source,
refuses symlinks and an existing destination, encrypts the workflow and template
crops, verifies the result, and expires any certification inherited from the
source. Key custody and rotation belong to the deployment.

## After the tutorial

The local runtime also supports these paths:

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
