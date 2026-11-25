---
description: >-
  How OpenAdapt wraps any closed-source or open-source agent as a black box and
  runs its open-source LoRA adapters on a separate local 4B verifier sidecar.
---

# Black-box agent wrapping and the local 4B verifier sidecar

OpenAdapt works with any closed-source or open-source agent (Claude, GPT,
Gemini, Codex, Browser Use, Playwright, or your own Python script) with **zero
access to your agent's weights**.

You never fine-tune, patch, or host your agent's model to use OpenAdapt.
OpenAdapt sits outside the agent as a wrapper or local tool server. When visual
verification or prompt-injection screening is enabled, OpenAdapt's open-source
LoRA adapters ([`Veto-4B-r6`](https://huggingface.co/OpenAdapt/openadapt-veto-4b-r6), `taint-guard`) run solely on OpenAdapt's own local
4B verifier sidecar (~3.15 GB VRAM) on your host.

## Architecture boundary

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 230" role="img" aria-labelledby="oa-sidecar-title oa-sidecar-desc">
  <title id="oa-sidecar-title">Black-box agent wrapping and local 4B verifier sidecar</title>
  <desc id="oa-sidecar-desc">Any frontier or open-source agent calls OpenAdapt over MCP or openadapt wrap with zero access to agent weights. The local OpenAdapt wrapper executes compiled workflows with zero model calls, then checks outcomes via deterministic read-back (fresh page reload, separate UI session, or system-of-record API/SQL/FHIR) alongside an optional local 4B verifier sidecar running Veto-4B-r6 and taint-guard LoRAs in 3.15 GB VRAM with zero screenshot egress.</desc>
  <defs>
    <marker id="sc-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="sc-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
  </defs>

  <g class="oa-svg-node">
    <rect x="14" y="42" width="248" height="146" rx="12" class="oa-svg-panel"/>
    <text x="30" y="66" font-size="10" class="oa-svg-accent">BLACK-BOX CALLER</text>
    <text x="30" y="89" font-size="14" class="oa-svg-title">Any agent or script</text>
    <text x="30" y="112" font-size="11.5" class="oa-svg-muted">Claude, GPT, Gemini, Codex,</text>
    <text x="30" y="130" font-size="11.5" class="oa-svg-muted">Browser Use, Playwright</text>
    <text x="30" y="156" font-size="10.5" class="oa-svg-mono">Zero access to agent weights</text>
  </g>

  <path d="M262,115 L318,115" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#sc-arr)"/>
  <text x="268" y="102" font-size="9.5" class="oa-svg-muted">MCP / wrap</text>

  <g class="oa-svg-node">
    <rect x="324" y="42" width="270" height="146" rx="12" class="oa-svg-panel-link"/>
    <circle cx="576" cy="60" r="4" class="oa-svg-gate-dot oa-svg-gate-dot--accent"/>
    <text x="340" y="66" font-size="10" class="oa-svg-accent">LOCAL EXECUTION LAYER</text>
    <text x="340" y="89" font-size="14" class="oa-svg-title">OpenAdapt wrapper</text>
    <text x="340" y="112" font-size="11.5" class="oa-svg-muted">Deterministic UI replay</text>
    <text x="340" y="130" font-size="11.5" class="oa-svg-muted">0 model calls per healthy run</text>
    <text x="340" y="156" font-size="10.5" class="oa-svg-mono">openadapt wrap · agent serve</text>
  </g>

  <path d="M594,88 C624,88 624,68 656,68" class="oa-svg-line-verified oa-svg-flow" marker-end="url(#sc-arr-v)"/>
  <path d="M594,142 C624,142 624,166 656,166" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#sc-arr)"/>

  <g class="oa-svg-node">
    <rect x="662" y="20" width="304" height="90" rx="12" class="oa-svg-panel-verified"/>
    <circle cx="948" cy="38" r="4" class="oa-svg-gate-dot oa-svg-gate-dot--verified"/>
    <text x="678" y="44" font-size="10" class="oa-svg-verified-txt">PRIMARY PROOF</text>
    <text x="678" y="66" font-size="13.5" class="oa-svg-title">Deterministic read-back</text>
    <text x="678" y="88" font-size="11" class="oa-svg-muted">Fresh reload, API, SQL, FHIR + receipt</text>
  </g>

  <g class="oa-svg-node">
    <rect x="662" y="122" width="304" height="90" rx="12" class="oa-svg-panel"/>
    <text x="678" y="146" font-size="10" class="oa-svg-accent">OPTIONAL LOCAL SIDECAR · ~3.15 GB VRAM</text>
    <text x="678" y="168" font-size="13.5" class="oa-svg-title">4B verifier sidecar</text>
    <text x="678" y="190" font-size="11" class="oa-svg-muted">Veto-4B-r6 + taint-guard LoRAs (local only)</text>
  </g>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Black-box isolation:</strong> Keep any frontier or open-source agent while running verification and optional 4B LoRAs locally.</span>
  <span><a href="../verification/">How a save is checked &rarr;</a></span>
</figcaption>
</figure>

## What each layer owns

| Layer | Runs where | Sees agent weights? | Purpose |
|---|---|---|---|
| **Your agent** | Cloud API or your own host | Yes (owned by you or the vendor) | Decides which task to run and supplies inputs |
| **OpenAdapt wrapper and compiled tool** | Local host (`openadapt wrap` or `openadapt agent serve`) | **No** | Executes compiled workflows at 0 model calls and checks outcomes via deterministic read-back |
| **Local 4B verifier sidecar** *(optional)* | Local host (~3.15 GB VRAM) | **No** | Runs OpenAdapt's open-source LoRA adapters ([`Veto-4B-r6`](https://huggingface.co/OpenAdapt/openadapt-veto-4b-r6), `taint-guard`) on local screenshots with zero screenshot egress |

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
   ([`Veto-4B-r6`](https://huggingface.co/OpenAdapt/openadapt-veto-4b-r6) for state verification, `taint-guard` for prompt-injection
   detection) without reloading the base model or touching the calling agent.

## Quickstart: download and run `OpenAdapt/openadapt-veto-4b-r6`

The `OpenAdapt/openadapt-veto-4b-r6` LoRA adapter (81 MB, Apache-2.0) pairs
with `Qwen/Qwen3.5-4B` in 4-bit NF4 quantization (~3.15 GB VRAM) and outputs a
single verdict token (`PASS`, `VETO`, or `ABSTAIN`).

### 1. Download from Hugging Face or run via `openadapt wrap`

Download the adapter weights locally:

```bash
pip install openadapt huggingface_hub
huggingface-cli download OpenAdapt/openadapt-veto-4b-r6 --local-dir ./veto-4b-r6
```

Or let `openadapt wrap` pull the adapter directly from Hugging Face and run it
around any agent command:

```bash
openadapt wrap --veto-model OpenAdapt/openadapt-veto-4b-r6 -- <your-agent-command>
```

### 2. Serve the shared BYOC sidecar (`byoc_veto_server.py`)

When workstations have no local GPU, run `openadapt_flow.byoc_veto_server` on a
host or VPC GPU to expose `POST /v1/verify` and `GET /healthz`. The server
requires per-tenant API keys, an app allow-list, and server-issued single-use
run bindings, and returns `HALT_ESCALATE` whenever the verifier abstains or
cannot confirm a save:

```python
from openadapt_flow.byoc_veto_server import create_byoc_veto_server
from openadapt_flow.multi_lora_veto import (
    AdapterSpec,
    AppAdapterRegistry,
    MultiLoraVetoRouter,
    TenantScope,
)

# Register OpenAdapt/openadapt-veto-4b-r6 with your local LoRA backend.
base_adapter = AdapterSpec(
    adapter_id="veto-4b-r6",
    base_model="Qwen/Qwen3.5-4B",
    adapter_uri="./veto-4b-r6",
    sha256="<adapter-sha256>",
    calibrated_threshold=0.5,
    tenant_scope=TenantScope.PUBLIC,
)
registry = AppAdapterRegistry(default_base_adapter=base_adapter)
router = MultiLoraVetoRouter(
    base_model="Qwen/Qwen3.5-4B",
    registry=registry,
    backend=local_lora_backend,
)

server = create_byoc_veto_server(
    router=router,
    tenant_api_keys={"clinic-a": "<tenant-api-key>"},
    tenant_allowed_apps={"clinic-a": {"portal-ehr"}},
    host="127.0.0.1",
    port=8443,
)
server.start()
```

Verify the sidecar is ready:

```bash
curl -s http://127.0.0.1:8443/healthz
```

## Related guides

- [Connect an agent](../how-to/connect-an-agent.md): expose compiled workflows
  over local MCP or wrap an existing agent script.
- [How a save is checked](verification.md): deterministic read-back checks and
  what happens when a save cannot be confirmed.
