# The program visualizer

A compiled bundle is a program, not a recording. Before you trust it in a
deployment, read it: what steps it takes, how it finds each target, where it
refuses, where it can stop. The visualizer renders that graph from the bundle
itself, so what you review is the artifact that actually runs.

## What the graph shows

For each step the visualizer surfaces the parts that decide whether a run is safe:

- **Steps, in order.** The action at each step and the target it acts on.
- **The resolution ladder.** The ordered rungs a step tries to re-find its
  target at replay time (structural element match, template, OCR, landmark
  geometry, and optionally a grounding model). The ladder shows how much drift a
  step can absorb before it halts. See
  [the capability ladder](capability-ladder.md).
- **Armed identity gates.** Which steps re-verify identity before acting, and
  which do not. An unarmed step has no identity check at all, and the graph
  shows that rather than leaving it implied. See
  [the identity gate](identity-gate.md).
- **Effect checks.** Which writes carry a typed effect verified against the
  system of record. See [effect verification](effect-verification.md).
- **Halt points.** Every place the run may stop: a low-confidence match on an
  irreversible step, a failed postcondition, a refuted write, an ambiguous
  target. This is the run's stop map.

For a program bundle it also shows the structure the linear case hides: loops
and their bounds, guarded transitions, and exception paths.

## One graph, three renderings

The CLI reads the bundle and emits one of three formats from the same
[graph spec](../reference/bundle-format.md):

```bash
openadapt flow visualize bundle -o graph.html     # self-contained page
openadapt flow visualize bundle --format mermaid  # flowchart source
openadapt flow visualize bundle --format json      # the shared graph spec
```

- **HTML** is a self-contained page you can open offline and hand to a reviewer.
- **Mermaid** is flowchart source you can paste into a Markdown file or design
  doc.
- **JSON** is the shared program-graph spec. The Cloud and desktop surfaces
  render the same spec, so a reviewer in Cloud and an engineer at the CLI see
  the same graph.

## Reading is safe

`visualize` never runs the workflow. It reads the bundle and describes it with
no side effects, so you can point it at any bundle, including one that would
refuse to certify. That is the intended order: visualize the program,
[lint](policy-and-certify.md) its coverage gaps, certify it against a policy,
then run it.

## In Cloud

The same graph appears in the Cloud workspace on a workflow's page, so a
reviewer who never touches the CLI can read the compiled program, its gates, and
its halt points before approving a version for deployment.
