---
description: >-
  Fixes for the problems people hit in their first week: blank recordings,
  install errors, runs that stop or are refused, and Cloud sync.
---

# Troubleshoot

## Recordings are blank or black

The operating system blocked screen capture without an error.

=== "macOS"

    Turn on OpenAdapt, or the terminal you record from, in
    **Privacy & Security → Screen Recording**, **Privacy & Security →
    Accessibility**, and **Privacy & Security → Input Monitoring**, then quit
    and reopen it. A new Screen Recording permission applies only after a
    restart.

=== "Windows"

    - **One window blank:** that window runs as administrator. Run
      OpenAdapt as administrator too.
    - **Everything blank:** the process runs in a different session from
      the signed-in desktop. See
      [the Windows agent server](#the-windows-agent-server-is-in-the-wrong-session).

## `pip install openadapt` doesn't install the engine

The engine and the MCP server need Python 3.10, 3.11, or 3.12. On Python 3.13
or later, pip installs only the launcher. Use a 3.12 environment, or:

```bash
uvx --python 3.12 openadapt quickstart
```

## The browser doesn't start on Linux

Run `openadapt doctor --backend web`. It lists the system libraries Chromium
needs that are missing, and the command that installs them.

## A run is refused before it starts

`run` exited 2 and nothing ran. The message names the gate. Common causes:

| Message names | Fix |
|---|---|
| Certification or policy | Run `openadapt flow certify bundle --policy clinical-write` and fix what it reports. |
| A missing admission | Standard and Regulated need `--qualification-authority-file` for that exact bundle version. |
| `unresolved` fields | Fill every field listed under `unresolved` in the deployment file. |
| A surface mismatch | The bundle was recorded on another surface. Pass the right `--backend`. |
| An unencrypted bundle | Regulated needs an encrypted bundle: `openadapt flow seal bundle -o bundle-sealed`. |

Add `--dry-run` to see every gate without running.

## A run stops too often on RDP or Citrix

The right-record check can't read an identifier with confidence from
pixels, usually because of confusable characters such as `O` and `0`. Teach
the specific case with `openadapt flow teach`, or use a surface with
structure if the app offers one. Don't lower the check: a stop is better than
a save to the wrong record. See [Handle a halt](handle-a-halt.md).

## A run ended `RECONCILIATION_REQUIRED`

A save may have gone through. Don't run it again. Have a person look up the
record in the application. If the save didn't happen, run the item again; if
it did, mark the item done. `openadapt flow approve --authorize-uncertain-retry`
allows one retry of the uncertain step after that check.

## The agent gets `did_not_run` with `not_ready_to_run`

The workflow hasn't passed the checks its profile needs. `failed_checks`
names each one, such as `not_certified`. See
[Certify and qualify a workflow](certify-and-qualify.md).

## The Windows agent server is in the wrong session

A Windows service, a task running as SYSTEM, or a command started over SSH
runs in a different session from the signed-in desktop. Screenshots come back
blank and input goes nowhere. Sign in, open a terminal on the desktop, and
start the server there:

```bat
set OAFLOW_AGENT_TOKEN=<a long random secret>
python -m openadapt_flow.backends.win_agent.server --port 5001
curl http://127.0.0.1:5001/health
```

`active_console_session` in the health response must be a number other than
`-1` or `0`.

## The offline queue is stuck

The desktop app shows **OFFLINE** or **SYNCING**, and pushes aren't reaching
Cloud. The upload queue keeps items across restarts and retries when the
connection returns. From the command line, a failed `push` exits 1 in both of
these cases, so read the message or the `--json` status, not the exit code:

- `push failed: ...` (`"status": "failed"`): Cloud didn't accept the
  artifact. Fix the cause and run `push` again.
- `Push delivery is uncertain` (`"status": "delivery_uncertain"`,
  `"next_action": "reconcile"`): Cloud may have received it. Don't push again
  yet. Reconcile the artifact in Cloud first, and push again only if Cloud
  doesn't have it.

If the token was revoked, mint a new one in Cloud settings and run
`openadapt flow login --token <token>`.

## `openadapt connect` says `No such command 'connect'`

The launcher is older than 1.7, often from an old Conda environment. Upgrade
in a clean virtual environment with `python -m pip install --upgrade
openadapt`, then generate a new pairing code; codes expire after five
minutes.

## Still stuck

Run `openadapt flow explain` on the run directory, then ask on
[Discord](https://discord.gg/yF527cQbDG) or open an issue on
[GitHub](https://github.com/OpenAdaptAI/OpenAdapt/issues). Leave patient data
and screenshots out of public posts.
