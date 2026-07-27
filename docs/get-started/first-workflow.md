# Your first workflow

This walks through compiling a workflow on **your own** web app: record what you
do, compile it, replay it, and read the report. It takes about five minutes and
makes zero model calls. Web is the quickest substrate to start on; the same
record, compile, replay loop drives native Windows, macOS, or Linux applications
and RDP or Citrix sessions by choosing a
[backend](../reference/cli.md#backend).

## Prerequisites

- **Python 3.10-3.12.** The engine declares `requires-python >=3.10,<3.13`.
- **macOS, Linux, or Windows.** This walkthrough selects the Playwright-driven
  browser capability, so it has no OS-specific steps. Its matching Chromium
  provisions automatically on the first web action; native, RDP, and Citrix
  paths do not install it.

Install the CLI if you have not already:

```bash
pip install 'openadapt[browser]'
```

Or use the installer script from the landing page, which installs
[uv](https://docs.astral.sh/uv/) if needed and sets up a persistent
`openadapt` command:

```bash
curl -fsSL https://openadapt.ai/install.sh | sh -s -- browser
```

No web app of your own to record against? No setup needed:
`openadapt flow demo-record --out rec` records the canonical triage task against
the bundled MockMed sample app, and `replay` serves MockMed automatically when
you omit `--url`. The
[complete demo journey](index.md#the-complete-demo-journey) walks that path
end to end.

## 1. Record

`record --url` opens a headed browser pointed at your app and watches what you
do: real clicks, typing, key presses, and scrolls. It writes the same recording
format that `compile` consumes.

```bash
openadapt flow record --url https://your.app --out rec
```

Perform the task once. When you are done, press ++ctrl+c++ or close the browser
window to finish. The recording is written to `rec/`.

!!! tip "Record a clean demonstration"
    Do the task the way you want it replayed: one clear path, no dead ends. The
    compiler treats your demonstration as evidence of intent, so a tidy run
    compiles into a tidy workflow.

## 2. Compile

```bash
openadapt flow compile rec --out bundle --name my-task
```

Compilation turns the recording into a **workflow bundle**: an ordered list of
steps, each carrying the evidence needed to re-find its target (a template crop,
an OCR label, geometry landmarks) and postconditions derived from what the demo
actually changed on screen. Write-shaped clicks (save, submit, create, delete)
are auto-classified as irreversible so they refuse to act on a low-confidence
match.

## 3. Lint

```bash
openadapt flow lint bundle
```

`lint` reports coverage gaps before you trust the bundle: clicks that act with
no identity check, steps that assert nothing, writes that may be
under-classified. Each finding carries a severity. It is advice, not a gate. See
[Write and enforce a policy](../guides/policy-and-certification.md) for the
`certify` gate that refuses an unsafe bundle outright.

## 4. Replay

```bash
openadapt flow replay bundle --url https://your.app
```

Recorded parameter values are the defaults; override any of them with
`--param key=value`. The run is deterministic and local. On the healthy path it
makes zero model calls and finishes in seconds.

## 5. Read the report

Each replay writes a timestamped run directory under `runs/` containing an
illustrated `REPORT.md` and a machine-readable `report.json`. The report tells
you, per step, which rung of the resolution ladder resolved the target, whether
the identity check was armed and what it verified, which postconditions passed,
and any heals that were applied. See [What you get](what-you-get.md) and
[Read and audit run reports](../guides/run-reports.md).

## What is next

- Parameterize a value and inject a secret: [Parameters and secrets](../guides/parameters-and-secrets.md)
- Understand why a step healed or halted: [Governed self-healing](../concepts/self-healing.md)
- Gate a bundle behind a safety policy: [Policy and certify](../concepts/policy-and-certify.md)
