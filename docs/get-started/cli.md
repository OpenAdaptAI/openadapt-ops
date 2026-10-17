---
description: >-
  Install the openadapt command, run the bundled tutorial to see a VERIFIED
  run, then make it stop on purpose with --break-it.
---

# Get started on the command line

This track installs the `openadapt` command and runs the bundled tutorial. The
tutorial uses MockMed, a synthetic clinic app with made-up patients, so it
needs no account, no app of your own, and no operating-system permissions.

The engine supports Python 3.10, 3.11, and 3.12. With
[uv](https://docs.astral.sh/uv/getting-started/installation/), you don't need
a matching Python: uv downloads Python 3.12 for the run.

## Try it without installing

```bash
uvx --python 3.12 openadapt flow tutorial
```

The tutorial starts MockMed on this computer, records the bundled
demonstration in a headless browser, compiles it, certifies the bundle, and
runs it under the Standard profile. It then reads the saved record back
through MockMed's read-only system-of-record API, which is independent of the
screen. If the browser that OpenAdapt drives isn't installed yet, the first
run downloads it.

A healthy run ends `VERIFIED` and writes a local receipt. The run enables no
model call and no Cloud call. Add `--headed` to watch the browser.

## Install the command

To keep `openadapt` on your PATH, use the installer script. It installs uv if
needed, then installs `openadapt` with Python 3.12 as an isolated tool.

=== "macOS and Linux"

    ```bash
    curl -fsSL https://openadapt.ai/install.sh | sh
    ```

=== "Windows (PowerShell)"

    ```powershell
    powershell -c "irm https://openadapt.ai/install.ps1 | iex"
    ```

=== "pip"

    On Python 3.10, 3.11, or 3.12:

    ```bash
    python -m pip install --upgrade openadapt
    ```

Then run the tutorial with the installed command:

```bash
openadapt flow tutorial
```

## What the tutorial writes

The tutorial writes everything under its output directory. The default is
`tutorials/tutorial-<UTC timestamp>` in the current directory, and `--out`
sets another one.

| Path | What it is |
|---|---|
| `<out>/recording/` | The recorded demonstration: frames, events, and metadata. |
| `<out>/bundle/` | The compiled, certified workflow bundle. |
| `<out>/run/REPORT.md` | The illustrated run report, for people. |
| `<out>/run/report.json` | The same report, for programs. |
| `<out>/run/receipt.json` | The local receipt. It's written only for a `VERIFIED` run, next to `receipt.md` and `receipt.png`. |

Read the report, draw the compiled program, and list its coverage gaps:

```bash
less <out>/run/REPORT.md
openadapt flow visualize <out>/bundle --out graph.html
openadapt flow lint <out>/bundle
```

The tutorial exits `0` when the run is `VERIFIED`, `1` on any other outcome,
and `2` when it refuses to start. [Run outcomes](../reference/run-outcomes.md)
lists every outcome.

## Make it stop on purpose

```bash
openadapt quickstart --break-it
```

This runs the same tutorial, then reruns the same certified bundle against a
MockMed server that shows a saved banner but rejects the write. Every check on
the screen passes. The independent read of the system of record finds no
record, so the run ends `HALTED` instead of reporting success.

The rerun's transaction outcome is `RECONCILIATION_REQUIRED`, shown as "Check
the record". The engine saw a write attempted and refuted, and it doesn't claim
that nothing was written unless it can prove it. In this synthetic store, the
record count stays at zero. The halted run gets no receipt.
`openadapt flow tutorial --break-it` does the same in the tutorial's own output
directory.

`openadapt quickstart` writes to `openadapt-quickstart` in the current
directory, or `openadapt-quickstart-2` and so on when that exists. The halted
rerun's report is in `run-broken/REPORT.md` under that directory. It never
overwrites an existing directory.

## Next

- [Author a workflow](first-workflow.md) on your own web app. Start with a
  lookup that doesn't change business data.
- [Record your own app](../guides/record-your-app.md) covers recording,
  compiling, and replaying in more depth.
- [The openadapt flow CLI](../reference/cli.md) lists every command and flag.
