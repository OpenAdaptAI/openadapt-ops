# OpenAdapt Execute: OEM architecture and commercial brief

For software vendors and service providers that need to complete authorized
transactions in customer systems they cannot integrate with: an RCM platform
that must write into customer EMRs, a vertical SaaS that must reach a legacy
system with no API, or an agent platform that needs a governed actuator.

**OpenAdapt Execute** is the approved product direction for this work. It uses
the MIT-licensed OpenAdapt Flow runtime in the customer-controlled execution
boundary. The managed API, compatibility packs, production verifier recipes,
and qualification intelligence are commercial services. The external API is
not yet a public endpoint.

## The idea: a transaction API over GUI execution

Most embedding integrations expose "run this script and hope." OpenAdapt's OEM
surface is designed as a **transaction API**: your product submits an intent,
and gets back a terminal outcome it can build product logic on.

```text
submit(qualified_workflow, inputs, idempotency_key, profile)
    -> accepted(execution_id)

event / poll result
    -> VERIFIED                  # business effect confirmed in the system of record
    -> COMPLETED_UNVERIFIED      # demo-only completion; never production success
    -> HALTED                    # a gate stopped the run with evidence
    -> FAILED                    # a platform failure with no possible effect
    -> RECONCILIATION_REQUIRED   # delivery or persistence is uncertain; do not retry
```

The API will be asynchronous because a transaction can wait for a person,
survive a restart, or need reconciliation. Each result carries the evidence
behind it: run report, identity coverage, effect verdicts, and hashes binding
the evidence to the exact bundle and inputs. Your product does not parse
screenshots to guess what happened; it branches on a verdict.

**Status: the public API contract is in design.** The underlying mechanics ship
in Flow 1.26: governed run admission, signed attended decisions, durable
resume, one-use managed authority, exact bundle/input binding, effect
verification, and evidence binding. OpenAdapt is specifying the stable
embedding surface, versioned schemas, webhooks, and SDKs with early OEM users.

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
- **Authority:** a managed dispatch binds one use to the exact run, qualified
  bundle digest, runtime-input digest, and governed authorization. A runner
  validates the envelope locally before it can actuate. The control plane can
  request work; it cannot widen local policy or mint a substitute authority.
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
  customer-specific design-partner agreement: defined feedback obligations,
  early access to the reference API, and input into its shape.
- The engine is MIT-licensed and auditable; embedding does not depend on a
  proprietary black box for its safety story.

## Where to start

An OEM conversation starts the same way every OpenAdapt engagement does: with
one real workflow. A [Qualification Sprint](qualification-sprint.md) against
one of your end-customer environments produces the evidence that the
integration is worth building, before either side commits to platform work.
