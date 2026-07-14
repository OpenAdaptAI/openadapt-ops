# Backends

A **backend** is the thin adapter between the substrate-agnostic replay engine
and a concrete way of driving an application. Every backend implements the same
`Backend` protocol — *PNG frames in, input events out* — so the same compiled
[bundle](bundle-format.md), [resolution ladder](../concepts/self-healing.md),
[effect verification](../concepts/effect-verification.md), and
[run report](../guides/run-reports.md) work everywhere. The substrate changes;
the workflow does not.

For the conceptual model of where the engine runs, see
[Backends, where it runs](../concepts/backends.md).

!!! warning "CLI wiring status"
    Today `replay` / `run` construct the **web (Playwright) backend
    unconditionally**. There is no CLI backend selector, and the Windows and RDP
    backends — though they exist and implement the protocol — are reachable only
    through the library API. The `--backend` selection documented here is the
    **target-state UX**; see the [gap list](#what-is-not-yet-wired).

## The backend protocol

Every backend implements a small, honest contract:

| Method | Purpose |
|---|---|
| `screenshot()` | Return the current surface as a PNG |
| `viewport()` | Report the surface size in pixels |
| `click()` / `double_click()` | Send a pointer event at pixel coordinates |
| `type_text()` | Send characters |
| `press()` | Send a key or chord (decomposed into ordered key down/up) |
| `scroll()` | Send a wheel gesture |

Two capabilities are **optional**, and a backend advertises only what it can
honestly provide:

- **`StructuralBackend`** — cheap structured observations (URL, title, element
  handles). The web backend has it (DOM); native Windows and RDP do **not**, so
  the [structural rung of the ladder](../concepts/self-healing.md) is simply
  absent there. Steps that would depend on it stay honestly unverified rather
  than faked.
- **`IdentityBackend.structured_text_at()`** — a higher-fidelity identity signal
  than OCR for the element under a point. The web backend reads DOM text; native
  Windows reads UI Automation text; RDP has neither and falls back to OCR.

## Web — Playwright (default, shipped)

The reference backend drives a Chromium page via Playwright.

- **Observation**: DOM **and** pixels. Full structural rung available.
- **Identity**: DOM text under the point.
- **Viewport**: fixed 1280×800, `deviceScaleFactor=1`, so CSS pixels equal
  screenshot pixels.
- **Provisioning**: the browser installs automatically on first use (disable with
  [`OPENADAPT_FLOW_NO_AUTO_INSTALL`](configuration.md)).

This is the only backend the CLI wires today. It is selected implicitly by
`replay` / `run` and configured by [`backend.url` / `backend.headed`](deployment-config.md#backend).

## Windows — the in-session agent

`WindowsBackend` drives a **native Windows desktop** over an HTTP contract served
by a small agent **inside the Windows session**:

```
GET  /screenshot        -> raw PNG bytes (not base64 JSON)
POST /execute_windows   -> executes input against the desktop.
                           Body: {"command": "<bare Python statements>"}
                           (bare Python — NOT wrapped in python -c "...")
```

- **Observation**: **pixels only** for resolution — it deliberately does *not*
  implement the structural observations (URL / title / page count) because native
  Windows has no cheap equivalent. Those steps stay honestly unverified.
- **Identity**: implements `structured_text_at()` via a **UI Automation**
  `ElementFromPoint` read — the element under the point exposes its `Name` /
  `Value` / text even with no stable `AutomationId`. Returns the real characters
  when the agent echoes them back, or `None` when it cannot (older agent), in
  which case identity falls back to OCR or the step halts per policy.
- **Auth**: the `/execute_windows` channel is **remote code execution by
  contract**. The agent binds to loopback by default; set
  [`OAFLOW_AGENT_TOKEN`](configuration.md#the-desktop-in-session-agent) to require
  a bearer token, and put it behind TLS on any non-loopback hop.

### The session-0 constraint

A Windows **service** runs in session 0, which is isolated from the interactive
desktop — it cannot screenshot or drive the user's applications. The in-session
agent therefore **must run in the interactive console session (session 1)**. The
test harness handles this by launching the agent shim into session 1 via
`CreateProcessAsUser`; a production deployment must do the equivalent (a scheduled
task set to run in the active session, or an equivalent launcher). Screen capture
uses a host-side or session-aware path, not an in-guest `BitBlt` from session 0.

## Remote display — RDP / Citrix

`FreeRDPBackend` drives a **pixel-only remote desktop** over RDP (the substrate
for Citrix-delivered and other streamed legacy apps). It is split into two layers
so the RDP library stays replaceable and the adapter is testable without a live
server:

- **`RDPTransport`** — a minimal transport protocol any RDP client can satisfy:
  `connect` / `disconnect` / `framebuffer` / `pointer` / `key` / `wheel`.
- **`FreeRDPBackend`** — implements the `Backend` protocol on top of a transport:
  `screenshot` PNG-encodes the framebuffer, `click` sends pointer down/up,
  `type_text` sends per-character key events, `press` decomposes a chord, `scroll`
  sends a wheel gesture.
- **`AardwolfTransport`** — a real transport over the pure-Python `aardwolf` RDP
  client, gated behind an optional extra.

Honest limits over RDP/Citrix:

- **No structured layer at all** — no DOM, no accessibility tree, no UIA. Every
  target is resolved from the picture; the structural rung does not exist.
- **Identity is OCR-grade** — there is no UIA over the pixel stream, so the
  [identity gate](../concepts/identity-gate.md) uses OCR and is armed only on the
  subset of steps with a stable discriminating band. The run report discloses the
  armed subset.
- **On-screen read-back is not independent verification.** For a consequential
  write, the authoritative check is
  [effect verification](../concepts/effect-verification.md) against the system of
  record, not the streamed pixels. See
  [Desktop and Citrix](../guides/desktop-and-citrix.md).

## Choosing a backend (target-state UX)

The intended selection surface is a `backend.kind` in the
[deployment config](deployment-config.md#backend) and a matching `--backend` CLI
flag:

```yaml
# Intended (not yet wired) — see the gap list
backend:
  kind: windows            # web | windows | rdp   (default: web)
  agent_url: http://127.0.0.1:5912   # windows: the in-session agent
  # rdp_host: citrix-vda.internal    # rdp: the remote-display host
```

```bash
openadapt flow run bundle --backend windows --agent-url http://127.0.0.1:5912
```

## What is not yet wired

- **No CLI / config backend selector.** `replay` / `run` build the web backend
  unconditionally; `backend.kind`, `--backend`, `--agent-url`, and `--rdp-host`
  do **not** exist yet. `WindowsBackend` and `FreeRDPBackend` are library-only.
- **No CLI desktop recorder.** `record --backend windows` (global-hook desktop
  recording from the CLI) is not exposed.
- **No managed Windows provisioning.** The cloud `desktop` runner
  (Windows-in-QEMU + streaming) that would host these backends is unbuilt; supply
  your own Windows host or VM.
