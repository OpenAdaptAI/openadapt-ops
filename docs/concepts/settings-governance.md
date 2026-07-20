# Settings and policy governance

Not every setting carries the same weight. A dashboard's default sort order is a
personal preference. A workflow's certification policy is a safety-critical
control. Treating them the same is how a safety control gets flipped by someone
who only meant to change a preference. The Cloud workspace separates
configuration into three tiers, and governs each one according to what it can
break.

## Three tiers

- **User preferences.** Per-person settings that change one operator's own
  experience and nothing else: default views, notification choices, display
  options. A user owns these outright.
- **Organization policy.** Workspace-wide settings that shape how the whole team
  operates: defaults, roles, and the guardrails that apply across workflows.
  Changing these is an administrator action, not a personal one.
- **Safety-critical configuration.** The controls that decide whether a run is
  allowed to act: certification policy, identity requirements, effect
  verification, egress boundaries, and the halt conditions behind them. These
  are governed, not merely set.

The tiers are ordered by blast radius. A user preference affects one person. An
organization policy affects the team. A safety-critical control affects whether
a workflow can write to a real system of record, so it gets the strongest
handling.

## Governed and audited

A change to a governed setting is a recorded event, not a silent flip. The
workspace keeps who changed what, from which value to which value, and when, so a
safety-relevant change is always attributable after the fact. Preferences do not
need this weight; safety-critical controls do, and the audit trail is where the
difference shows.

## Fail-closed

Governed configuration is fail-closed. When a required safety-critical setting is
missing, unreadable, or ambiguous, the workspace does not fall back to a
permissive default and proceed. It refuses. The same posture runs through the
rest of the product: a run that cannot establish its declared checks
[halts rather than guessing](regulated-execution.md), and configuration that
cannot be resolved safely blocks rather than quietly loosening a control.

This is why the tiers matter. Making a preference easy to change and a safety
control hard to change, with every governed change audited and every missing one
refused, is what keeps a convenience edit from becoming a safety incident.
