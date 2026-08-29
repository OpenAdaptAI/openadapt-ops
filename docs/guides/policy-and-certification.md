# Write and enforce a policy

`lint` tells you where a bundle is thin. `certify` refuses a bundle that
violates a policy. Together they make "runnable" distinct from "certified safe."
For the model behind it, see [Policy and certify](../concepts/policy-and-certify.md).

## Lint first

```bash
openadapt flow lint bundle
```

`lint` reports coverage gaps, each with a severity: clicks that act with no
identity check, steps that assert nothing, writes left under-classified. It exits
nonzero once a finding reaches `error` (an unarmed or vacuous *irreversible*
step). Add `--strict` to also fail on warnings:

```bash
openadapt flow lint bundle --strict
```

Use `lint` while authoring, to decide what to fix.

## Certify to gate a deploy

`certify` enforces a policy and exits nonzero when the bundle fails, so it can be
a CI or deploy gate:

```bash
openadapt flow certify bundle --policy clinical-write
```

`--policy` takes a YAML path or a built-in name (`permissive`, `clinical-write`).
A failing certification prints each violated requirement and exits nonzero, so an
unsafe bundle never ships.

## Two shipped policies

- **`permissive`**: a lenient default for low-stakes, reversible workflows.
- **`clinical-write`**: a strict policy for consequential writes. It requires,
  for example, no unarmed clicks, identity on every write and entity-navigation
  step, and effect verification on every write.

Point `--policy` at your own YAML to encode your organization's requirements.

## Fix the gaps certify finds

Common findings and how to close them:

| Finding | Fix |
|---|---|
| A write step is not marked irreversible | Add a `risk_overrides` entry; the auto-classifier reads labels only and misses non-write labels and ++enter++-submitted writes |
| A consequential click is unarmed (no identity) | The target's row has no discriminating text; restructure the click or accept the disclosed gap for a reversible step |
| A write asserts nothing verifiable | Declare an [effect](../concepts/effect-verification.md) and configure a verifier |
| An ambiguous step | Resolve it with [`disambiguate`](../concepts/multi-trace-induction.md) |

## Put it in CI

A minimal gate that refuses an uncertified bundle on every change:

```bash
openadapt flow lint    bundle --strict
openadapt flow certify bundle --policy clinical-write
```

Both exit nonzero on failure, so a standard CI step fails the build. Gaps
that `lint` only reports become requirements `certify` enforces.
