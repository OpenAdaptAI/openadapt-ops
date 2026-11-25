---
title: OpenAdapt documentation
description: >-
  OpenAdapt compiles one or more demonstrations into a repeatable GUI workflow,
  checks each save through the system of record or a separate UI session, and
  writes signed Ed25519 receipts.
hide:
  - toc
  - navigation
---

<div class="oa-docs-home" markdown>

<section class="oa-hero-shell" markdown>

<div class="oa-pill-row">
  <span class="oa-pill oa-pill--verified">0 model calls on healthy runs</span>
  <span class="oa-pill oa-pill--link">Flow 4.0 · Python 3.11+</span>
  <span class="oa-pill">Signed Ed25519 receipts</span>
</div>

<p class="oa-docs-kicker">OpenAdapt documentation</p>

# Compile GUI workflows.<br>Verify every save.

<p class="oa-docs-lede">OpenAdapt is a compiler and verification runtime for GUI workflows. Build a deterministic program from one or more demonstrations, check each save through the system of record or a separate UI session, and stop whenever proof is missing.</p>

<p class="oa-docs-intro">Built for browser, Windows, macOS, Linux, RDP, and Citrix applications. A healthy compiled run makes zero AI model calls and keeps data inside your network boundary.</p>

<div class="oa-hero-actions" markdown>

[Try the quickstart](tutorials/quickstart.md){ .md-button .md-button--primary }
[How OpenAdapt works](explanation/how-it-works.md){ .md-button }

</div>

</section>

<div class="oa-docs-start" markdown>

<div class="oa-docs-start-copy" markdown>

### Run a checked task locally

Watch one compiled workflow confirm a save in a synthetic clinic app, then stop when a test backend fakes a success banner and drops the write. Runs in a hidden browser by default with no account or API key.

</div>

<div class="oa-docs-command" markdown>

```bash
uvx --python 3.12 openadapt@latest quickstart
```

[Other install options](tutorials/quickstart.md#run-it) · [Command reference](reference/cli.md)

</div>

</div>

## Three ways to run OpenAdapt

<div class="oa-modes-grid" markdown>

<div class="oa-mode-card" markdown>
<span class="oa-mode-icon oa-mode-icon--verified" aria-hidden="true">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
</span>

### Local wrapper and 4B sidecar

Wrap any agent (Claude Code, OpenAI CUA, Browser Use, Playwright, or custom scripts) with `openadapt wrap` and an optional local `Veto-4B-r5` sidecar (~3.13 GB VRAM) with zero screenshot egress.

<span class="oa-mode-footer">[Local verifier sidecar &rarr;](explanation/local-verifier-sidecar.md)</span>
</div>

<div class="oa-mode-card" markdown>
<span class="oa-mode-icon" aria-hidden="true">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>
</span>

### OpenAdapt Hosted and BYOC

Run web workflows on our managed Linux runner billed only on verified runs, or pair your own Windows, Linux, or VPC host with `openadapt connect` so credentials and PHI stay inside your network.

<span class="oa-mode-footer">[Deploy and BYOC &rarr;](how-to/deploy.md)</span>
</div>

<div class="oa-mode-card" markdown>
<span class="oa-mode-icon" aria-hidden="true">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
</span>

### Bring your own sandbox

Attach to Browserbase, E2B, Daytona, or Browser Use over `--cdp-url` and stream signed Ed25519 receipts and human approval gates directly to `app.openadapt.ai`.

<span class="oa-mode-footer">[Cloud sandboxes &rarr;](how-to/verify-cloud-sandboxes.md)</span>
</div>

</div>

## Core execution pipeline

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 245" role="img" aria-labelledby="oa-pipe-title oa-pipe-desc">
  <title id="oa-pipe-title">OpenAdapt core execution pipeline</title>
  <desc id="oa-pipe-desc">One or more demonstrations are recorded, compiled into a deterministic workflow program, replayed with zero model calls, checked at the commit boundary through the system of record or a separate UI session, and attested with a signed Ed25519 receipt. Any failed or uncertain check stops the run and routes to human review or guarded teach repair.</desc>
  <defs>
    <marker id="oa-arr-accent" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="oa-arr-verified" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
    <marker id="oa-arr-stopped" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-stopped"/>
    </marker>
  </defs>

  <g class="oa-svg-node">
    <rect x="14" y="24" width="156" height="108" rx="12" class="oa-svg-panel"/>
    <text x="30" y="48" font-size="10.5" class="oa-svg-accent">01 · RECORD</text>
    <text x="30" y="70" font-size="14" class="oa-svg-title">Demonstrate</text>
    <text x="30" y="91" font-size="11.5" class="oa-svg-muted">Person or agent runs</text>
    <text x="30" y="109" font-size="11.5" class="oa-svg-muted">the task 1+ times</text>
  </g>

  <path d="M170,78 L198,78" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#oa-arr-accent)"/>

  <g class="oa-svg-node">
    <rect x="204" y="24" width="156" height="108" rx="12" class="oa-svg-panel"/>
    <text x="220" y="48" font-size="10.5" class="oa-svg-accent">02 · COMPILE</text>
    <text x="220" y="70" font-size="14" class="oa-svg-title">Workflow IR</text>
    <text x="220" y="91" font-size="11.5" class="oa-svg-muted">DOM, UIA, AX, or API</text>
    <text x="220" y="109" font-size="11.5" class="oa-svg-muted">Certify and qualify</text>
  </g>

  <path d="M360,78 L388,78" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#oa-arr-accent)"/>

  <g class="oa-svg-node">
    <rect x="394" y="24" width="170" height="108" rx="12" class="oa-svg-panel-link"/>
    <circle cx="546" cy="42" r="4" class="oa-svg-gate-dot oa-svg-gate-dot--accent"/>
    <text x="410" y="48" font-size="10.5" class="oa-svg-accent">03 · REPLAY</text>
    <text x="410" y="70" font-size="14" class="oa-svg-title">Deterministic run</text>
    <text x="410" y="91" font-size="11.5" class="oa-svg-muted">0 AI model calls</text>
    <text x="410" y="109" font-size="11.5" class="oa-svg-muted">Right-record pre-check</text>
  </g>

  <path d="M564,78 L592,78" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#oa-arr-accent)"/>

  <g class="oa-svg-node">
    <rect x="598" y="24" width="172" height="108" rx="12" class="oa-svg-panel"/>
    <text x="614" y="48" font-size="10.5" class="oa-svg-accent">04 · COMMIT GATE</text>
    <text x="614" y="70" font-size="14" class="oa-svg-title">Verify effect</text>
    <text x="614" y="91" font-size="11.5" class="oa-svg-muted">API, SQL, FHIR read-back</text>
    <text x="614" y="109" font-size="11.5" class="oa-svg-muted">or separate UI session</text>
  </g>

  <path d="M770,78 L798,78" class="oa-svg-line-verified oa-svg-flow" marker-end="url(#oa-arr-verified)"/>

  <g class="oa-svg-node">
    <rect x="804" y="24" width="162" height="108" rx="12" class="oa-svg-panel-verified"/>
    <circle cx="948" cy="42" r="4.5" class="oa-svg-gate-dot oa-svg-gate-dot--verified"/>
    <text x="820" y="48" font-size="10.5" class="oa-svg-verified-txt">05 · RECEIPT</text>
    <text x="820" y="70" font-size="14" class="oa-svg-title">VERIFIED</text>
    <text x="820" y="91" font-size="11.5" class="oa-svg-muted">Signed Ed25519 proof</text>
    <text x="820" y="109" font-size="11.5" class="oa-svg-muted">Safe to share · /r/&lt;id&gt;</text>
  </g>

  <!-- Halt & Teach feedback loop -->
  <path d="M684,132 C684,182 654,186 484,186" class="oa-svg-line-stopped oa-svg-flow-slow" marker-end="url(#oa-arr-stopped)"/>
  <g class="oa-svg-node">
    <rect x="204" y="158" width="276" height="58" rx="10" class="oa-svg-panel-stopped"/>
    <circle cx="464" cy="176" r="4" class="oa-svg-gate-dot oa-svg-gate-dot--stopped"/>
    <text x="220" y="180" font-size="11" class="oa-svg-stopped-txt">HALT / RECONCILIATION_REQUIRED</text>
    <text x="220" y="200" font-size="11.5" class="oa-svg-muted">Stop safely, inspect, teach guarded fix</text>
  </g>
  <path d="M282,158 L282,136" class="oa-svg-line-stopped oa-svg-flow-slow" marker-end="url(#oa-arr-stopped)"/>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Pipeline:</strong> Decisions happen once at compile time; runtime enforces pre-save identity and post-save read-back. Hover any stage to inspect.</span>
  <span><a href="explanation/how-it-works/">Read architecture &rarr;</a></span>
</figcaption>
</figure>

## Start in three steps

<div class="oa-steps-strip" markdown>

<div class="oa-step-card" markdown>
<p class="oa-step-num">Step 01</p>

### Demonstrate the task

Run `openadapt record` on a web page, desktop app, or remote session (once for a simple path, or a few times with `openadapt compile --induce` to cover variations), or let an AI agent perform the task once while OpenAdapt records it, ideally on test data.

</div>

<div class="oa-step-card" markdown>
<p class="oa-step-num">Step 02</p>

### Compile and qualify

Compile the recording into an inspectable program, attach record checks, and qualify it against planted faults.

</div>

<div class="oa-step-card" markdown>
<p class="oa-step-num">Step 03</p>

### Run and verify

Execute deterministically with zero model calls per step, or expose the workflow to any AI agent over MCP with signed receipts.

</div>

</div>

## Developer primitives

<div class="oa-bento-grid" markdown>

<div class="oa-bento-card oa-bento-card--wide" markdown>

### Deterministic compiled replay and `@openadapt.jit`

A computer-use agent sends screenshots to a model on every click. OpenAdapt compiles one or more demonstrations into a structured workflow program targeting DOM, Windows UI Automation, macOS Accessibility, or API calls first, falling back to pixels only when the app exposes no structure. In Python, wrap repeated agent flows with `@openadapt.jit`.

<span class="oa-bento-meta">0 model calls · repeatable · inspectable IR</span>

</div>

<div class="oa-bento-card oa-bento-card--wide" markdown>

### Commit-boundary verification

Every consequential save is guarded before and after the write. Before acting, a right-record check confirms the intended entity is open. After saving, a read-back through the system of record (REST, GraphQL, FHIR, SQL, or file export) or a separate signed-in UI session confirms what persisted.

<span class="oa-bento-meta">3-valued verdicts · never trusts a banner</span>

</div>

<div class="oa-bento-card" markdown>

### Signed Ed25519 receipts and `/r/<id>`

Verified runs emit portable JSON receipts containing digests, check tiers, `agent_used`, and `verifier_adapter` provenance with no screenshots, typed values, or free text. Check offline with `openadapt verify` or online at `app.openadapt.ai/r/<id>`.

<span class="oa-bento-meta">offline verification · safe to share</span>

</div>

<div class="oa-bento-card" markdown>

### MCP tools and Starter Skills

Expose compiled workflows as typed MCP tools (`openadapt agent serve` or `openadapt mcpify --from-compiled`), verify writes from Python with `openadapt.verify`, or pull verified Starter Skills from `app.openadapt.ai/registry`.

<span class="oa-bento-meta">MCP stdio · idempotent request_id</span>

</div>

<div class="oa-bento-card" markdown>

### Desktop app and local data boundary

OpenAdapt Desktop `0.35.0` brings Before/After step screenshot previews with a blur privacy toggle in Watch Run. Recordings, credentials, and typed values stay on the runner you control with optional AES-256-GCM encryption and Presidio scrubbing.

<span class="oa-bento-meta">on-prem · VPC · strict no-outbound</span>

</div>

</div>

## Jump to what you need

<nav class="oa-docs-paths" aria-label="Documentation shortcuts" markdown>

[<strong>Build your first workflow</strong><span>Record a read-only task, compile it, inspect the graph, and replay it.</span>](tutorials/first-workflow.md){ .oa-docs-path }

[<strong>Connect an agent</strong><span>Serve compiled workflows over MCP, use <code>@openadapt.jit</code>, or verify writes with <code>openadapt.verify</code>.</span>](how-to/connect-an-agent.md){ .oa-docs-path }

[<strong>Find a command</strong><span>Install, record, compile, qualify, run, and verify receipts from the CLI.</span>](reference/cli.md){ .oa-docs-path }

[<strong>Understand a result</strong><span>Read transaction outcomes and decide what is safe to retry vs. reconcile.</span>](reference/outcomes.md){ .oa-docs-path }

[<strong>Deploy a workflow</strong><span>Choose local, on-premises, BYOC, cloud sandboxes, or OpenAdapt Hosted.</span>](how-to/deploy.md){ .oa-docs-path }

[<strong>Review security and data</strong><span>Inspect data handling, deployment boundaries, release integrity, and procurement details.</span>](security/index.md){ .oa-docs-path }

</nav>

<div class="oa-docs-more" markdown>

### Go deeper

[How the compiler works](explanation/how-it-works.md#a-program-not-a-model-in-a-loop) · [How a save is checked](explanation/verification.md) · [Local verifier sidecar](explanation/local-verifier-sidecar.md) · [Receipts and signing](reference/receipts.md) · [Data handling](security/data-handling.md) · [Release integrity](security/release-integrity.md) · [Packages](reference/packages.md) · [Versions and compatibility](reference/compatibility.md) · [Validated systems and limits](explanation/limits.md)

</div>

</div>
