# Workflow Qualification Sprint

**Fixed-scope, paid qualification of one workflow. From $15,000. Ten-business-day
target once access is confirmed.**

## What it is

You bring one named workflow. We qualify the exact application, environment,
identities, effects, failure cases, and deployment boundary, and you leave with
a signed go/no-go decision backed by evidence. The sprint is a bounded
engineering assessment of whether this workflow can run safely, what it costs,
and what it returns.

The sprint qualifies **one** workflow in **one** application and **one**
environment. Additional workflows, applications, or environments are separate
sprints or scoped extensions.

## Price

- Browser and standard desktop scopes: **from $15,000**.
- Complex native, RDP, and Citrix scopes: **typically $25,000 to $40,000**,
  reflecting per-environment identity, verification, and fixture work.
- The sprint fee is due regardless of outcome. **"Do not automate" is a valid,
  full-value result**. The report gives you a defensible decision before you
  fund a production deployment.

## When the clock starts

The ten-business-day target starts on the first business day on which **all**
of the following are true, confirmed in writing:

1. The Statement of Work is signed and the invoice terms are agreed.
2. Working access to the target application and test environment is verified by
   an OpenAdapt engineer (login succeeds, the workflow's screens are reachable).
3. Representative test data is available and safe to write against.
4. The customer has named its workflow owner and security contact.

Days on which access is broken or revoked pause the clock. See the
[scope and prerequisite checklist](scope-checklist.md).

## What the customer provides

- A named business workflow with an owner who can demonstrate it.
- Application access in a test or sandboxed environment (or a
  customer-controlled production boundary with explicit written approval).
- Test data that is representative and safe to modify.
- A read path for verification: an API, database, report, or read-only session
  through which the business effect can be independently confirmed. See
  [effect verification](../concepts/effect-verification.md).
- A security contact for boundary and data-handling questions.

## Exclusions

- No production writes without explicit written authorization per workflow.
- No development of new application features, APIs, or integrations in the
  target system.
- No general process re-engineering or consulting beyond the named workflow.
- No compliance certification of any kind; see the
  [security packet](security-packet.md) for the current attestation state.
- Model-assisted repair and grounding, where used, stay within the deployment's
  configured endpoints; the sprint does not introduce uncontrolled egress.

## No-go criteria

We recommend against automation, and say so in the report, when for example:

- The business effect cannot be independently verified and the risk class does
  not allow screen-only confirmation.
- The workflow requires judgment calls that cannot be reduced to checkable
  rules, identities, and postconditions.
- The environment is too unstable for a bounded requalification policy (for
  example uncontrolled application releases with no test tenant).
- A direct API or batch interface already exists that makes GUI automation the
  wrong tool. We will tell you to use it.
- The volume and value do not clear an agreed economic threshold under
  conservative assumptions.

## Acceptance criteria

The sprint is complete when the deliverables below are handed over and walked
through with the customer. A "go" recommendation additionally requires, on the
qualified fixture set:

- All representative cases complete with the declared verification strength.
- All seeded fault cases end in a safe halt or verified reconciliation.
- **Zero silent incorrect successes**: no run reports success while the system
  of record disagrees. This target is absolute; see the
  [acceptance matrix](acceptance-matrix.md).
- Coverage gaps, exclusions, and requalification triggers are enumerated, not
  discovered later.

## Deliverables

1. **Qualification report**: the signed go/no-go decision with the full
   evidence trail. Structure in the
   [qualification report outline](qualification-report-outline.md).
2. **Coverage matrix**: which steps are identity-armed, which writes carry
   effect contracts, at what verification strength, and every gap.
3. **Go/no-go decision**: an explicit recommendation with the reasons, the
   boundary within which it holds, and what would change it.
4. **Evidence pack**: run reports (`REPORT.md` and `report.json`), fault-case
   results, hashes binding evidence to the exact bundle, and the working
   qualified prototype bundle where the decision is "go". See
   [run reports](../guides/run-reports.md).

## What happens after

- **Go**: proceed to a Supervised Production Pilot (typically $30,000 to
  $60,000) on representative production cases, then production.
- **No-go**: you keep the report, the evidence, and the analysis. Many no-go
  reports still identify a smaller automatable slice or an API path worth
  pursuing.

Start by describing the workflow at
[openadapt.ai/qualify](https://openadapt.ai/qualify). The written proposal and
agreement define the exact scope, payment schedule, and production options.
