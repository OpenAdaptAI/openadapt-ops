# Backends: where it runs

A compiled workflow does not care what is underneath it. The runtime sits behind
a small four-method `Backend` protocol (screenshot in; click, type, key, scroll
out), so the same bundle, the same resolution ladder, and the same identity gate
run against a browser, a native Windows desktop, or a pixel-only remote session.
Backends are **adapters, not rewrites**.

## Vision-first, not vision-only

The runtime can always operate a pure pixel surface: PNG bytes in, clicks and
keys at pixel coordinates out. That is the floor, and it is why the whole loop
runs in CI with no OS permissions. But it is not a ceiling. Where a backend owns
a structured layer (a browser DOM, a native accessibility tree), the
[capability ladder](capability-ladder.md)'s top rung re-finds the recorded
target as an *element* and acts on it deterministically. The visual rungs are
the fallback for substrates that expose only pixels. The ladder is
**backend-agnostic**: it uses the highest-fidelity signal each surface offers.

## The backends

### Web — Playwright (reference)

A headless Chromium driven by Playwright is the reference backend and the one
every example in these docs uses. It is the most capable substrate:

- **Structural rung**: reads the DOM element under a point, so resolution and
  [identity](identity-gate.md) can use stable selectors and structured text
  where they exist.
- **Structural postconditions**: URL change, title change, new-tab opened.
- **CI-friendly**: no OS permissions, no display server; the whole record →
  compile → replay loop runs in a container.

This is where the product is most mature and most heavily tested.

### Desktop — Windows (UIA)

The `WindowsBackend` drives a native Windows desktop through the Windows Agent
Arena (WAA) HTTP contract: it screenshots the desktop and sends pixel-coordinate
input, and it reads the **UI Automation** tree for identity. Crucially, an
element usually exposes `Name` / `Value` text **even when it has no stable
`AutomationId`**, so UIA-based identity is viable on most native apps even where
a durable selector is not.

Desktop (and Citrix/VDI) is the **differentiated wedge**: the work that has no
web UI and no usable API, where a computer-use agent is the only alternative and
a wrong write is expensive. Structured desktop text distinguishes an `O` from a
`0` that OCR collapses, which is exactly what makes wrong-record writes
preventable there.

!!! warning "Honest status: the live desktop proof is recent and limited"
    The desktop path is real and runs end to end, but the published proof is an
    **existence result**, not a big-N study. It was measured on a WinForms app
    (a stand-in for a clinical EMR that is not no-touch installable) inside a
    Windows 11 **ARM** VM under x64 emulation on Apple Silicon, at small N per
    condition. Two honest findings from that run:

    - The **mechanism transfers**: record → compile → replay of a real WinForms
      workflow ran deterministically over the vision-only `WindowsBackend`,
      judged by database ground truth, with identity bands extracted and
      verified on desktop-rendered text — and it **never mis-wrote**.
    - **Vision-only replay is defeated by render-scale and theme drift** on
      desktop (it safe-halted, it did not mis-act), which is precisely the
      argument for the structural (UIA) rung over pixels. On a controlled DOM
      re-render the structural rung resolved **21/21** targets where visual
      replay alone managed **6/21**.

    A native-x86 confirmation run and larger N are future work. Absolute
    per-app numbers (including identity-armed coverage) are per-app
    measurements, not universal constants.

#### The in-session agent (the session-0 problem)

Driving a real desktop has a subtlety a browser does not: a Windows service runs
as `SYSTEM` in **session 0**, isolated from the logged-on user's desktop, where
a screenshot captures a blank screen and synthetic input goes nowhere. So the
desktop path ships a small **in-session agent server** that must run in the
interactive console session (session 1). It exposes exactly the endpoints the
backend calls (`/screenshot`, `/execute_windows`, `/health`). It is hardened
relative to a bare shim: it binds to loopback by default (its execute channel is
remote code execution by contract) and supports an **optional bearer token**
(`OAFLOW_AGENT_TOKEN`) so the channel is not left unauthenticated in a PHI
deployment.

### Remote — RDP (pixel-only)

The `FreeRDPBackend` drives a legacy application over **RDP**, read pixel-only:
no accessibility tree, no DOM, no structured layer of any kind. That is exactly
the substrate the vision-first runtime was built for. It is split into a
swappable `RDPTransport` protocol (so the adapter is CI-testable without a live
server) and a real transport over the pure-Python async `aardwolf` client,
behind the optional `rdp` extra. On a pure-pixel substrate the ladder runs on
its visual floor and the identity gate falls back to its pixel/OCR tiers — which
is why a look-alike identifier can force a [halt rather than a verify](identity-gate.md)
there.

## Status at a glance

| Backend | Substrate | Structural rung | Identity signal | Maturity |
|---|---|---|---|---|
| Playwright (web) | Browser DOM | Yes (DOM) | Structured text (DOM) | Reference, heavily tested |
| `WindowsBackend` | Native Windows | Via UIA | UI Automation `Name`/`Value` | Live proof recent and limited |
| `FreeRDPBackend` | Pixel-only RDP | No | Pixel / OCR floor | Adapter, CI-tested against a mock transport |

The desktop and RDP backends are exercised in CI against mocked servers, so the
adapter contract is verified without a live OS. What varies per substrate is how
high up the [capability ladder](capability-ladder.md) a given app lets the
runtime climb — and everything below the top rung remains the same fail-safe
machinery.
