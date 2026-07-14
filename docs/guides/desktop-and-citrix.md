# Desktop and Citrix

!!! warning "Target-state page — the desktop backends exist but are not wired into the CLI"
    The `WindowsBackend` (native Windows over the in-session agent) and the
    `FreeRDPBackend` (pixel-only over RDP) both **exist** in the engine and
    implement the same `Backend` protocol as the web backend. What is missing is
    the **CLI selector** to run a bundle against them (`replay`/`run` build the
    web backend only). The commands below show the **intended UX**; today the same
    path runs from the library API. See the [gap list](#what-is-not-yet-wired).

Many enterprise workflows live in applications the browser backend cannot reach:
native Windows EMRs, WinForms/WPF line-of-business apps, and legacy systems
delivered as a **Citrix or RDP remote-display stream**. The demonstration
compiler drives all of these with the **same bundle, resolution ladder, effect
verification, and run report** — the substrate changes, the workflow does not.

## Two desktop substrates

| | Native Windows | Citrix / RDP remote display |
|---|---|---|
| Backend | `WindowsBackend` (in-session agent HTTP API) | `FreeRDPBackend` (RDP transport) |
| Observation | Pixels; UIA text for identity | **Pixels only** — no accessibility, no DOM, nothing |
| Structural rung | Not available | Not available |
| Identity signal | UIA element text under the point | **OCR only** (no UIA over the pixel stream) |
| Runs where | On/beside the Windows host | Beside the Citrix/RDP client, reading its pixels |

Both are **vision-anchored**: PNG frames in, pixel-coordinate clicks and keys
out. That is exactly what the runtime was built for. The honest cost is that the
**structural rung of the [resolution ladder](../concepts/self-healing.md) is
gone** — template, OCR, and geometry carry the whole load — and, over Citrix,
even the identity signal drops to OCR.

## Native Windows

The engine drives native Windows through an **in-session agent**: an HTTP server
in the interactive Windows session exposing `GET /screenshot` and
`POST /execute_windows`. See
[Backends → Windows](../reference/backends.md#windows-the-in-session-agent) for
the contract and the [session-0 constraint](../reference/backends.md#the-session-0-constraint).

```bash
# Intended UX (not yet wired from the CLI):
openadapt flow run bundle --backend windows \
  --agent-url http://127.0.0.1:5912 --config deployment.yaml
```

Identity checks use the **UI Automation (UIA)** text of the element under the
click point where one exists — a higher-fidelity signal than OCR, even for
elements that carry no stable `AutomationId`. Where UIA returns nothing, the step
falls back to OCR or halts, per policy; it never silently clicks an unverified
target.

## Citrix and RDP

When the application is only reachable as a **remote-display stream**, the engine
reads the RDP framebuffer and sends pointer/keyboard/wheel events back over the
same connection. There is **no structured layer at all** — this is the
pixel-only extreme the vision runtime was designed for.

```bash
# Intended UX (not yet wired from the CLI):
openadapt flow run bundle --backend rdp \
  --rdp-host citrix-vda.internal --config deployment.yaml
```

!!! warning "Citrix limits, stated honestly"
    - **Pixel-only.** No accessibility tree, no DOM, no UIA — every target is
      resolved from the picture. Template/OCR/geometry drift healing still works;
      the structural rung does not exist here.
    - **Identity is OCR-grade** over the pixel stream. The [identity
      gate](../concepts/identity-gate.md) is armed on a *subset* of click steps
      (those with a stable discriminating band); the run report states exactly
      which steps were armed and which were not, and why.
    - **On-screen read-back is not independent verification.** Reading a value
      back from the same pixels you just typed proves the pixels, not that the
      underlying record changed. For any consequential write, the authoritative
      check is [effect verification](../concepts/effect-verification.md) against
      the system of record — configure it, or the write halts rather than being
      trusted.

## Deploying beside Citrix (the BYOC form)

The productized form of a Citrix workflow is a Connector + engine running on a
Windows host **beside the clinic's Citrix Workspace**, inside their perimeter:
the pixels never leave the building, and the control plane sees only PHI-free
metadata. That packaging (MSI/service + Citrix-adjacency runbook) is the
highest-value [BYOC](deploy-byoc.md) lane and is **in progress**. Today the same
mechanism runs [self-hosted / on-prem](deploy-on-prem.md).

## What is not yet wired

- **No CLI backend selector.** `replay` / `run` construct the web backend
  unconditionally; `--backend windows` / `--backend rdp`, `--agent-url`, and
  `--rdp-host` do **not** exist on the CLI. The `WindowsBackend` and
  `FreeRDPBackend` are reachable only through the library API.
- **`record --backend windows`** (global-hook desktop recording wired to the CLI)
  is not exposed; desktop recording runs through the evals/Parallels test harness.
- **Automated Windows-host provisioning** (the cloud `desktop` runner:
  Windows-in-QEMU + streaming) is unbuilt — bring your own Windows host or VM.
- The **Citrix Connector packaging** (MSI/service) is unbuilt.
