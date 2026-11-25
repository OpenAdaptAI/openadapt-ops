---
description: >-
  What to do when a run stops: read why, decide the paused item, teach the
  program the fix, and promote the repaired program safely.
---

# Handle a halt

A run stops whenever it can't confirm the next step is safe: the screen
changed, the wrong record is open, two records match, or the record check
didn't find the save. Stopping is the designed behavior. This page covers
what happens next.

## 1. Find out why it stopped

```bash
openadapt flow explain runs/<run-dir>
```

`explain` names the step, the check that failed, and the next command to
run. The same detail is in `REPORT.md` in the run directory. A run that
stopped before a save wrote nothing.

If the outcome is `RECONCILIATION_REQUIRED`, a save may have gone through.
Have a person check the record in the application before anything else. No
command retries that save automatically.

## 2. Decide the paused item

A durable run pauses at the halt. Someone decides what happens to that item:

```bash
openadapt flow approve runs/<run-dir> --approver "jane@clinic.example"
openadapt flow resume runs/<run-dir> --require-approval
```

`approve` records who decided and which option they chose (`--resolution`).
`resume` checks the live screen, the record, and the target again before it
continues, and never repeats a confirmed save. In OpenAdapt Desktop and on a
phone, the same pause offers only the actions that fit that halt, such as
resume, skip, reject, teach, escalate, or reconcile. See
[Answer a halt from a phone](answer-from-a-phone.md).

## 3. Teach the program the fix

When the same halt will recur, for example a new dialog that must be
dismissed, record only the corrective steps and teach them to the program:

```bash
openadapt flow record --url https://staging.your-app.example --out fix
openadapt flow teach runs/<run-dir> --fix fix --bundle bundle --out bundle-v2
```

`teach` turns the fix into a guarded branch for that halt. It replays the
original evidence to check that the fix doesn't weaken any check, and writes
`bundle-v2` only when the fix passes. A rejected fix is quarantined and the
program keeps stopping at that point.

When the right fix depends on the situation, teach a branch from two or more
halted runs and their fixes:

```bash
openadapt flow teach-branch \
  --example runs/halt-1 fix-1 --example runs/halt-2 fix-2 \
  --normal-run runs/ok-1 --bundle bundle --out bundle-v2
```

## 4. Let a calling agent help

When an agent calls the workflow through the MCP server and the run stops,
the result carries `needs_repair` with the step and a one-time repair token.
If an administrator turned on screen access for repairs
(`openadapt agent repair access`, then `serve --repair-access FILE`), the
agent can look at the stopped screen and demonstrate the fix with
`get_repair_screen` and `teach_repair`. `--hold-on-halt` keeps the stopped
browser page open for that, 300 seconds by default.

The agent's fix becomes a candidate like any other. The agent can't review
or approve its own candidate.

## 5. Promote the repaired program

A repaired bundle never replaces the running one just because it exists.
It goes through a fixed sequence, and no step can be skipped:

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 265" role="img" aria-labelledby="oa-rep-title oa-rep-desc">
  <title id="oa-rep-title">Governed repair promotion pipeline</title>
  <desc id="oa-rep-desc">A candidate repair moves strictly through human diff review, replay campaign, fault campaign, human approval, hash-pinned staging, canary verification, and active status. Any canary regression reverts to staged, and active rollback restores the prior version.</desc>
  <defs>
    <marker id="rep-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="rep-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
    <marker id="rep-arr-w" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-warn"/>
    </marker>
  </defs>

  <!-- Row 1: Candidate -> Review -> Replay -> Fault -->
  <g class="oa-svg-node">
    <rect x="14" y="20" width="206" height="66" rx="10" class="oa-svg-panel"/>
    <text x="28" y="42" font-size="9.5" class="oa-svg-accent">01 · REGISTER</text>
    <text x="28" y="61" font-size="13" class="oa-svg-title">Candidate bundle</text>
    <text x="28" y="76" font-size="10" class="oa-svg-muted">Weakened checks refused</text>
  </g>
  <path d="M220,53 L262,53" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#rep-arr)"/>

  <g class="oa-svg-node">
    <rect x="268" y="20" width="206" height="66" rx="10" class="oa-svg-panel-warn"/>
    <circle cx="458" cy="34" r="3.5" class="oa-svg-gate-dot oa-svg-dot-warn"/>
    <text x="282" y="42" font-size="9.5" class="oa-svg-warn-txt">02 · HUMAN GATE</text>
    <text x="282" y="61" font-size="13" class="oa-svg-title">Diff reviewed</text>
    <text x="282" y="76" font-size="10" class="oa-svg-muted">Person inspects repair</text>
  </g>
  <path d="M474,53 L516,53" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#rep-arr)"/>

  <g class="oa-svg-node">
    <rect x="522" y="20" width="206" height="66" rx="10" class="oa-svg-panel"/>
    <text x="536" y="42" font-size="9.5" class="oa-svg-accent">03 · REPLAY</text>
    <text x="536" y="61" font-size="13" class="oa-svg-title">Replay campaign</text>
    <text x="536" y="76" font-size="10" class="oa-svg-muted">Prior evidence passes</text>
  </g>
  <path d="M728,53 L770,53" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#rep-arr)"/>

  <g class="oa-svg-node">
    <rect x="776" y="20" width="190" height="66" rx="10" class="oa-svg-panel"/>
    <text x="790" y="42" font-size="9.5" class="oa-svg-accent">04 · ADVERSARIAL</text>
    <text x="790" y="61" font-size="13" class="oa-svg-title">Fault campaign</text>
    <text x="790" y="76" font-size="10" class="oa-svg-muted">Every fault must halt</text>
  </g>

  <!-- Connector from Row 1 end down to Row 2 start -->
  <path d="M871,86 L871,108 L117,108 L117,128" class="oa-svg-line-accent oa-svg-flow-slow" marker-end="url(#rep-arr)"/>

  <!-- Row 2: Approved -> Staged -> Canary -> Active -->
  <g class="oa-svg-node">
    <rect x="14" y="134" width="206" height="66" rx="10" class="oa-svg-panel-warn"/>
    <circle cx="204" cy="148" r="3.5" class="oa-svg-gate-dot oa-svg-dot-warn"/>
    <text x="28" y="156" font-size="9.5" class="oa-svg-warn-txt">05 · HUMAN GATE</text>
    <text x="28" y="175" font-size="13" class="oa-svg-title">Approved by person</text>
    <text x="28" y="190" font-size="10" class="oa-svg-muted">Models never approve</text>
  </g>
  <path d="M220,167 L262,167" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#rep-arr)"/>

  <g class="oa-svg-node">
    <rect x="268" y="134" width="206" height="66" rx="10" class="oa-svg-panel"/>
    <text x="282" y="156" font-size="9.5" class="oa-svg-accent">06 · STAGE</text>
    <text x="282" y="175" font-size="13" class="oa-svg-title">Staged by hash</text>
    <text x="282" y="190" font-size="10" class="oa-svg-muted">Immutable bundle digest</text>
  </g>
  <path d="M474,167 L516,167" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#rep-arr)"/>

  <g class="oa-svg-node">
    <rect x="522" y="134" width="206" height="66" rx="10" class="oa-svg-panel-link"/>
    <text x="536" y="156" font-size="9.5" class="oa-svg-accent">07 · CANARY</text>
    <text x="536" y="175" font-size="13" class="oa-svg-title">Canary runs</text>
    <text x="536" y="190" font-size="10" class="oa-svg-muted">First runs checked</text>
  </g>
  <path d="M728,167 L770,167" class="oa-svg-line-verified oa-svg-flow" marker-end="url(#rep-arr-v)"/>

  <g class="oa-svg-node">
    <rect x="776" y="134" width="190" height="66" rx="10" class="oa-svg-panel-verified"/>
    <circle cx="950" cy="148" r="3.5" class="oa-svg-gate-dot oa-svg-dot-verified"/>
    <text x="790" y="156" font-size="9.5" class="oa-svg-verified-txt">08 · PROMOTED</text>
    <text x="790" y="175" font-size="13" class="oa-svg-title">Active bundle</text>
    <text x="790" y="190" font-size="10" class="oa-svg-muted">Serving production</text>
  </g>

  <!-- Regression & Rollback return paths -->
  <path d="M625,200 C625,232 371,232 371,204" class="oa-svg-line-warn" stroke-dasharray="4 4" marker-end="url(#rep-arr-w)"/>
  <text x="498" y="236" text-anchor="middle" font-size="9.5" class="oa-svg-warn-txt">canary regression &rarr; auto-revert to prior bundle</text>

  <path d="M871,200 C871,252 371,252 371,204" class="oa-svg-line-warn" stroke-dasharray="4 4" marker-end="url(#rep-arr-w)"/>
  <text x="750" y="256" text-anchor="middle" font-size="9.5" class="oa-svg-warn-txt">rollback &rarr; prior version restored</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Governed promotion:</strong> No step can be skipped, and models never review, approve, or promote a repair.</span>
  <span><a href="../../explanation/verification/">How checks work &rarr;</a></span>
</figcaption>
</figure>

```bash
openadapt flow repair register bundle-v2 --prior bundle --source teach --evidence runs/<run-dir>
openadapt flow repair review <id> --reviewed-by "jane@clinic.example"
openadapt flow repair campaign <id> --kind replay
openadapt flow repair campaign <id> --kind fault
openadapt flow repair approve <id> --approved-by "jane@clinic.example"
openadapt flow repair stage <id>
openadapt flow repair canary <id> --max-runs 5
openadapt flow repair canary-record <id> --run-dir runs/<canary-run>
openadapt flow repair rollback
```

`register` refuses a candidate that weakens any check. The fault campaign
must refuse every adversarial case: ambiguity, wrong record, stale target,
an unexpected dialog, and a failed record check. During the canary, any wrong
success or failed check switches back to the prior bundle automatically.
Models never approve or promote a repair.
