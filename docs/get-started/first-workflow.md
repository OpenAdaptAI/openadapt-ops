# Your first workflow

This walks through compiling a workflow on **your own** web app: record what you
do, compile it, replay it, and read the report. It takes about five minutes and
makes zero model calls. Web is the quickest
[substrate](../reference/glossary.md#substrate) to start on; the same
record, compile, replay loop drives native Windows, macOS, or Linux applications
and RDP or Citrix sessions by choosing a
[backend](../reference/cli.md#backend).

Here is the loop you are about to run — record once, replay deterministically,
and watch the run heal or halt under drift:

![Record, compile, and replay a workflow with OpenAdapt](../assets/showcase/demo.gif)

## Prerequisites and install

- **macOS, Linux, or Windows.** This walkthrough selects the Playwright-driven
  browser capability, so it has no OS-specific steps. Its matching Chromium
  provisions automatically on the first web action; native, RDP, and Citrix
  paths do not install it.

**Recommended: install with uv.** The first command installs
[uv](https://docs.astral.sh/uv/) if it is missing; the second provisions a
suitable Python, installs OpenAdapt with browser support as a persistent
`openadapt` command, and runs a short environment check:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://raw.githubusercontent.com/OpenAdaptAI/openadapt-flow/main/scripts/install.sh | sh
```

**Manual path: pip in a virtual environment.** If you prefer to manage the
environment yourself — or your team standardizes on pip — use the tabs below.
The engine declares `requires-python >=3.10,<3.13`; check yours with
`python --version` (on some systems `python3 --version`). The quoting around
`openadapt[browser]` differs per shell, and getting it wrong is the most common
first failure:

=== "macOS / Linux (bash, zsh)"

    ```bash
    python3 -m venv .venv && source .venv/bin/activate
    pip install 'openadapt[browser]'
    ```

    The quotes matter: unquoted square brackets are glob characters in zsh
    (`no matches found`) and can misbehave in bash. Single or double quotes
    both work here. A virtual environment keeps the install isolated and
    avoids the stale-package problems a shared or Conda base environment
    causes.

=== "Windows PowerShell"

    ```powershell
    py -m venv .venv; .\.venv\Scripts\Activate.ps1
    pip install "openadapt[browser]"
    ```

    PowerShell accepts single or double quotes; double quotes are shown for
    consistency with cmd.exe.

=== "Windows cmd.exe"

    ```bat
    py -m venv .venv && .venv\Scripts\activate.bat
    pip install "openadapt[browser]"
    ```

    Use **double** quotes. cmd.exe passes single quotes through literally, so
    `pip install 'openadapt[browser]'` fails with an *Invalid requirement*
    error that starts with `'openadapt`.

=== "Linux native desktop (AT-SPI)"

    The browser walkthrough on this page needs no extra system packages. To
    later record or replay **native Linux applications** (`--backend linux`),
    install the AT-SPI runtime and build prerequisites first (Debian/Ubuntu):

    ```bash
    sudo apt-get install \
      gcc pkg-config python3-dev libcairo2-dev libgirepository-2.0-dev \
      gir1.2-atspi-2.0 libatspi2.0-0
    pip install 'openadapt[linux]'
    ```

    The built-in driver uses X11; Wayland requires an operator-approved XDG
    portal session.

!!! tip "No app to record against yet?"
    You do not need your own target to try the loop. The engine bundles
    **MockMed**, a synthetic demo clinic app (fake data only):
    `openadapt flow demo-record --out rec` serves it locally and records the
    canonical triage demo, and `openadapt flow replay bundle` with no `--url`
    serves it again as the replay target. It is a local development fixture,
    not a production workflow or product outcome — but it is a real, running
    web app, so every step below works against it unchanged.

## 1. Record

`record --backend web --url` opens a headed browser pointed at your app and
watches what you do: real clicks, typing, key presses, and scrolls. It writes
the same recording format that `compile` consumes.

```bash
openadapt flow record --backend web --url https://your.app --out rec
```

(Omitting `--backend` defaults to `web` with a printed notice; production
profiles require it explicitly.)

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
an OCR label, geometry landmarks — the
[capability ladder](../reference/glossary.md#capability-ladder)) and
postconditions derived from what the demo actually changed on screen.
Write-shaped clicks (save, submit, create, delete) are auto-classified as
irreversible so they refuse to act on a low-confidence match.

## 3. Lint

```bash
openadapt flow lint bundle
```

`lint` reports coverage gaps before you trust the bundle: clicks that act with
no [identity check](../reference/glossary.md#identity-gate), steps that assert
nothing, writes that may be under-classified. Each finding carries a severity.
It is advice, not a gate. See
[Write and enforce a policy](../guides/policy-and-certification.md) for the
`certify` gate that refuses an unsafe bundle outright.

!!! success "A nonzero exit here is expected, not broken"
    `lint` exits `1` when any finding reaches `error` severity — an unarmed or
    vacuous **irreversible** step. That is the safety boundary working: it is
    telling you a write-shaped click would act without a wrong-record guard.
    Review the findings, then continue to step 4; replay still runs, and the
    [`certify` gate](../guides/policy-and-certification.md) is where a failing
    bundle is actually refused. All exit codes are listed in
    [Run outcomes and halt reasons](../reference/run-outcomes.md#cli-exit-codes).

## 4. Replay

```bash
openadapt flow replay bundle --url https://your.app
```

Recorded parameter values are the defaults; override any of them with
`--param key=value`. The run is deterministic and local. On the healthy path it
makes zero model calls and finishes in seconds. `replay` exits `0` on success
and `1` on a [halt](../reference/glossary.md#halt) — a halt is the fail-closed
refusal to guess, not a crash.

## 5. Read the report

Each replay writes a timestamped run directory under `runs/` containing an
illustrated `REPORT.md` and a machine-readable `report.json`. The report tells
you, per step, which rung of the resolution ladder resolved the target, whether
the identity check was armed and what it verified, which postconditions passed,
and any heals that were applied. See [What you get](what-you-get.md) and
[Read and audit run reports](../guides/run-reports.md). Every outcome and halt
reason the report can show is defined in
[Run outcomes and halt reasons](../reference/run-outcomes.md).

## What is next

- Parameterize a value and inject a secret: [Parameters and secrets](../guides/parameters-and-secrets.md)
- Understand why a step healed or halted: [Governed self-healing](../concepts/self-healing.md)
- Gate a bundle behind a safety policy: [Policy and certify](../concepts/policy-and-certify.md)
