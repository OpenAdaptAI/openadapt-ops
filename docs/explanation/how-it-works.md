---
description: >-
  How OpenAdapt turns a demonstration into a program, what happens at each
  step of a run, and what happens when something changes.
---

# How OpenAdapt works

OpenAdapt is a compiler and a runtime for data-entry work in applications
that have no usable API. A person or an agent shows the task once or a few
times. OpenAdapt compiles what it saw into a program. The program runs the
same steps every time, checks each one, and stops when it can't confirm the
next step is safe.

```text
Record (1+ demos) -> Compile (IR) -> Certify (policy) -> Qualify (fault drills) -> Admit -> Run -> Verify & Sign
```

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 280" role="img" aria-labelledby="oa-how-title oa-how-desc">
  <title id="oa-how-title">OpenAdapt workflow lifecycle from demonstration to verified run</title>
  <desc id="oa-how-desc">One or more demonstrations compile into a workflow bundle, pass policy certification, pass qualification against normal and fault cases, receive a signed admission, and execute deterministically. Runs end VERIFIED with a signed receipt, HALTED_BEFORE_EFFECT before writing, or RECONCILIATION_REQUIRED when a write cannot be confirmed. Halts can be taught as guarded branches back into compilation.</desc>
  <defs>
    <marker id="how-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="how-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
    <marker id="how-arr-s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-stopped"/>
    </marker>
  </defs>

  <!-- Stage 1 -->
  <rect x="12" y="34" width="128" height="92" rx="10" class="oa-svg-panel"/>
  <text x="24" y="58" font-size="10" class="oa-svg-accent">DEMONSTRATE</text>
  <text x="24" y="78" font-size="13.5" class="oa-svg-title">Show task</text>
  <text x="24" y="98" font-size="11" class="oa-svg-muted">1+ recordings</text>
  <text x="24" y="114" font-size="11" class="oa-svg-muted">person or agent</text>
  <path d="M140,80 L164,80" class="oa-svg-line-accent" marker-end="url(#how-arr)"/>

  <!-- Stage 2 -->
  <rect x="170" y="34" width="118" height="92" rx="10" class="oa-svg-panel"/>
  <text x="182" y="58" font-size="10" class="oa-svg-accent">BUILD</text>
  <text x="182" y="78" font-size="13.5" class="oa-svg-title">Compile</text>
  <text x="182" y="98" font-size="11" class="oa-svg-muted">Workflow IR</text>
  <text x="182" y="114" font-size="11" class="oa-svg-muted">+ checks</text>
  <path d="M288,80 L312,80" class="oa-svg-line-accent" marker-end="url(#how-arr)"/>

  <!-- Stage 3 -->
  <rect x="318" y="34" width="126" height="92" rx="10" class="oa-svg-panel"/>
  <text x="330" y="58" font-size="10" class="oa-svg-accent">GATE 1</text>
  <text x="330" y="78" font-size="13.5" class="oa-svg-title">Certify</text>
  <text x="330" y="98" font-size="11" class="oa-svg-muted">Policy rules</text>
  <text x="330" y="114" font-size="11" class="oa-svg-muted">&amp; coverage</text>
  <path d="M444,80 L468,80" class="oa-svg-line-accent" marker-end="url(#how-arr)"/>

  <!-- Stage 4 -->
  <rect x="474" y="34" width="132" height="92" rx="10" class="oa-svg-panel"/>
  <text x="486" y="58" font-size="10" class="oa-svg-accent">GATE 2</text>
  <text x="486" y="78" font-size="13.5" class="oa-svg-title">Qualify</text>
  <text x="486" y="98" font-size="11" class="oa-svg-muted">Normal + 5</text>
  <text x="486" y="114" font-size="11" class="oa-svg-muted">planted faults</text>
  <path d="M606,80 L630,80" class="oa-svg-line-accent" marker-end="url(#how-arr)"/>

  <!-- Stage 5 -->
  <rect x="636" y="34" width="118" height="92" rx="10" class="oa-svg-panel-link"/>
  <text x="648" y="58" font-size="10" class="oa-svg-accent">EXECUTE</text>
  <text x="648" y="78" font-size="13.5" class="oa-svg-title">Admit &amp; Run</text>
  <text x="648" y="98" font-size="11" class="oa-svg-muted">0 model calls</text>
  <text x="648" y="114" font-size="11" class="oa-svg-muted">Read-back check</text>

  <!-- Branches to outcomes -->
  <path d="M754,56 L792,56" class="oa-svg-line-verified" marker-end="url(#how-arr-v)"/>
  <path d="M754,84 L772,84 L772,144 L792,144" class="oa-svg-line-stopped" marker-end="url(#how-arr-s)"/>
  <path d="M754,108 L764,108 L764,226 L792,226" class="oa-svg-line-stopped" marker-end="url(#how-arr-s)"/>

  <!-- Outcome 1: VERIFIED -->
  <rect x="798" y="20" width="170" height="68" rx="10" class="oa-svg-panel-verified"/>
  <text x="812" y="45" font-size="12" class="oa-svg-verified-txt">VERIFIED</text>
  <text x="812" y="64" font-size="11" class="oa-svg-muted">Report + signed receipt</text>

  <!-- Outcome 2: HALTED_BEFORE_EFFECT -->
  <rect x="798" y="106" width="170" height="72" rx="10" class="oa-svg-panel-stopped"/>
  <text x="812" y="131" font-size="10.5" class="oa-svg-stopped-txt">HALTED_BEFORE_EFFECT</text>
  <text x="812" y="150" font-size="11" class="oa-svg-muted">Stopped before save</text>
  <text x="812" y="165" font-size="11" class="oa-svg-muted">Nothing written</text>

  <!-- Outcome 3: RECONCILIATION_REQUIRED -->
  <rect x="798" y="192" width="170" height="72" rx="10" class="oa-svg-panel-reconcile"/>
  <text x="812" y="216" font-size="9.5" class="oa-svg-reconcile-txt">RECONCILIATION_REQUIRED</text>
  <text x="812" y="235" font-size="11" class="oa-svg-muted">Save not confirmed</text>
  <text x="812" y="250" font-size="11" class="oa-svg-muted">Person checks record</text>

  <!-- Teach loop -->
  <path d="M798,162 L229,162 L229,130" class="oa-svg-line-stopped" stroke-dasharray="5 4" marker-end="url(#how-arr-s)"/>
  <text x="415" y="182" font-size="11" class="oa-svg-muted">teach a guarded fix -> review -> re-qualify -> canary</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Lifecycle:</strong> Compilation, certification, and qualification are separate gates before production execution.</span>
  <span><a href="../verification/">How a save is checked &rarr;</a></span>
</figcaption>
</figure>

## A program, not a model in a loop

A computer-use agent decides each click by sending screenshots to a model.
OpenAdapt makes those decisions once, at compile time, from the
demonstrations. At run time it replays the compiled steps. A healthy run makes
zero model calls, so it costs nothing per step, does the same thing every
time, and sends no screens anywhere.

The compiled program is a file you can read. `openadapt flow visualize`
draws each step, how it finds its target, and which checks guard it.

## Three checks around every save

Each step that changes a record is guarded three ways:

1. **Before acting**, a right-record check confirms the screen shows the
   record the inputs name, for example the right patient.
2. **The action** itself: the click or the typing, on a target found the
   same way it was found in the demonstration.
3. **After saving**, a record check reads the saved record back through a
   different path from the screen, such as the app's API or database. The
   success message on screen doesn't count: it shows that a save happened,
   not what was stored.

If any check fails or can't tell, the run stops. When it stops before the
save, nothing was written. When the save may have gone through but couldn't
be confirmed, the run ends `RECONCILIATION_REQUIRED` and never retries on its
own; a person checks the record.

## From demonstration to production

| Stage | What it establishes |
|---|---|
| Compiled | The demonstration became a program that can be replayed. |
| Certified | The program meets a policy's rules, for example every save has a right-record check. |
| Qualified | In a test copy of the real environment, the program saved correctly on the normal case and stopped on five deliberate faults. |
| Admitted | A signed admission lets that exact program version run under the Standard or Regulated profile. |

Compiling isn't certifying, and certifying isn't qualifying. Each stage is a
separate gate, and the run report says which ones a run passed.

## When the screen changes

Each step stores several ways to find its target, strongest first: the
page or window structure where the app exposes one, then image matching, then
text found by OCR, then position relative to nearby landmarks. An optional
vision model can propose a target when all of those fail, but it's off by
default and its answer still has to pass the right-record check. See
[Surfaces](surfaces.md).

When none of them finds the target, or the right-record check fails, the run
stops and writes what it saw. Someone records the fix, `teach` adds it to the
program as a guarded branch, and the repaired program goes through review,
replay and fault campaigns, approval by a person, and a canary before it
replaces the old one. See [Handle a halt](../how-to/handle-a-halt.md).

## What a run leaves behind

Every run writes a report with each step, how its target was found, every
check and its result, and the number of model calls. A `VERIFIED` run also
writes a receipt that's safe to share. A run that OpenAdapt Cloud Execute
tracked can carry an Ed25519 countersignature (also called a Seal) on that
receipt, which anyone can check offline. See
[Files and evidence](../reference/artifacts.md).

## Where it runs

The engine runs on a computer that can open the application, inside your
network. It can run fully offline, with an optional model server on your own
network, or connected to OpenAdapt Cloud for shared workspaces and managed
browser runs. See [Deploy](../how-to/deploy.md).
