---
description: >-
  Run a synthetic task twice: once against an honest app and once against an
  app that shows "saved" and drops the write. See why only the second run
  stops.
---

# Quickstart: watch a run refuse a false success

In this tutorial you run one compiled workflow twice against a synthetic
clinic app on your computer. The first run saves a note and confirms it. The
second run gets a "saved" message from the app, but the server has dropped the
write. OpenAdapt notices and stops.

You need about five minutes and a network connection for the first install.
You don't need an account, an API key, or an application of your own.

## Run it

With [uv](https://docs.astral.sh/uv/getting-started/installation/) installed:

```bash
uvx --python 3.12 openadapt quickstart --break-it
```

uv downloads Python 3.12 for this command if you don't have it. Without uv,
use Python 3.10, 3.11, or 3.12:

```bash
python -m pip install --upgrade openadapt
openadapt quickstart --break-it
```

On the first browser step, OpenAdapt asks Playwright to download its Chromium
build. On a minimal Linux host, run `openadapt doctor --backend web` first. It
lists any missing system libraries and the command that installs them.

## What happens

The command writes everything under `openadapt-quickstart/` in the current
directory (`openadapt-quickstart-2`, `-3`, and so on if that folder exists).
It runs five stages, then the fault run:

```text
[1/5] Record the demonstration against a real persistence boundary
[2/5] Compile and propose a fixture-specific effect contract
      2 system-of-record effect proposal(s) derived from the fixture's record delta on step_005; review is required for a real deployment
[3/5] Certify against the clinical-write policy
[4/5] Admit and execute under the standard profile
      VERIFIED in 4.3s; 0 model calls; the system of record holds 1 record(s)
[5/5] Emit the local run receipt
```

1. **Record.** A scripted demonstration adds a triage note in MockMed, the
   bundled synthetic app.
2. **Compile.** The recording becomes a workflow program in
   `openadapt-quickstart/bundle/`. The compiler also proposes two record
   checks for the save step, from what the demonstration changed in the app's
   data.
3. **Certify.** The program is checked against `clinical-write`, the strict
   built-in policy.
4. **Admit and run.** The program runs under the Standard profile. After the
   save, it reads the record back through MockMed's read-only API, which the
   screen doing the work never touches.
5. **Receipt.** The run writes a receipt you can share.

The clean run ends like this:

```text
Result: Done and checked. It saved the entry and read the record back to confirm it.
VERIFIED: openadapt-quickstart/run/REPORT.md
  transaction     VERIFIED
  profile         standard
  model calls     0
  effects         2/2 confirmed by an independent system-of-record read (Seal Oracle tier 2)
```

Then the same certified program runs again, against a server that rejects the
write after the app has shown its success message:

```text
  The screen claimed:  every on-screen check passed -- the app painted its success banner
  The verifier found:  1/2 declared effect(s) REFUTED by an independent
                       read of the system of record, which holds 0 record(s)
  The engine did:      HALTED at the consequential step instead of claiming
                       success (transaction: RECONCILIATION_REQUIRED, billable: no)
  Result:              Check the record. A save may have gone through. A person checks the record before anything is retried.
```

The output above is from `openadapt` 1.17.0 with `openadapt-flow` 2.1.0 on
macOS, run on 17 October 2026, with paths shortened and some lines left out.

## Why the second run stops

Both runs see the same screen. The only difference is what the record check
finds. In the second run the check reads the app's data and finds no new
note, so OpenAdapt doesn't report success.

It also doesn't retry. The outcome is `RECONCILIATION_REQUIRED`: the program
can't prove whether a write landed, so a person checks the record first. A
retry could create a duplicate. [Run outcomes](../reference/outcomes.md)
lists every outcome and what a caller may do after each one.

## Look at what it wrote

```text
openadapt-quickstart/
  recording/          the demonstration
  bundle/             the compiled program (workflow.json, manifest.json, ...)
  run/                the clean run: REPORT.md, report.json, receipt.json, receipt.png
  run-broken/         the fault run: REPORT.md, report.json
```

Ask OpenAdapt to explain the fault run in plain language:

```bash
openadapt flow explain openadapt-quickstart/run-broken
```

It names the step that stopped, why stopping was the safe result, and what to
do next. Only the clean run gets a receipt: a receipt is only written for a
`VERIFIED` run.

See the program the demonstration compiled into, as a diagram:

```bash
openadapt flow visualize openadapt-quickstart/bundle --format mermaid
```

## Next steps

- [Automate your first workflow](first-workflow.md) on your own application.
- [How a save is checked](../explanation/verification.md) explains the record
  check and why the screen isn't enough.
- [Connect an agent](../how-to/connect-an-agent.md) to call a workflow as one
  tool.
