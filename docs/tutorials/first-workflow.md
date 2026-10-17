---
description: >-
  Record a read-only task in a test copy of your own web app, compile it,
  inspect the program, and replay it.
first_workflow_scope: read_only
first_write_admission: qualification_required
---

# Automate your first workflow

In this tutorial you record a short task in your own web application, compile
it into a workflow program, read what it compiled into, and replay it. You'll
use a task that only reads data, so nothing you do here can change a record.
Workflows that save data need a record check and qualification first; the
last section points to those guides.

You need:

- Python 3.10, 3.11, or 3.12.
- A test or staging copy of a web application you can sign in to.
- A short task in it that doesn't save anything, such as opening a test
  record and viewing one field.

The same steps work for Windows, macOS, and Linux apps, and for RDP and
Citrix sessions, with a different recording command. See
[Record a demonstration](../how-to/record.md).

## 1. Install

=== "macOS and Linux"

    ```bash
    python3 -m venv .venv && source .venv/bin/activate
    python -m pip install --upgrade openadapt
    openadapt doctor --backend web
    ```

=== "Windows PowerShell"

    ```powershell
    py -m venv .venv; .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade openadapt
    openadapt doctor --backend web
    ```

`doctor` checks that the engine and the browser driver are installed. It
also lists any system libraries Chromium needs on Linux.

## 2. Record the task

```bash
openadapt flow record --url https://staging.your-app.example --out rec
```

A browser window opens at that address. Sign in if you need to, then do the
task once at a normal pace. When you're done, close the browser window or
press Ctrl-C in the terminal. The recording is saved in `rec/`.

Password fields are never saved. To keep another typed value out of the
recording, pass `--secret FIELD`; the value is then read at run time from the
`OPENADAPT_FLOW_SECRET_<FIELD>` environment variable.

## 3. Compile it

```bash
openadapt flow compile rec --out bundle --name my-first-workflow
```

The compiler turns the recording into a program in `bundle/`. When you typed
a value into a labeled field, the compiler may propose making it an input
that changes per run. In a terminal it asks you about each proposal. To
accept proposals without the prompt, pass `--accept-params NAME1,NAME2`;
any proposal you don't accept stays a fixed value from the recording. The
proposals are listed in `bundle/param_proposals.json`.

## 4. Read what it compiled into

```bash
openadapt flow visualize bundle --out graph.html
openadapt flow lint bundle
```

`visualize` writes a page that shows every step, how each one finds its
target on screen, and which steps have a right-record check. Open
`graph.html` in a browser.

`lint` lists what the program doesn't cover yet, such as a click with no
right-record check. It exits 1 only for an `error`. A fresh recording usually
has a few warnings and informational notes.

## 5. Replay it

```bash
openadapt flow replay bundle --url https://staging.your-app.example --run-dir run
```

`replay` drives the real app at `--url` and performs every recorded step. It
doesn't ask first and it isn't a dry run, which is why this tutorial uses a
task that only reads. Point it at a test copy, never at production data.

When it finishes, it prints a summary and writes `run/REPORT.md` and
`run/report.json`. A replay ends `COMPLETED_UNVERIFIED`: the steps finished,
but nothing read a saved record back, because `replay` doesn't check saves.
Exit code 0 from `replay` means the steps finished, not that anything was
confirmed.

If a screen has changed since you recorded, the step tries other ways to find
its target, logs a proposed repair, and stops if nothing matches. Run
`openadapt flow explain run` for a plain-language account of any run.

## What you have now

- A recording in `rec/`.
- A compiled program in `bundle/`, which you can read as a diagram.
- A run report in `run/` that shows each step, how its target was found, and
  how many model calls the run made (zero on a healthy run).

## Before a workflow saves anything

A program that writes to a real system needs more than a replay. It needs a
check that reads the saved record back, a policy check, and a test against
normal and faulty cases in the environment where it will run. In order:

1. [Add record checks](../how-to/record-checks.md).
2. [Certify and qualify the workflow](../how-to/certify-and-qualify.md).
3. [Run it in production](../how-to/run.md).
