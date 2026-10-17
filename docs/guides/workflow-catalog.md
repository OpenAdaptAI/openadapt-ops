# The workflow catalog and halt map

Once you are running more than one workflow, you need a portfolio view: what is
compiled, how each is doing, what it is worth, and where runs are getting stuck.
The Cloud workspace has two read-only readouts for this: the workflow catalog and
the step-level halt map.

## The catalog

The catalog is a read-only portfolio readout across every compiled workflow in
the workspace. For each entry it shows what the workflow automates, its trial
results, and the return it stands to return, so an operator or owner sees the
whole portfolio on one page without opening each workflow.

It is a readout, not a control panel. You do not edit, approve, or run a workflow
from the catalog; it links out to the workflow's own page for that.

Every entry carries its own scope. A trial result from a synthetic fixture says
so, and none of the numbers claim to be a customer-proven or publication-grade
benchmark. The catalog reports the evidence a workflow actually has, at the
strength it actually has it.

## The halt map

A halt is not a failure to hide: it is the system refusing to guess, and it tells
you exactly where the demonstration or policy needs work. The halt map is a
step-level view of where runs stop and why: which step, which check, and how
often. See [the halt-learn loop](../concepts/halt-learn-loop.md) for how a single
halt gets resolved.

Reading halts at the step level changes what you do next. Instead of "this
workflow is flaky," you get "step 7 halts on an ambiguous target on 8% of runs,"
which points at a specific fix: tighten the demonstration at that step, arm or
adjust a gate, or teach a guarded correction.

## How to read it together

The catalog answers "what do we have and what is it worth?" The halt map answers
"where is it stopping and why?" Together they turn a pile of compiled bundles into
a portfolio you can operate: see the return, find the halts, fix the steps, and
watch the halt rate move.

To read a single workflow's compiled structure behind these numbers, open its
[program graph](../concepts/program-visualizer.md).
