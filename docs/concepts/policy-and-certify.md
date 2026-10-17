# Policy and certify

Compiled is not the same as certified safe. A runnable bundle can still have
gaps: a write with no identity check, a step that asserts nothing. `lint`
reports those gaps. `certify` enforces a policy and exits nonzero, refusing
the bundle before it deploys, when it fails.

## lint and certify

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
  when it fails. Put it in CI or a deploy step so an unsafe bundle never ships.

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

## Risk classification

At compile time, write-shaped clicks (create, update, delete, submit, save,
confirm, add, and siblings, matched on word boundaries) are auto-classified
`irreversible`. That arms the low-confidence refusal by default for
consequential writes, not only when a human marks the step. A `risk_overrides`
map wins either direction.

!!! warning "The classifier reads labels, not the app's effect"
    Risk classification reads the label and the intent, never the app's true
    effect. It is biased toward irreversible (a false irreversible costs
    availability; a false reversible costs safety), but it misses writes with
    non-write labels (an icon-only "commit", a bare "OK" that saves) and writes
    committed by a submitting ++enter++ key. It also over-flags benign write
    words ("Apply filter", "Add to favourites"). A write behind a non-write
    label stays reachable with a green report unless a human adds
    `risk_overrides`. That is why `certify` with a strict policy refuses a
    bundle whose gaps stay open.

Policy and certify run at compile time and before deploy. They don't change
the replayer, identity ladder, or healer. See
[Write and enforce a policy](../guides/policy-and-certification.md) for a
worked example. At runtime, [`run`](regulated-execution.md) applies the same
kind of gate: [identity](identity-gate.md) stops an unresolvable target,
[effect verification](effect-verification.md) stops an unverifiable write, and
[induction](multi-trace-induction.md) withholds an ambiguous program.
