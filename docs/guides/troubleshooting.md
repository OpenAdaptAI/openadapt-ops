# Troubleshooting

The first-week failure modes, keyed by symptom → cause → fix. The docs explain
*why* the runtime halts ([the identity gate](../concepts/identity-gate.md)); this
page is the operational "it halted, now what."

## Capture is blank or black

**Symptom.** Recordings come out empty — a blank or black frame — with no error
dialog. The app looks like it is recording but captures nothing.

**Cause.** Missing OS permissions. This is the single most common first-run
problem.

**Fix.**

=== "macOS"

    Grant **both** Screen Recording and Accessibility, then **restart the app**:

    - **System Settings → Privacy & Security → Screen Recording** → OpenAdapt on.
    - **System Settings → Privacy & Security → Accessibility** → OpenAdapt on.
    - Quit and reopen OpenAdapt — macOS only applies a newly granted Screen
      Recording permission after a restart.

    Full steps: [Desktop app — install and first run](../desktop/install.md#3-grant-os-permissions-the-step-everyone-misses).

=== "Windows"

    Ordinary windows capture without a permission prompt. If **one specific
    window** is blank, it is running **as administrator** (UAC elevation) and a
    normally-privileged app cannot see it. Run **OpenAdapt as administrator too**
    (right-click → *Run as administrator*) so both are at the same integrity
    level.

## It halts too much (over-halting on Citrix / pixel-only)

**Symptom.** On a Citrix / RDP (pixel-only) session, the run **halts on a
glyph-confusable identifier** — an MRN where `O`/`0` or `l`/`1`/`I` are
ambiguous — far more often than on the browser.

**Cause.** This is the identity gate doing its job, not a bug: it **halts rather
than guessing** a wrong-patient click. On a pure-pixel substrate there is no
structured accessibility text, so the identity ladder falls back to OCR, which
cannot always disambiguate confusable glyphs — so it safely halts. See
[the identity gate](../concepts/identity-gate.md) and
[backends](../concepts/backends.md#remote-rdp-pixel-only).

**Fix.** Teach the halt instead of loosening the gate:

- **`teach` the correction.** Demonstrate the fix once and `teach` compiles it
  back into the workflow as a governed, guarded branch so that state stops
  halting — without weakening the wrong-patient guarantee. See
  [the halt-learn loop](../concepts/halt-learn-loop.md) and
  [`teach`](../reference/cli.md#teach).
- **`report-break`** to surface the halt centrally (PHI-free) for triage:
  [`report-break`](../reference/cli.md#report-break).
- Where the render is stable, capturing the identifier crop at compile time and
  using a higher-fidelity backend (structured a11y/DOM text instead of pixels)
  removes the ambiguity at the source. Prefer `--backend windows` (UI Automation)
  over pixel-only where the app exposes it.

!!! note "Do not just lower the threshold"
    Over-halting is preferable to a silent wrong write. The remedy is to *teach*
    the specific case or raise the substrate's fidelity — not to disable the
    gate.

## The offline queue is stuck / recordings aren't syncing

**Symptom.** The tray shows **OFFLINE** or **SYNCING** and pushes are not
reaching the cloud workspace.

**Cause.** No connectivity to `app.openadapt.ai`, an expired or revoked ingest
token, or the durable upload queue is holding items to retry.

!!! note
    The tray/desktop sync surface is part of the
    [desktop app](../desktop/install.md); from the CLI, a
    failed `push` simply exits nonzero and is safe to re-run.

**Fix.**

- The upload queue is **durable**: it persists across restarts, retries with
  backoff, and flushes when connectivity returns — a network blip does not lose a
  recording. Wait for connectivity to return, or check it directly.
- Verify the token: `openadapt flow login --token oai_ingest_…` re-validates it.
  If it was revoked, mint a new one at
  `app.openadapt.ai/dashboard/settings/ingest` (see
  [Connect to a cloud workspace](../desktop/connect-to-cloud.md)).
- Confirm you are on the right lane: **regulated/PHI recordings are not pushed to
  the cloud** — they stay local on the [on-prem lane](deploy-on-prem.md). If a
  PHI-bearing push is being refused, that is the fail-closed PHI boundary working
  as intended.

## The Windows agent landed in session 0 {#session-0}

**Symptom.** On Windows the backend gets a **blank screenshot** and synthetic
input **goes nowhere**, even though permissions look fine.

**Cause.** A Windows service runs as `SYSTEM` in **session 0**, isolated from the
logged-on user's interactive desktop (session 1). A screenshot there captures a
blank screen and input goes into the void. See
[backends → the session-0 problem](../concepts/backends.md#the-in-session-agent-the-session-0-problem).

**Fix.** The in-session agent server **must run in the interactive console
session (session 1)**, not as a session-0 service. Launch it in the logged-on
user's session (it binds to loopback by default and supports an optional bearer
token, `OAFLOW_AGENT_TOKEN`, so its execute channel is not left unauthenticated
in a PHI deployment). For Citrix/RDP, ensure the agent runs inside the same
interactive session that renders the application.

## `openadapt connect` fails with `No such command 'connect'` {#connect-no-such-command}

**Symptom.** Pairing a computer to a cloud workspace with
`openadapt connect --pairing …` errors with `Error: No such command 'connect'`.

**Cause.** You are on an old launcher build — most often an Anaconda-installed
`openadapt` 1.5.x. The `connect` command ships in the `openadapt` launcher from
**1.7 onward**.

**Fix.** Upgrade and retry:

```bash
pip install --upgrade openadapt   # resolves openadapt >= 1.7.1
openadapt --version               # confirm 1.7.1 or newer
```

Then generate a **fresh** pairing code in the dashboard (the previous one expires
after five minutes) and re-run `openadapt connect --pairing …`. If `pip` keeps
resolving the old version, you are likely in a stale Conda environment — install
into a clean virtualenv instead. See
[Connect the desktop app to a cloud workspace](../desktop/connect-to-cloud.md#3-connect-the-desktop-app).

## Still stuck?

- Re-read the run's `REPORT.md` and `report.json` — the halt reason, the resolver
  rung, and the drift signature are recorded there. See
  [Read and audit run reports](run-reports.md).
- Check what a bundle is missing before you deploy it with
  [`lint`](../reference/cli.md#lint) and [`certify`](../reference/cli.md#certify).
- Ask on the [Discord](https://discord.gg/yF527cQbDG) or open an issue on
  [GitHub](https://github.com/OpenAdaptAI).
