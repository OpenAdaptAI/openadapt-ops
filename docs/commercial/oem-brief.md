# OEM architecture and commercial brief

For software vendors and platforms that want to embed verified GUI execution
in their own product: an RCM platform that must write into customer EMRs, a
vertical SaaS that must reach a legacy system with no API, an agent platform
that needs a governed actuator.

## The idea: a transaction API over GUI execution

Most embedding integrations expose "run this script and hope." OpenAdapt's OEM
surface is designed as a **transaction API**: your product submits an intent,
and gets back a terminal outcome it can build product logic on.

```text
submit(workflow, inputs, profile)
    -> VERIFIED              # business effect confirmed in the system of record
    -> COMPLETED_UNVERIFIED  # finished, but no independent confirmation; never
                             # treated as success under standard or regulated profiles
    -> HALTED                # a gate refused; durable, with the violated expectation named
    -> FAILED                # aborted with no write
    -> ROLLED_BACK           # a refuted effect was reconciled by compensation
```

Each outcome carries the evidence behind it: run report, identity coverage,
effect verdicts, and hashes binding the evidence to the exact bundle and
inputs. Your product does not parse screenshots to guess what happened; it
branches on a verdict.

**Status: this reference API is in design.** The underlying mechanics
(governed run admission, terminal outcomes, effect verification, evidence
binding) ship in the engine today; the stable embedding surface, versioned
schemas, and external-executor adapter are being specified. OEM engagements at
this stage are design-partner engagements and shape that surface.

## Integration surface

- **Submission:** your control plane submits a qualified, sealed workflow
  bundle plus typed inputs. Admission is fail-closed: an uncertified bundle,
  missing coverage, or unsatisfied profile requirement is refused before
  actuation, not discovered after.
- **Execution profiles:** `demo`, `standard`, and `regulated` profiles compile
  into explicit requirements (certification, sealed bundles, consequential
  identity and effect coverage, egress policy). Your product selects a
  profile, not a bag of flags.
- **Runners:** execution lands on a runner in the right boundary: your cloud,
  your customer's environment, or a managed browser runner for non-regulated
  web targets ([deployment boundaries](deployment-boundaries.md)). Runners
  advertise capabilities; a plan a runner cannot satisfy is rejected before
  actuation.
- **Evidence:** every run returns machine-readable evidence
  ([report schema](../guides/run-reports.md)) suitable for your own audit
  trail and your customers' reviewers.
- **External executors:** the adapter contract
  (`authorize -> invoke -> observe -> verify -> VERIFIED | HALTED + evidence`)
  is designed so identity, authorization, verification, and evidence stay
  authoritative even when another tool (a script, an RPA bot, an API call, an
  agent) performs the action.

## Responsibility boundaries

| Responsibility | OpenAdapt | OEM partner |
|---|---|---|
| Engine, safety gates, report schema | R | uses |
| Qualification tooling and evidence format | R | runs or resells |
| Workflow qualification per customer environment | C (or delivered as a service) | R |
| End-customer relationship, UX, and support | | R |
| Deployment boundary and data handling per end customer | C | R |
| Verifier read paths in end-customer systems | C | R |
| Claims made to end customers about coverage | must match the evidence | R |

The last row is contractual on purpose: bounded evidence stays bounded, in
your marketing as in ours.

## Commercial shape

- **OEM programs: typically $75,000 to $150,000 annually, plus scoped
  integration work**, matching the public
  [pricing page](https://openadapt.ai/pricing).
- Scope covers the embedding license, the integration surface, named
  environments, and support; per-end-customer workflow qualification is scoped
  separately or delivered by the partner using the qualification tooling.
- Early OEM partners operate under a
  [design-partner structure](legal-outlines.md): defined feedback obligations,
  early access to the reference API, and input into its shape.
- The engine is MIT-licensed and auditable; embedding does not depend on a
  proprietary black box for its safety story.

## Where to start

An OEM conversation starts the same way every OpenAdapt engagement does: with
one real workflow. A [Qualification Sprint](qualification-sprint.md) against
one of your end-customer environments produces the evidence that the
integration is worth building, before either side commits to platform work.
