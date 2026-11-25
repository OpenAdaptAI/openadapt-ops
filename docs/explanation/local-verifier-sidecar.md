---
description: >-
  How OpenAdapt wraps any closed-source or open-source agent as a black box and
  runs its open-source LoRA adapters on a separate local 4B verifier sidecar.
---

# Black-box agent wrapping and the local 4B verifier sidecar

OpenAdapt works with any closed-source or open-source agent — Claude, GPT,
Gemini, Codex, browser-use, or your own Python script — with **zero access to
your agent's weights**.

You never fine-tune, patch, or host your agent's model to use OpenAdapt.
OpenAdapt sits outside the agent as a wrapper or local tool server. When visual
verification or prompt-injection screening is enabled, OpenAdapt's open-source
LoRA adapters (`Veto-4B-r6`, `taint-guard`) run solely on OpenAdapt's own local
4B verifier sidecar (~3.15 GB VRAM) on your host.

## Architecture boundary

```text
[Any Agent (Claude / GPT / Gemini / Codex / Open-Source)]
                            |
                            |  typed tool call or `openadapt wrap`
                            |  (zero access to agent weights)
                            v
           [OpenAdapt Wrapper & Compiled Tool]
                            |
                            |  deterministic UI replay (0 model calls)
                            v
 [Deterministic Read-Back + Optional Local 4B Sidecar]
          (Veto-4B-r6 / taint-guard LoRAs)
```

## What each layer owns

| Layer | Runs where | Sees agent weights? | Purpose |
|---|---|---|---|
| **Your agent** | Cloud API or your own host | Yes (owned by you / vendor) | Decides which task to run and supplies inputs |
| **OpenAdapt wrapper & compiled tool** | Local host (`openadapt wrap` or `openadapt agent serve`) | **No** | Executes compiled workflows at 0 model calls and checks outcomes via deterministic read-back |
| **Local 4B verifier sidecar** *(optional)* | Local host (~3.15 GB VRAM) | **No** | Runs OpenAdapt's open-source LoRA adapters (`Veto-4B-r6`, `taint-guard`) on local screenshots with zero screenshot egress |

## Why the verifier runs as a separate sidecar

1. **Works with frontier API models.** Hosted models like Claude, GPT, and
   Gemini do not expose weights for LoRA adapters. Running verification on an
   independent local sidecar lets you keep your preferred frontier agent while
   still checking outcomes and screening untrusted screen content locally.
2. **No screenshot egress.** When pixel-level checks are needed (for example on
   Windows RDP, Citrix, or legacy desktop apps), screenshots stay on the local
   machine and are inspected by the 4B sidecar instead of leaving your network.
3. **Fast adapter switching.** Because the base 4B model stays loaded in ~3.15
   GB VRAM, OpenAdapt can swap between small task-specific LoRA adapters
   (`Veto-4B-r6` for state verification, `taint-guard` for prompt-injection
   detection) without reloading the base model or touching the calling agent.

## Related guides

- [Connect an agent](../how-to/connect-an-agent.md) — expose compiled workflows
  over local MCP or wrap an existing agent script.
- [How a save is checked](verification.md) — deterministic read-back checks and
  what happens when a save cannot be confirmed.
