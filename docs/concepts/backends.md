# Backends: where it runs

A compiled workflow does not care what is underneath it. The runtime sits behind
a small four-method `Backend` protocol (screenshot in; click, type, key, scroll
out), so the same bundle, the same resolution ladder, and the same identity gate
run against a browser, a native Windows desktop, or a pixel-only remote session.
Backends are **adapters, not rewrites**.

!!! tip "Selecting a backend on the CLI"
    `record`, `replay`, `run`, and `resume` take
    [`--backend {web,windows,rdp}`](../reference/cli.md#backend) (with
    `--agent-url` for Windows and `--rdp-host` for RDP). The default is `web`.
    See [Choosing a backend](../reference/cli.md#backend).

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

The public `WindowsBackend` now narrows the in-session boundary to typed
`/input` and `/uia/*` operations, disables arbitrary legacy execution by
default, screenshots the desktop, and reads the **UI Automation** tree for
identity. Crucially, an
element usually exposes `Name` / `Value` text **even when it has no stable
`AutomationId`**, so UIA-based identity is viable on most native apps even where
a durable selector is not.

Desktop (and Citrix/VDI) is the **differentiated wedge**: the work that has no
web UI and no usable API, where a computer-use agent is the only alternative and
a wrong write is expensive. Structured desktop text distinguishes an `O` from a
`0` that OCR collapses, which is exactly what makes wrong-record writes
preventable there.

!!! warning "Honest status: scoped Windows acceptance, not broad support"
    The accepted `20260717-candidate-56759c8-v2` matrix covers one exact in-tree
    WinForms Patient Notes workflow on a Windows 11 ARM VM snapshot. It completed 3/3 trials; an
    independent SQLite oracle confirmed all 3/3 effects; stale-target and
    ambiguous-target controls each refused 3/3; and the counted matrix recorded
    0 silent incorrect successes, 0 over-halts, and 0 model calls. The native
    receipts prove delivery to a re-resolved unique fingerprint; the SQLite
    oracle, not the receipt, proves the business effect.

    The report preserves earlier rejected diagnostic matrices; they are not
    counted acceptance trials. The counted result is enough to accept the named matrix, not arbitrary Windows
    applications, native-x86 clean-machine support, hosted desktop, or a
    production SLA. Review [Flow PR #132](https://github.com/OpenAdaptAI/openadapt-flow/pull/132)
    and the [immutable evidence report](https://github.com/OpenAdaptAI/openadapt-flow/blob/defafbae758a75c8e149d9693f2cffe1f2264b8c/benchmark/windows_uia/results.json).

#### The in-session agent (the session-0 problem)

Driving a real desktop has a subtlety a browser does not: a Windows service runs
as `SYSTEM` in **session 0**, isolated from the logged-on user's desktop, where
a screenshot captures a blank screen and synthetic input goes nowhere. So the
desktop path ships a small **in-session agent server** that must run in the
interactive console session (session 1). The shipped typed agent uses
authenticated TLS, bounded screenshot/input/UIA operations, unique-candidate
selection, and stale-target rejection. The older `/execute_windows`
compatibility route remains a migration surface and is disabled by default; it
is not the production RPC contract.

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

!!! warning "Honest status: scoped RDP acceptance, not broad support"
    On one Parallels Windows 11 VM at 1280x800 with Aardwolf 0.2.14, candidate
    `82a658a` completed 3/3 trials that created a unique file through the Windows
    Run dialog over network RDP. Independent guest-tools readback confirmed the
    exact contents. Trial latencies were 51.845s, 10.467s, and 7.477s; the batch
    recorded 0 failures, 0 silent incorrect successes, 0 over-halts, and 0 model
    calls.
    Cleanup removed only the batch-owned snapshot, restored the exact
    eight-snapshot inventory, left the VM suspended, and returned the current
    pointer without resume to the unchanged original base. This accepts only
    that task, snapshot, transport, and oracle. It is not
    arbitrary-app, record-identity, clean-machine, production, hosted-RDP, or
    Citrix evidence. Review
    [Flow PR #142](https://github.com/OpenAdaptAI/openadapt-flow/pull/142)
    and the [immutable sanitized report](https://github.com/OpenAdaptAI/openadapt-flow/blob/6610d24cebba27918b8ea507b2f05a094057ac85/benchmark/rdp/results_82a658a_20260718.sanitized.json).

### Remote-display / Citrix analog (pixel-only)

The macOS remote-display adapter can capture a named application window and
inject input at screen coordinates. It has been exercised against a Windows VM
window as a **Citrix analog** so the pixel-only mechanism and permission failure
behavior can be tested.

It is not a Citrix integration. The analog does not validate ICA/HDX
compression and latency, client DPI mapping, credentials and lock screens,
synthetic-input acceptance, independent effect verification, or wrong-record
behavior on real charts. Those require a real Citrix deployment.

### Native macOS

A native exact-window candidate in [Flow PR #135](https://github.com/OpenAdaptAI/openadapt-flow/pull/135)
captures only a uniquely selected application window, refuses ambiguous or
non-frontmost targets, and fails before input when Screen Recording or
Accessibility access is missing. On one macOS 15.7.3 arm64 host, counted
candidate `b1b61a5` completed 3/3 exact-byte TextEdit trials and refused a
two-window ambiguity without changing either file, with 0 silent incorrect
successes and 0 over-halts.

The [immutable original report](https://github.com/OpenAdaptAI/openadapt-flow/blob/ca1b522cad215875f7471782283f8f8bb8e6c998/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.json)
still says `status: failed`: its graceful-close cleanup warnings were classified
as a batch failure. A separate [SHA-256-bound adjudication](https://github.com/OpenAdaptAI/openadapt-flow/blob/ca1b522cad215875f7471782283f8f8bb8e6c998/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json)
verified all exact harness PIDs and the temporary root were absent, preserved
the original result, and accepted only the action-effect and ambiguity-refusal
evidence. This is one-host TextEdit evidence, not clean-machine, design-partner,
production, broad-app, AX structural-resolution, or general macOS acceptance.

## Status at a glance

| Backend | Substrate | Structural rung | Identity signal | Maturity |
|---|---|---|---|---|
| Playwright (web) | Browser DOM | Yes (DOM) | Structured text (DOM) | **Beta / reference**: end-to-end CI and real third-party proof |
| `WindowsBackend` | Native Windows | Via UIA | UI Automation `Name`/`Value` | **Partner qualification; scoped acceptance passed**: exact in-tree WinForms 3/3 matrix; arbitrary apps remain unqualified |
| Native macOS | Native macOS | Exact window candidate; AX candidate metadata | Window identity and pixel/OCR floor | **Partner qualification; scoped TextEdit evidence accepted**: one-host 3/3 exact-byte and ambiguity-refusal evidence; broad apps remain unqualified |
| `FreeRDPBackend` | Pixel-only network RDP | No | Pixel / OCR floor | **Partner qualification; scoped RDP evidence accepted**: one-snapshot 3/3 Windows Run-dialog task with exact guest-file readback; arbitrary apps remain unqualified |
| Citrix | ICA/HDX remote application | Deployment-dependent | Pixel / OCR floor unless the client exposes more | **Design partner needed; no ICA/HDX evidence**: RDP evidence does not transfer |

The desktop, RDP, and remote-display adapters have CI coverage that does not
substitute for workload validation on a live OS or remote environment. What
varies per substrate is how high up the
[capability ladder](capability-ladder.md) a given app lets the runtime climb.
Use [What works today](../get-started/what-works-today.md) as the public maturity
contract.
