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

<nav class="oa-docs-paths" aria-label="Documentation shortcuts">

<a class="oa-docs-path" href="tutorials/first-workflow/">
<strong>Build your first workflow</strong>
<span>Record the task, work with new inputs, and check the saved result.</span>
</a>

<a class="oa-docs-path" href="how-to/connect-an-agent/">
<strong>Connect your agent</strong>
<span>Give an agent a compiled workflow as a single tool call.</span>
</a>

<a class="oa-docs-path" href="reference/cli/">
<strong>Find a command</strong>
<span>Install, record, compile, run, and inspect the evidence.</span>
</a>

<a class="oa-docs-path" href="reference/outcomes/">
<strong>Understand a result</strong>
<span>Read the run outcome and decide what needs review.</span>
</a>

<a class="oa-docs-path" href="how-to/deploy/">
<strong>Deploy a workflow</strong>
<span>Choose a runner and keep the right data boundary.</span>
</a>

<a class="oa-docs-path" href="security/">
<strong>Review security and data</strong>
<span>Find data handling, deployment boundaries, and procurement details.</span>
</a>

</nav>

<div class="oa-docs-start" markdown>

<div class="oa-docs-start-copy" markdown>

### Run it on your computer

See a saved result and a stopped run using synthetic data. No account or API key.

</div>

<div class="oa-docs-command" markdown>

```bash
uvx --python 3.12 openadapt quickstart --break-it
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
