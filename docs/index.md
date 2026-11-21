---
title: OpenAdapt documentation
description: >-
  Build a repeatable workflow from one or more demonstrations. Start with a
  checked run, connect your agent, and find the guides and reference you need.
hide:
  - toc
  - navigation
---

<div class="oa-docs-home" markdown>

<p class="oa-docs-kicker">OpenAdapt documentation</p>

# Automate the task.<br>Check the result.

<p class="oa-docs-lede">Build a workflow from one or more demonstrations, then check each save.</p>

<p class="oa-docs-intro">For browser, desktop, and remote applications. A healthy compiled run makes no AI model calls.</p>

[Try the quickstart](tutorials/quickstart.md){ .md-button .md-button--primary }

## Jump to what you need

<nav class="oa-docs-paths" aria-label="Documentation shortcuts" markdown>

[<strong>Build your first workflow</strong><span>Record the task, work with new inputs, and check the saved result.</span>](tutorials/first-workflow.md){ .oa-docs-path }

[<strong>Connect your agent</strong><span>Give an agent a compiled workflow as a single tool call.</span>](how-to/connect-an-agent.md){ .oa-docs-path }

[<strong>Find a command</strong><span>Install, record, compile, run, and inspect the evidence.</span>](reference/cli.md){ .oa-docs-path }

[<strong>Understand a result</strong><span>Read the run outcome and decide what needs review.</span>](reference/outcomes.md){ .oa-docs-path }

[<strong>Deploy a workflow</strong><span>Choose a runner and keep the right data boundary.</span>](how-to/deploy.md){ .oa-docs-path }

[<strong>Review security and data</strong><span>Find data handling, deployment boundaries, and procurement details.</span>](security/index.md){ .oa-docs-path }

</nav>

<div class="oa-docs-start" markdown>

<div class="oa-docs-start-copy" markdown>

### Run it on your computer

See a saved result and a stopped run using synthetic data. No account or API key.

</div>

<div class="oa-docs-command" markdown>

```bash
uvx --python 3.12 openadapt@latest quickstart --break-it
```

[Other install options](tutorials/quickstart.md#run-it)

</div>

</div>

## A save is more than a click

<div class="oa-docs-checks" markdown>

<div markdown>

### Check the target

Before entering data, check that the intended record is on screen.

</div>

<div markdown>

### Read the saved result

Check what persisted. An independent read uses the system of record, rather than the screen that did the work.

</div>

<div markdown>

### Stop when unsure

If a check fails or the result is uncertain, pause for review instead of claiming success.

</div>

</div>

[How a save is checked](explanation/verification.md){ .oa-docs-text-link }

<div class="oa-docs-more" markdown>

### Go deeper

[How the compiler works](explanation/how-it-works.md#a-program-not-a-model-in-a-loop) · [Data handling](security/data-handling.md) · [Release integrity](security/release-integrity.md) · [Packages](reference/packages.md) · [Versions and compatibility](reference/compatibility.md) · [Validated systems and limits](explanation/limits.md)

</div>

</div>
