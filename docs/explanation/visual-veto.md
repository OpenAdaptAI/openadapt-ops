---
description: >-
  How the Multi-LoRA visual veto registry, tenant-isolated calibration
  collector, and shared BYOC HTTP server add local visual screening alongside
  system-of-record read-back.
---

# Visual veto and Multi-LoRA runtime

!!! info "Upcoming release"
    This page documents the Multi-LoRA visual veto registry, calibration
    collector, and shared BYOC HTTP server staged in
    [OpenAdapt#2576](https://github.com/OpenAdaptAI/OpenAdapt/pull/2576).

Independent system-of-record read-back remains the authority required for a
`VERIFIED` signed receipt. When a workflow also runs local visual screening at
the commit boundary, OpenAdapt provides a Multi-LoRA visual veto stack built
around open-weights models published on Hugging Face:

- Base model: [OpenAdapt-Veto-9B-v4](https://huggingface.co/OpenAdapt/OpenAdapt-Veto-9B-v4)
- Example per-app LoRA adapter: [OpenAdapt-Veto-9B-app-dark-saas](https://huggingface.co/OpenAdapt/OpenAdapt-Veto-9B-app-dark-saas)

The visual veto layer runs inside your boundary (4-bit NF4 on a local GPU, or
on a single shared GPU inside your VPC). It can **veto** a suspicious screen
state and escalate to a person, and it never overrides a failed or missing
system-of-record read-back.

## Hybrid read-back and Multi-LoRA architecture

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 275" role="img" aria-labelledby="oa-veto-title oa-veto-desc">
  <title id="oa-veto-title">Hybrid read-back and Multi-LoRA visual veto architecture</title>
  <desc id="oa-veto-desc">Zero-GPU workstations run compiled workflows and send pre/post screenshot checks over HTTPS inside the customer VPC to a shared BYOC HTTP server (byoc_veto_server.py). The server authenticates the tenant key in constant time and routes requests to MultiLoraVetoRouter, which hot-swaps a compact per-app LoRA adapter on a single 4-bit NF4 base model. In parallel, Tier 1 deterministic read-back queries the system of record. Any VETO or ABSTAIN routes to HALT_ESCALATE; operator overrides log structural metadata and SHA-256 hashes into CalibrationCollector.</desc>
  <defs>
    <marker id="vt-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="vt-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
    <marker id="vt-arr-s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-stopped"/>
    </marker>
  </defs>

  <!-- Workstation -->
  <rect x="14" y="42" width="186" height="148" rx="12" class="oa-svg-panel"/>
  <text x="28" y="66" font-size="10" class="oa-svg-accent">ZERO-GPU WORKSTATION</text>
  <text x="28" y="88" font-size="13.5" class="oa-svg-title">Local runner</text>
  <text x="28" y="110" font-size="11" class="oa-svg-muted">Compiled replay</text>
  <text x="28" y="128" font-size="11" class="oa-svg-muted">Pre/post screenshots</text>
  <text x="28" y="152" font-size="10" class="oa-svg-mono">post_verify_request()</text>
  <text x="28" y="170" font-size="10" class="oa-svg-muted">Stays inside VPC</text>

  <!-- Split to Read-back + BYOC Veto Server -->
  <path d="M200,82 L248,60" class="oa-svg-line-verified" marker-end="url(#vt-arr-v)"/>
  <path d="M200,146 L248,168" class="oa-svg-line-accent" marker-end="url(#vt-arr)"/>

  <!-- Tier 1 Read-back -->
  <rect x="254" y="16" width="440" height="84" rx="12" class="oa-svg-panel-verified"/>
  <text x="270" y="39" font-size="10" class="oa-svg-verified-txt">PRIMARY PROOF · SYSTEM OF RECORD</text>
  <text x="270" y="60" font-size="13.5" class="oa-svg-title">Deterministic read-back (REST, GraphQL, FHIR, SQL)</text>
  <text x="270" y="81" font-size="11" class="oa-svg-muted">Required authority for VERIFIED receipts; visual veto never replaces it</text>

  <!-- Shared BYOC Veto Server -->
  <rect x="254" y="114" width="440" height="144" rx="12" class="oa-svg-panel-link"/>
  <text x="270" y="138" font-size="10" class="oa-svg-accent">CUSTOMER VPC · SHARED GPU SERVER</text>
  <text x="270" y="159" font-size="13.5" class="oa-svg-title">byoc_veto_server + MultiLoraVetoRouter</text>
  <text x="270" y="181" font-size="11" class="oa-svg-muted">• Constant-time tenant auth (POST /v1/verify, GET /healthz)</text>
  <text x="270" y="199" font-size="11" class="oa-svg-muted">• Single 4-bit NF4 base (OpenAdapt-Veto-9B-v4) + serialized lock</text>
  <text x="270" y="217" font-size="11" class="oa-svg-muted">• Hot-swaps per-app LoRA by (tenant_id, app_id, workflow_id, domain)</text>
  <text x="270" y="239" font-size="10" class="oa-svg-mono">CalibrationCollector logs SHA-256 hashes + labels (no raw values)</text>

  <!-- Outcomes -->
  <path d="M694,58 L748,58" class="oa-svg-line-verified" marker-end="url(#vt-arr-v)"/>
  <path d="M694,186 L748,186" class="oa-svg-line-stopped" marker-end="url(#vt-arr-s)"/>

  <rect x="754" y="20" width="212" height="84" rx="12" class="oa-svg-panel-verified"/>
  <text x="770" y="45" font-size="12" class="oa-svg-verified-txt">VERIFIED</text>
  <text x="770" y="66" font-size="11.5" class="oa-svg-muted">Read-back confirmed and</text>
  <text x="770" y="84" font-size="11.5" class="oa-svg-muted">no visual veto raised</text>

  <rect x="754" y="128" width="212" height="114" rx="12" class="oa-svg-panel-reconcile"/>
  <text x="770" y="152" font-size="11" class="oa-svg-reconcile-txt">HALT_ESCALATE</text>
  <text x="770" y="173" font-size="11.5" class="oa-svg-muted">VETO, ABSTAIN, or HTTP 503</text>
  <text x="770" y="192" font-size="11.5" class="oa-svg-muted">from veto server stops run</text>
  <text x="770" y="211" font-size="11.5" class="oa-svg-muted">for operator review</text>
  <text x="770" y="229" font-size="10" class="oa-svg-mono">override -> calibration queue</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Shared VPC GPU:</strong> One 4-bit NF4 base model serves multiple apps via hot-swapped LoRA adapters; any abstain or backend error escalates to a person.</span>
  <span><a href="../verification/">How a save is checked &rarr;</a></span>
</figcaption>
</figure>

## Runtime components

The Multi-LoRA stack lives in `openadapt_flow` as three modules:

### 1. Declarative adapter registry and router (`multi_lora_veto.py`)

`AppAdapterRegistry` and `MultiLoraVetoRouter` load a single quantized 4-bit
NF4 base model (`OpenAdapt-Veto-9B-v4`) and hot-swap compact per-app LoRA
adapters keyed by `(tenant_id, app_id, workflow_id, domain)`:

- **Tenant isolation:** Adapters are scoped to their declared `tenant_id`;
  cross-tenant lookups are refused.
- **Per-adapter temperature calibration:** Each adapter carries its own
  calibration temperature and decision thresholds.
- **Strict abstain handling:** `ABSTAIN` always maps to `HALT_ESCALATE`, never
  to silent pass.

### 2. Shared BYOC HTTP server (`byoc_veto_server.py`)

Workstations without a local GPU can route visual checks to one GPU host inside
your VPC using the standard-library `ThreadingHTTPServer`:

- Endpoints: `POST /v1/verify` and `GET /healthz`.
- Client helper: `post_verify_request(...)`.
- Security and concurrency: constant-time tenant-key authentication (`401`/`403`),
  a serialized lock around GPU adapter hot-swaps, and HTTP `503` on backend
  errors so callers escalate rather than silently passing.

### 3. Calibration collector (`calibration_collector.py`)

When an operator reviews a halted check and overrides a false pause,
`CalibrationCollector` and `record_operator_override(...)` record a compact
entry in a tenant-scoped JSONL queue for overnight per-app LoRA calibration:

- Stores SHA-256 screenshot hashes, allowlisted structural metadata, and
  verdict labels.
- Applies PII pattern guards and enforces tenant isolation on both writes and
  reads.

## Hardware and memory tiers

OpenAdapt targets three local and customer-VPC hardware tiers so teams can size
visual screening to their existing machines. Tiers marked **under evaluation**
are active evaluation targets and do not yet carry published benchmark numbers.

| Tier | Memory budget | Model and adapter stack | Status |
|---|---|---|---|
| Edge / ultra-light | ~2 to 3 GB VRAM (8 to 16 GB laptops) | Sub-4B VLMs (`LFM2.5-VL-3B`, `Qwen3.5-4B`) | Under evaluation |
| Default local tier | 6.62 GB VRAM (16 GB Mac or 8 to 12 GB GPU) | `OpenAdapt-Veto-9B-v4` (`Qwen3.5-9B` 4-bit NF4) + per-app Multi-LoRA (116 MB adapters, in-VRAM hot-swap) | Published weights + PR `#2576` router |
| Workstation / BYOC server | 16 to 24+ GB VRAM (24 GB+ Apple Silicon or VPC GPU) | Looped-MoE / high-concurrency serving (`Inkling-2-Mini` / `Locals` on 24 GB+ Apple Silicon; `vLLM` or `SGLang` batched Multi-LoRA) | Under evaluation |

### Serving optimizations

On shared workstation and BYOC GPU deployments, the serving layer pairs
batched Multi-LoRA inference (`vLLM` or `SGLang`) with:

- **Prefix caching:** reuses the system prompt and recurring workflow framing
  across consecutive commit-boundary checks.
- **Grammar-constrained decoding:** restricts model output to the three-token
  decision vocabulary (`PASS`, `VETO`, or `ABSTAIN`) so responses parse
  deterministically with minimal latency.

## Related pages

- [How a save is checked](verification.md)
- [Deploy](../how-to/deploy.md)
- [Data handling](../security/data-handling.md)
