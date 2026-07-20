# Policy and certify

Compiled is not certified safe. A runnable bundle can still have gaps: a write
with no identity check, a step that asserts nothing. Policy and certify separate
"runnable" from "certified safe", and fail closed.

## Two commands, two jobs

```mermaid
flowchart LR
    B{{Bundle}} --> L[[lint]]
    B --> C[[certify]]
    L --> LR[Report gaps<br/>with a severity each<br/>advice, exit by severity]
    C --> CR{Policy satisfied?}
    CR -->|yes| PASS([exit 0, deploy])
    CR -->|no| FAIL([exit nonzero, REFUSED])
```

- **`lint`** reports a bundle's coverage gaps: clicks that act with no identity
  check, steps that assert nothing, writes left under-classified. Each finding
  carries a severity. It exits nonzero once a finding reaches `error` (an
  unarmed or vacuous *irreversible* step); `--strict` also fails on warnings.
  `lint` is advice.
- **`certify`** enforces a policy and **refuses** the bundle (exits nonzero)
  when it fails. It is the gate: put it in CI or a deploy step and an unsafe
  bundle never ships.

```bash
openadapt flow lint    bundle
openadapt flow certify bundle --policy clinical-write
```

## What a policy asserts

A policy is a YAML document of requirements. Two ship: a permissive default and
a strict `clinical-write`. The strict policy asserts, for example:

- no unarmed clicks,
- identity required on every write and every entity-navigation step,
- effect verification required on every write.

`certify` evaluates the bundle against the policy and reports each violated
requirement before deploy.

## Risk is auto-classified, then enforceable

At compile time, write-shaped clicks (create, update, delete, submit, save,
confirm, add, and siblings, matched on word boundaries) are auto-classified
`irreversible`. That arms the low-confidence refusal by default for
consequential writes, not only when a human marks the step. A `risk_overrides`
map wins either direction.

!!! warning "The classifier is a heuristic, not understanding"
    Risk classification reads the label and the intent, never the app's true
    effect. It is deliberately biased toward irreversible (a false irreversible
    costs availability; a false reversible costs safety), but it misses writes
    with non-write labels (an icon-only "commit", a bare "OK" that saves) and
    writes committed by a submitting ++enter++ key. It also over-flags benign
    write words ("Apply filter", "Add to favourites"). A write behind a
    non-write label stays reachable with a green report unless a human adds
    `risk_overrides`. That is why `certify` with a strict policy is the gate that
    refuses a bundle whose gaps stay open.

## Fail-closed, everywhere

Policy and certify are the compile-time and pre-deploy face of the runtime's
posture: [halt rather than guess](identity-gate.md),
[refuse rather than accept an unverifiable write](effect-verification.md),
[quarantine rather than emit an ambiguous program](multi-trace-induction.md).
The gate turns disclosure into enforcement: the residual gaps OpenAdapt is
honest about become a policy that refuses the bundle until they are closed.

This is a compile-time and pre-deploy layer only; the replayer, identity ladder,
and healer are unchanged. See
[Write and enforce a policy](../guides/policy-and-certification.md) for a worked
example.
