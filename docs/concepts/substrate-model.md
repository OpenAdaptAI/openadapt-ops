# The substrate model: one runner, many surfaces

Work lives on different surfaces. A referral moves through a browser app; a
clinical chart lives in a native Windows EMR; a legacy line-of-business tool is
reachable only as pixels over Citrix. OpenAdapt compiles and replays the same
[workflow program](workflow-ir.md) on all three, because the runtime sits behind
one small [backend protocol](backends.md) and one **substrate-agnostic runner**.

The runner does not know which surface it is driving. It routes on a single
field, `workflow.target_kind`. Everything above it is identical across surfaces:
the resolution ladder, the [identity gate](identity-gate.md),
[effect verification](effect-verification.md), and the
[halt-learn loop](halt-learn-loop.md).

## Two axes, one contract

Two orthogonal questions about any run, kept separate:

- **Substrate**: *what surface is being driven?* Browser, Windows UIA, native
  macOS, native Linux, RDP, or Citrix/VDI.
- **Deployment**: *where does the run execute and who owns the data?* See
  [the deployment matrix](deployment-matrix.md).

A single runner contract spans both. It speaks the same `enqueue` /
`run-callback` shapes regardless of substrate or deployment: a job is a signed
bundle to fetch, a signed report to write back, a target, an allowed-host list,
parameters, and a secrets reference. The control plane routes; it never sees
pixels or resolved field values.

```mermaid
flowchart TD
    J[Job: signed bundle + target + params] --> R{{Substrate-agnostic runner}}
    R -->|target_kind = web| W[Browser sandbox<br/>Playwright backend]
    R -->|target_kind = desktop| D[Native desktop<br/>Windows / macOS / Linux]
    R -->|target_kind = remote| V[Remote display<br/>RDP / Citrix]
    W --> L[Resolution ladder · identity gate · effect verification]
    D --> L
    V --> L
    L --> C[[Signed report + minimized callback]]
```

## The web substrate

A headless Chromium driven by Playwright exposes a full DOM, so the ladder's
structural rung re-finds a recorded target as an *element* and the identity gate
compares **structured text** where `0` and `O` are distinct characters. The
whole record → compile → replay loop runs in CI with no OS permissions. See
[Backends](backends.md#web-playwright).

## Native desktop and remote applications: the wedge

The differentiated work has no web UI and no usable API: a native Windows EMR, a
WinForms line-of-business app, a clinical tool published through Citrix. This is
where a computer-use agent is otherwise the only option and where a wrong write
is expensive.

The released backends cover it behind the same protocol:

- **`WindowsBackend`** drives a native Windows desktop through an in-session
  agent. Its shipped typed RPC exposes bounded screenshot, input, and UIA
  operations while the legacy arbitrary-execution route stays disabled by
  default. It reads the **UI Automation** tree for identity. Crucially, most
  native controls expose `Name` / `Value` text **even without a stable
  `AutomationId`**, so structured identity is viable on desktop, not just the
  browser.
- The **native macOS backend** binds one exact application window and uses
  Accessibility metadata plus retained visual evidence.
- **`LinuxBackend`** binds one exact AT-SPI application and top-level window,
  uses structural actuation where available, and refuses ambiguous or stale
  native targets.
- **`FreeRDPBackend`** drives a legacy app over RDP as **pure pixels**: no
  accessibility tree, no DOM, no structured layer. This is the floor the
  vision-first runtime was built for, the lowest-fidelity surface a Citrix/VDI
  deployment may expose.
- **`CitrixWorkspaceBackend`** is the dedicated `--backend citrix` preset over
  the exact-window remote-display backend. It binds the Workspace owner/title
  and gates readiness before governed input.

Consequential RDP and Citrix input is two-phase. The runtime acquires a fresh
actuation frame, re-resolves the target, and rechecks record identity. The
backend then verifies the same session/window, focus where applicable,
geometry, readiness, and pixels immediately before the first input edge. A
change invalidates the one-shot lease and halts instead of reusing stale
coordinates.

!!! info "Citrix / RDP is pixel-first: the identity gate adapts to it"
    On a pure-pixel substrate the ladder runs on its visual floor and the
    identity gate uses its pixel/OCR tiers. When an identifier is genuinely
    ambiguous at that fidelity (a same-name/same-DOB record whose MRN differs by
    a single `O`/`0` glyph), the gate
    **[halts rather than guesses](identity-gate.md)** by design. That is the same
    never-click-the-wrong-record guarantee every substrate enforces. Each surface
    verifies with the highest-fidelity signal it exposes, and structured layers
    (a browser DOM, Windows UIA) resolve that class outright. Per-substrate
    behavior is detailed in
    [LIMITS](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).

## Where the desktop substrate runs today

Desktop, RDP, and Citrix substrates run **inside the customer boundary**:
locally, self-hosted/on-prem on a machine the customer controls (see
[Deploy on-prem](../guides/deploy-on-prem.md)), or in a configured
customer-controlled cloud runtime. The public managed runner executes approved
browser workflows. Customer-controlled runtimes can connect to the same Cloud
control plane for reports and governed operation without moving sensitive live
observations into the shared managed-browser boundary.

OpenAdapt also runs the desktop substrate in its own infrastructure as an
**internal, licensing-gated lane** rather than a public offer. There the Windows
surface is a **QEMU/KVM guest on a Linux host**, streamed for
monitoring/recording over **RDP through Apache Guacamole**. RDP is Windows-native,
so nothing streaming-related runs inside the guest and the VM stays clean for
snapshot-revert between runs. The deterministic replay path itself drives the
guest through the in-session agent contract, not the stream.

Desktop execution is provisioned per qualified workflow, so Windows licensing,
warm-state policy, isolation, recovery, and cost are explicit deployment inputs
rather than hidden properties of the runner. The same job and report contract
drives a customer-owned Windows session unchanged. Multi-tenant hosting of the
desktop substrate in OpenAdapt's cloud is deferred; it is not part of any public
offer.

## Qualification record

- The **web substrate** (Playwright) is the substrate used by the public managed
  subscription.
- Windows UIA is qualified for the counted
  `20260717-candidate-56759c8-v2` exact in-tree WinForms matrix:
  3/3 completed trials, 3/3 independent SQLite effects, 3/3 stale-target
  refusals, 3/3 ambiguity refusals, 0 silent incorrect successes, 0 over-halts,
  and 0 model calls. Earlier rejected diagnostic matrices remain in the report
  and are not counted acceptance trials.
- Native macOS is qualified for one-host TextEdit evidence: 3/3 exact-byte effects
  and a two-window ambiguity refusal, with 0 silent incorrect successes and 0
  over-halts. The original batch remains failed due to cleanup-warning
  classification; a hash-bound adjudication verified actual cleanup and accepts
  those effects/refusal.
- Linux AT-SPI is a required current-main CI lane. Exact Flow commit
  `3de5fc67` confirmed 3/3 exact-file effects, 3/3 ambiguity refusals, and
  3/3 stale-target refusals on the in-tree GTK3/X11 fixture, with zero silent
  incorrect successes, over-halts, operator interventions, or model calls.
- RDP has complementary accepted evidence: 3/3 Aardwolf-over-Windows
  transport/input effects, plus a full real-FreeRDP record → compile → governed
  replay lifecycle with 3/3 healthy effects and 3/3 drift safe-halts. The
  [FreeRDP artifact](https://github.com/OpenAdaptAI/openadapt-flow/blob/affedc5f1f0de533a0744deaa8e30a203c91c6b3/benchmark/rdp_ladder/results.json)
  covers a synthetic Linux task on a real protocol round trip; it does not
  inherit the separate Windows/Aardwolf scope.
- Citrix/VDI ships as dedicated `--backend citrix` with exact Workspace-window
  binding, readiness gating, and durable resume. Its accepted no-DOM contract
  evidence records 3/3 healthy effects and 3/3 drift safe-halts. The artifact
  explicitly records `ica_hdx_accepted: false`: a counted real ICA/HDX batch is
  a separate evidence/qualification boundary, not a missing backend.
- The public hosted subscription currently entitles approved browser workflows.
  Desktop and virtual-desktop deployments are scoped and qualified separately.

These results qualify the substrate mechanisms for their named tasks. The
[complete evidence appendix](../get-started/what-works-today.md) carries exact
commits, environments, oracles, refusal checks, and failure taxonomies. Backend
expansion does not require a different bundle or safety model: the same ladder
and gates apply while each workflow is qualified in its real environment.
