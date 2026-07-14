# Desktop quickstart (Windows)

!!! warning "Target-state page — the Windows backend is not yet wired into the CLI"
    Everything the deterministic replay engine needs to drive a native Windows
    desktop **exists** (`WindowsBackend`, the in-session agent, the RDP backend),
    but `replay` and `run` still construct the **web** backend only. The
    `--backend windows` selection and `backend.kind` config shown here are the
    **intended UX**; they are not selectable from the CLI today. Track the wiring
    in the [gap list](#what-is-not-yet-wired). Until then this path runs from the
    library API, not the CLI.

The [five-minute web tour](index.md) records and replays against a browser app.
The same demonstration compiler drives a **native Windows desktop** — WinForms,
WPF, Win32, and legacy EMRs the browser backend cannot reach — over the exact
same bundle format, resolution ladder, effect verification, and run report. The
substrate underneath changes; the workflow, the artifacts, and the safety model
do not.

## What is different from the web path

| | Web (today) | Windows desktop (target state) |
|---|---|---|
| Backend | Playwright / Chromium | `WindowsBackend` over the in-session agent HTTP API |
| Observation | DOM + pixels | **Pixels only** (PNG frames in, pixel-coordinate input out) |
| Structural rung | Available (DOM handles) | **Not available** — native Windows has no cheap DOM equivalent |
| Identity signal | DOM text | UI Automation (UIA) element text under the point, where present |
| Where it runs | Local browser | A Windows host or VM running the in-session agent |

The pixel-only substrate is exactly what the vision-anchored runtime was built
for. What you lose is the structural rung of the [resolution
ladder](../concepts/self-healing.md); template, OCR, and geometry still resolve
targets, and [effect verification](../concepts/effect-verification.md) against a
real system of record remains the authoritative check — the screen is never
trusted as proof a write landed.

## 1. Stand up a Windows host with the in-session agent

The engine drives Windows through an **in-session agent**: a small HTTP server
running inside the Windows session that exposes `GET /screenshot` (raw PNG) and
`POST /execute_windows` (executes input against the desktop). See
[Backends](../reference/backends.md#windows-the-in-session-agent) for the
contract and the session-0 constraint (the agent must run in the interactive
session, not the service session, or it cannot see or drive the desktop).

```bash
# On the Windows host / VM, launched into the interactive session:
#   the agent serves /screenshot and /execute_windows on loopback.
# Protect the execute channel with a bearer token on any non-loopback hop:
set OAFLOW_AGENT_TOKEN=<a-strong-token>
```

!!! danger "The execute channel is remote code execution by contract"
    `/execute_windows` runs code against the desktop. Bind the agent to loopback,
    put it behind TLS on any hop that leaves the machine, and set
    `OAFLOW_AGENT_TOKEN` so every request must authenticate. Never expose it
    unauthenticated on a shared network.

## 2. Record the task on the Windows app

Record the demonstration against the real Windows application. Input is captured
from the OS globally (real clicks, typing, keys), producing the same recording
format `compile` consumes.

```bash
# Intended UX (not yet wired from the CLI — see the gap list):
openadapt flow record --backend windows --out rec
```

## 3. Compile, lint, certify — unchanged

Compilation, coverage linting, and policy certification are **substrate-agnostic**
and work today exactly as on the web path:

```bash
openadapt flow compile rec --out bundle --name intake
openadapt flow lint    bundle
openadapt flow certify bundle --policy clinical-write
```

## 4. Replay against the Windows desktop

```bash
# Intended UX (not yet wired from the CLI — see the gap list):
openadapt flow replay bundle --backend windows \
  --agent-url http://127.0.0.1:5912
```

The run writes the same illustrated `REPORT.md` and `report.json` as the web
path. The report states, per step, which rung of the ladder resolved the target,
whether the identity check was armed and what UIA text it verified, and which
postconditions and effects passed.

## Citrix and other remote desktops

When the Windows application is only reachable as a **remote-display stream**
(Citrix, RDP), the engine drives it **pixel-only** over the
[RDP backend](../reference/backends.md#remote-display-rdp-citrix): there is no
accessibility tree, no DOM, no structured layer. See
[Desktop and Citrix](../guides/desktop-and-citrix.md) for the full guide and its
honest limits (pixel-only means no structural rung and no independent on-host
observation channel).

## What is not yet wired

This quickstart documents the **target state**. Today:

- The CLI `replay` / `run` construct the **web** backend unconditionally; there
  is no `--backend` flag and no `backend.kind` config field. Driving Windows
  goes through the library API (`WindowsBackend`, `FreeRDPBackend`) directly.
- `--agent-url` / `--backend windows` / `--backend rdp` shown above do not exist
  on the CLI yet.
- Automated Windows-host provisioning (the cloud `desktop` runner) is unbuilt;
  you bring your own Windows host or VM.

See [Deploy the desktop backend](../guides/desktop-and-citrix.md) and the
[Backends reference](../reference/backends.md) for the current library-level path.
