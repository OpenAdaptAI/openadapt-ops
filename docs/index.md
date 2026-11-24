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
  <span class="oa-pill oa-pill--link">Commit-boundary checks</span>
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

Watch one compiled workflow confirm a save in a synthetic clinic app, then halt when a test backend fakes a success banner and drops the write. No account or API key.

</div>

<div class="oa-docs-command" markdown>

```bash
uvx --python 3.12 openadapt@latest quickstart
```

[Other install options](tutorials/quickstart.md#run-it) · [Command reference](reference/cli.md)

</div>

</div>

## Core execution pipeline

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 230" role="img" aria-labelledby="oa-pipe-title oa-pipe-desc">
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

  <!-- Step 1: Record -->
  <rect x="14" y="24" width="156" height="106" rx="12" class="oa-svg-panel"/>
  <text x="30" y="48" font-size="10.5" class="oa-svg-accent">01 · RECORD</text>
  <text x="30" y="70" font-size="14" class="oa-svg-title">Demonstrate</text>
  <text x="30" y="90" font-size="11.5" class="oa-svg-muted">Person or agent runs</text>
  <text x="30" y="107" font-size="11.5" class="oa-svg-muted">the task 1+ times</text>

  <path d="M170,77 L198,77" class="oa-svg-line-accent" marker-end="url(#oa-arr-accent)"/>

  <!-- Step 2: Compile -->
  <rect x="204" y="24" width="156" height="106" rx="12" class="oa-svg-panel"/>
  <text x="220" y="48" font-size="10.5" class="oa-svg-accent">02 · COMPILE</text>
  <text x="220" y="70" font-size="14" class="oa-svg-title">Workflow IR</text>
  <text x="220" y="90" font-size="11.5" class="oa-svg-muted">DOM, UIA, AX, or API</text>
  <text x="220" y="107" font-size="11.5" class="oa-svg-muted">Certify and qualify</text>

  <path d="M360,77 L388,77" class="oa-svg-line-accent" marker-end="url(#oa-arr-accent)"/>

  <!-- Step 3: Deterministic replay -->
  <rect x="394" y="24" width="170" height="106" rx="12" class="oa-svg-panel-link"/>
  <text x="410" y="48" font-size="10.5" class="oa-svg-accent">03 · REPLAY</text>
  <text x="410" y="70" font-size="14" class="oa-svg-title">Deterministic run</text>
  <text x="410" y="90" font-size="11.5" class="oa-svg-muted">0 AI model calls</text>
  <text x="410" y="107" font-size="11.5" class="oa-svg-muted">Right-record pre-check</text>

  <path d="M564,77 L592,77" class="oa-svg-line-accent" marker-end="url(#oa-arr-accent)"/>

  <!-- Step 4: Commit gate -->
  <rect x="598" y="24" width="172" height="106" rx="12" class="oa-svg-panel"/>
  <text x="614" y="48" font-size="10.5" class="oa-svg-accent">04 · COMMIT GATE</text>
  <text x="614" y="70" font-size="14" class="oa-svg-title">Verify effect</text>
  <text x="614" y="90" font-size="11.5" class="oa-svg-muted">API, SQL, FHIR read-back</text>
  <text x="614" y="107" font-size="11.5" class="oa-svg-muted">or separate UI session</text>

  <path d="M770,77 L798,77" class="oa-svg-line-verified" marker-end="url(#oa-arr-verified)"/>

  <!-- Step 5: Signed receipt -->
  <rect x="804" y="24" width="162" height="106" rx="12" class="oa-svg-panel-verified"/>
  <text x="820" y="48" font-size="10.5" class="oa-svg-verified-txt">05 · RECEIPT</text>
  <text x="820" y="70" font-size="14" class="oa-svg-title">VERIFIED</text>
  <text x="820" y="90" font-size="11.5" class="oa-svg-muted">Signed Ed25519 proof</text>
  <text x="820" y="107" font-size="11.5" class="oa-svg-muted">Safe to share · offline</text>

  <!-- Halt & Teach feedback loop -->
  <path d="M684,130 L684,174 L484,174" class="oa-svg-line-stopped" marker-end="url(#oa-arr-stopped)"/>
  <rect x="204" y="152" width="276" height="54" rx="10" class="oa-svg-panel-stopped"/>
  <text x="220" y="174" font-size="11" class="oa-svg-stopped-txt">HALT / RECONCILIATION_REQUIRED</text>
  <text x="220" y="193" font-size="11.5" class="oa-svg-muted">Stop safely, inspect, teach guarded fix</text>
  <path d="M282,152 L282,134" class="oa-svg-line-stopped" stroke-dasharray="4 3" marker-end="url(#oa-arr-stopped)"/>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Pipeline:</strong> Decisions happen once at compile time; runtime enforces pre-save identity and post-save read-back.</span>
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

## How OpenAdapt guards every run

<div class="oa-bento-grid" markdown>

<div class="oa-bento-card oa-bento-card--wide" markdown>

### Deterministic compiled replay

A computer-use agent sends screenshots to a model on every click. OpenAdapt compiles one or more demonstrations into a structured workflow program targeting DOM, Windows UI Automation, macOS Accessibility, or API calls first, falling back to pixels only when the app exposes no structure.

<span class="oa-bento-meta">0 model calls · repeatable · inspectable IR</span>

</div>

<div class="oa-bento-card oa-bento-card--wide" markdown>

### Commit-boundary verification

Every consequential save is guarded before and after the write. Before acting, a right-record check confirms the intended entity is open. After saving, a read-back through the system of record (REST, GraphQL, FHIR, SQL, or file export) or a separate signed-in UI session confirms what persisted.

<span class="oa-bento-meta">3-valued verdicts · never trusts a banner</span>

</div>

<div class="oa-bento-card" markdown>

### Signed Ed25519 receipts

Verified runs emit portable JSON receipts containing digests, check tiers, and counts with no screenshots, typed values, or free text. Cloud-tracked runs add an Ed25519 signature anyone can verify offline.

<span class="oa-bento-meta">offline verification · safe to share</span>

</div>

<div class="oa-bento-card" markdown>

### Safe layer for AI agents

Expose compiled workflows as typed MCP tools (`openadapt agent serve`) or verify writes made by any agent or script with `openadapt.verify` and `openadapt verify serve`.

<span class="oa-bento-meta">MCP stdio · idempotent request_id</span>

</div>

<div class="oa-bento-card" markdown>

### Local-first data boundary

Recordings, credentials, and typed values stay on the runner you control. Local runs send nothing outbound by default, with optional AES-256-GCM encryption and Presidio PII scrubbing.

<span class="oa-bento-meta">on-prem · VPC · strict no-outbound</span>

</div>

</div>

## Jump to what you need

<nav class="oa-docs-paths" aria-label="Documentation shortcuts" markdown>

[<strong>Build your first workflow</strong><span>Record a read-only task, compile it, inspect the graph, and replay it.</span>](tutorials/first-workflow.md){ .oa-docs-path }

[<strong>Connect an agent</strong><span>Serve compiled workflows over MCP or verify writes from Python with <code>openadapt.verify</code>.</span>](how-to/connect-an-agent.md){ .oa-docs-path }

[<strong>Find a command</strong><span>Install, record, compile, qualify, run, and verify receipts from the CLI.</span>](reference/cli.md){ .oa-docs-path }

[<strong>Understand a result</strong><span>Read transaction outcomes and decide what is safe to retry vs. reconcile.</span>](reference/outcomes.md){ .oa-docs-path }

[<strong>Deploy a workflow</strong><span>Choose local, on-premises, or OpenAdapt Cloud while keeping the right data boundary.</span>](how-to/deploy.md){ .oa-docs-path }

[<strong>Review security and data</strong><span>Inspect data handling, deployment boundaries, release integrity, and procurement details.</span>](security/index.md){ .oa-docs-path }

</nav>

<div class="oa-docs-more" markdown>

### Go deeper

[How the compiler works](explanation/how-it-works.md#a-program-not-a-model-in-a-loop) · [How a save is checked](explanation/verification.md) · [Receipts and signing](reference/receipts.md) · [Data handling](security/data-handling.md) · [Release integrity](security/release-integrity.md) · [Packages](reference/packages.md) · [Versions and compatibility](reference/compatibility.md) · [Validated systems and limits](explanation/limits.md)

</div>

</div>
