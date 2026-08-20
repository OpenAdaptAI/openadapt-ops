# Backends: where it runs

A compiled workflow does not care what is underneath it. The runtime sits behind
a small four-method `Backend` protocol (screenshot in; click, type, key, scroll
out), so the same bundle, resolution ladder, identity gate, effect checks, and
reporting run against browser, Windows, macOS, Linux, RDP, and Citrix/VDI.
Backends are **adapters, not rewrites**.

!!! tip "Selecting a backend on the CLI"
    `record`, `replay`, `run`, and `resume` take
    [`--backend {web,windows,macos,linux,rdp,citrix}`](../reference/cli.md#backend).
    Each native backend has an exact target selector; governed Citrix `run`
    also requires a readiness marker. The default is `web`.
    See [Choosing a backend](../reference/cli.md#backend).

## Vision-first, not vision-only

The runtime can always operate a pure pixel surface: PNG bytes in, clicks and
keys at pixel coordinates out. That floor is why the whole loop runs in CI with
no OS permissions. It is not a ceiling. Where a backend owns a structured layer
(a browser DOM, a native accessibility tree), the
[capability ladder](capability-ladder.md)'s top rung re-finds the recorded
target as an *element* and acts on it deterministically. Visual rungs are the
fallback for pixel-only substrates. The ladder is **backend-agnostic**: it uses
the highest-fidelity signal each surface offers.

## The backends

### Web: Playwright

Playwright drives the web substrate. Flow can launch Chromium or attach to one
existing signed-in local Chromium tab through a loopback CDP endpoint. Both
entry modes use the same recorder, compiler format, and governed runtime. The
browser exposes a full structured layer:

- **Structural rung**: reads the DOM element under a point, so resolution and
  [identity](identity-gate.md) can use stable selectors and structured text
  where they exist.
- **Structural postconditions**: URL change, title change, new-tab opened.
- **CI-friendly**: no OS permissions, no display server; the whole record →
  compile → replay loop runs in a container.
- **Existing-session recording**: attach mode preserves a dedicated browser
  profile that has already completed sign-in, SSO, or 2FA. Flow refuses remote
  endpoints and ambiguous same-origin tabs. It does not navigate or close the
  external browser. It records viewport and monitor-scale transitions as new
  per-event coordinate baselines. An idle transition rebaselines and continues.
  An action that overlaps an unverified transition aborts the recording and
  publishes no complete metadata.

It shares the same bundle, resolution ladder, and identity gate as every other
substrate; nothing about the safety model is specific to it.

The Chrome extension code in `openadapt-capture` does not define a second
compiler or direct replay path. An extension acquisition path must use Flow's
shared event and evidence schema, capture-time secret exclusion, authenticated
session identity, acknowledged ordered delivery, and exact event/frame/viewport
binding before Flow accepts its recording. Source-time secret exclusion, DOM
identity, field geometry, and exact event/frame binding stay inside the
compiler contract.

### Desktop: Windows (UIA)

The public `WindowsBackend` now narrows the in-session boundary to typed
`/input` and `/uia/*` operations, disables arbitrary legacy execution by
default, screenshots the desktop, and reads the **UI Automation** tree for
identity. Crucially, an
element usually exposes `Name` / `Value` text **even when it has no stable
`AutomationId`**, so UIA-based identity is viable on most native apps even where
a durable selector is not.

Native authoring uses `openadapt-capture` rather than a second recorder inside
Flow. Capture retains the UIA element observed at each demonstrated action, and
the compiler walks that evidence to the nearest actionable node before storing
the structural target. Window-scoped recordings convert the observation into
the captured window's coordinate space before compilation. RDP and Citrix
recordings intentionally omit local client UIA: the remote application remains
an externally observed pixel surface.

Desktop (and Citrix/VDI) is the **differentiated wedge**: the work that has no
web UI and no usable API, where a computer-use agent is the only alternative and
a wrong write is expensive. Structured desktop text distinguishes an `O` from a
`0` that OCR collapses, which is exactly what makes wrong-record writes
preventable there.

!!! info "Windows qualification evidence"
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

### Desktop: native macOS

The native macOS backend captures and drives one exact application window. It
uses the owner plus an optional title substring to bind the target, refuses
ambiguous or non-frontmost windows before input, and fails loud when Screen
Recording or Accessibility permission is unavailable.

!!! info "macOS qualification evidence"
    On one macOS 15.7.3 arm64 host, counted candidate `b1b61a5` completed 3/3
    exact-byte TextEdit trials and refused a two-window ambiguity without
    changing either file, with 0 silent incorrect successes and 0 over-halts.
    The immutable original report remains failed because cleanup warnings were
    classified as a batch failure; a separate SHA-256-bound adjudication
    verified actual cleanup and accepts only the action-effect and
    ambiguity-refusal evidence. Review [Flow PR #135](https://github.com/OpenAdaptAI/openadapt-flow/pull/135)
    and the [exact adjudication](https://github.com/OpenAdaptAI/openadapt-flow/blob/ca1b522cad215875f7471782283f8f8bb8e6c998/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json).

### Desktop: native Linux (AT-SPI)

`LinuxBackend` binds one exact AT-SPI application and top-level window, resolves
structural controls, and revalidates the target fingerprint immediately before
actuation. `--linux-allow-physical-input` is an explicit X11-only fallback when
native AT-SPI actuation is unavailable; it is never selected silently.

!!! info "Linux qualification evidence"
    Required current-main job
    [`linux-atspi-x11`](https://github.com/OpenAdaptAI/openadapt-flow/actions/runs/30059807758/job/89378981573)
    at exact commit `3de5fc67` confirmed 3/3 independently checked exact-file
    effects, 3/3 ambiguity refusals, and 3/3 stale-target refusals on a fresh
    GTK3 process per trial. It recorded 0 silent incorrect successes,
    0 over-halts, 0 operator interventions, and 0 model calls. The scope is the
    in-tree GTK3 fixture on isolated Ubuntu 24.04 X11/AT-SPI, not Wayland or
    arbitrary third-party applications.

### Remote: RDP (pixel-only)

The `FreeRDPBackend` drives a legacy application over **RDP**, read pixel-only:
no accessibility tree, no DOM, no structured layer of any kind. That is exactly
the substrate the vision-first runtime was built for. It is split into a
swappable `RDPTransport` protocol (so the adapter is CI-testable without a live
server) and a real transport over the pure-Python async `aardwolf` client,
behind the optional `rdp` extra. On a pure-pixel substrate the ladder runs on
its visual floor and the identity gate falls back to its pixel/OCR tiers, which
is why a look-alike identifier can force a [halt rather than a verify](identity-gate.md)
there.

For every consequential remote action, the runtime uses a two-phase actuation
lease. It captures a fresh frame, re-resolves the target, and rechecks identity
on that frame. The backend then captures again under its input lock and refuses
before the first input edge if pixels, dimensions, session readiness, or the
leased context changed. A potentially stale coordinate is never delivered
merely because the remote connection is still alive.

!!! info "RDP qualification evidence"
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

    A separate full governed lifecycle uses the swappable transport contract
    over a real FreeRDP3 client/server round trip. It recorded, compiled, and
    replayed a synthetic note write with 3/3 healthy effects and 3/3
    drift safe-halts, zero model calls, silent incorrect successes, false
    completions, drift writes, or healthy over-halts. That result is scoped to
    a synthetic Linux Tk task and simulated drift on the real RDP session; it
    is not the Aardwolf transport or a Windows-app qualification. Review
    [Flow PR #177](https://github.com/OpenAdaptAI/openadapt-flow/pull/177) and
    the [accepted FreeRDP lifecycle report](https://github.com/OpenAdaptAI/openadapt-flow/blob/affedc5f1f0de533a0744deaa8e30a203c91c6b3/benchmark/rdp_ladder/results.json).

### Remote-display / Citrix / VDI (pixel-only)

`CitrixWorkspaceBackend` is the released, dedicated `--backend citrix` path. It
selects the exact Citrix Workspace/Viewer owner for the host OS, optionally
binds an exact window title, refuses ambiguous targets, requires a visible
readiness marker for governed `run`, and carries the closed target into durable
resume. It is pixel-only by construction, so the same visual resolution,
identity, effect, policy, and halt contracts run without pretending a DOM or
accessibility tree exists.

Citrix uses the same two-phase remote actuation contract as RDP. Immediately
before a consequential action, OpenAdapt reacquires the exact Workspace window,
focus, geometry, readiness, fresh pixels, resolved target, and record identity.
The first input edge is refused if any of that evidence changes after
resolution.

!!! info "Citrix qualification evidence"
    The accepted no-DOM qualification completed 3/3 healthy effects and 3/3
    severe-drift safe-halts, with 0 model calls, silent incorrect successes,
    false completions, healthy over-halts, or drift writes. Review
    [Flow PR #183](https://github.com/OpenAdaptAI/openadapt-flow/pull/183) and
    the [immutable report](https://github.com/OpenAdaptAI/openadapt-flow/blob/f6faac5b900b78cbda5980de0e983a9f987285ac/benchmark/citrix_workspace/results.json).

    The accepted artifact explicitly records `code_readiness_accepted: true`
    and `ica_hdx_accepted: false`. It qualifies the shipped Workspace-window
    backend contract over a no-DOM canvas stand-in, not a counted real ICA/HDX
    batch. The exact client, codec, latency, DPI, lock/readiness, input,
    identity, and effect matrix is qualified separately for consequential
    ICA/HDX use.

## Status at a glance

| Backend | Substrate | Structural rung | Identity signal | Support |
|---|---|---|---|---|
| Playwright (web) | Browser DOM | Yes (DOM) | Structured text (DOM) | **First-class**: structured DOM identity |
| `WindowsBackend` | Native Windows | Via UIA | UI Automation `Name`/`Value` | **First-class**: UIA structured identity |
| Native macOS | Native macOS | Exact window candidate; AX candidate metadata | Window identity and pixel/OCR floor | **First-class**: window identity and AX metadata |
| `LinuxBackend` | Native Linux | Yes (AT-SPI) | Exact app/window plus AT-SPI role/name/fingerprint | **First-class**: AT-SPI structured identity |
| `FreeRDPBackend` | Pixel-only network RDP | No | Pixel / OCR floor | **First-class**: pixel/OCR identity floor |
| `CitrixWorkspaceBackend` | Citrix Workspace / VDI window | No | Exact Workspace owner/title/readiness plus pixel/OCR floor | **First-class**: governed pixel identity floor |

Every backend runs the same bundle, resolution ladder, identity gate, and effect
verification. What varies per substrate is how high up the
[capability ladder](capability-ladder.md) a given app lets the runtime climb, and
every workflow is qualified in its real environment before it carries
consequential work. [Qualification evidence](../get-started/what-works-today.md)
records the exact task, environment, oracle, and accepted scope behind each
result.
