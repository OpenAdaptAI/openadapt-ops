# Get started

OpenAdapt turns a single demonstration into a deterministic, locally-run
workflow. This section takes you from an empty terminal to a compiled workflow
and an illustrated run report in about five minutes.

## Install

```bash
pip install openadapt
```

The reference backend is a headless browser. The first time you record or
replay against a web app, the browser provisions automatically. To provision it
ahead of time:

```bash
playwright install chromium
```

!!! note "Package names during the transition"
    The product is moving to a single `openadapt` dispatcher, so the primary
    command is `openadapt flow <verb>`. The engine also ships today as its own
    package, `openadapt-flow`, whose command is `openadapt-flow <verb>`. Every
    example in these docs uses the unified `openadapt flow` form; drop the space
    (`openadapt-flow`) if you installed the standalone package.

## The one-minute tour

```bash
# 1. Record the canonical demo (serves a local sample app, records a triage task)
openadapt flow demo-record --out rec

# 2. Compile the recording into a workflow bundle
openadapt flow compile rec --out bundle --name my-task

# 3. Check it for coverage gaps
openadapt flow lint bundle

# 4. Refuse it if it violates a safety policy
openadapt flow certify bundle --policy clinical-write

# 5. Replay it: local, deterministic, $0
openadapt flow replay bundle

# 6. Drift the UI and watch it heal
openadapt flow replay bundle --drift theme
```

Steps 5 and 6 serve the bundled sample app and write an illustrated
`REPORT.md` for each run. Step 6 injects a theme the workflow has never seen;
each step re-resolves through OCR or geometry and each fix is written back to
the bundle as a reviewable diff, with **zero model calls** on either run.
`lint` and `certify` are the pre-deploy gate that makes a bundle "runnable"
distinct from "certified safe".

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

-   [__Desktop quickstart (Windows)__](desktop-quickstart.md)

    The same compiler against a native Windows or Citrix desktop (target
    state).

-   [__What you get__](what-you-get.md)

    The bundle, the run report, and what each artifact is for.

-   [__Core concepts__](../concepts/index.md)

    Understand the compiler model before you deploy it for real work.

</div>
