# Commercial offers

This section explains how to [qualify](../reference/glossary.md#qualify) and deploy one workflow. If you're
deciding whether OpenAdapt fits a workflow at all, start with
[Evaluate](../evaluate/index.md).

## Software

The public [pricing page](https://openadapt.ai/pricing) is the source for
software prices. This table restates it.

| Plan | Price | What it includes |
|---|---|---|
| Local | $0 (MIT) | The engine on your machine. Record, compile, and replay. No account. |
| Hosted | $29/month | We run the machine for approved browser workflows on non-regulated data: a managed runner, a dashboard and run history, an API key and verify URL, and agent access. |
| Enterprise | Talk to us | One app and one environment, qualified, with identity and effect checks; a customer-controlled or dedicated runner; a BAA and a private verify URL; and Citrix, VDI, volume, and SLA terms. |

Hosted isn't a lane for PHI or PII. Workflows that touch regulated data run on
a machine you control. See [Deployment boundaries](deployment-boundaries.md).

## Services

We scope implementation and ongoing maintenance per workflow, separately from
software hosting. A written proposal sets the deliverables, responsibilities,
acceptance criteria, and fees before the build starts.
[How a first project works](../evaluate/first-project.md) walks through the
steps.

| Offer | Typical range | What it is |
|---|---|---|
| [Workflow Qualification Sprint](qualification-sprint.md) | From $15,000 (native, RDP, and Citrix scopes typically $25,000 to $40,000) | Fixed-scope paid qualification of one workflow, ending in a signed go/no-go report. |
| Supervised Production Pilot | Typically $30,000 to $60,000 | Prove the qualified workflow on representative production cases and leave with an acceptance report. |
| Production | Typically $48,000 to $120,000/year | Annual scope covering the qualified workflow family, environment, runners, evidence, support, and requalification. |
| OEM / embedding | Typically $75,000 to $150,000/year plus scoped integration | Embed verified execution in another product. See the [OpenAdapt Execute private-pilot guide](oem-brief.md). |

These ranges are typical, not quotes. Your proposal sets the fee for your
workflow.

The Workflow Qualification Sprint comes first. A successful qualification can
move to a supervised pilot and then to production. The sprint remains paid when
the evidence supports a "do not automate" decision.

## Buyer and evaluation resources

| Document | What it covers |
|---|---|
| [Workflow Qualification Sprint](qualification-sprint.md) | The entry offer: price, clock, deliverables, and acceptance criteria. |
| [Scope and prerequisite checklist](scope-checklist.md) | What you provide before the sprint clock starts. |
| [Qualification report outline](qualification-report-outline.md) | The structure of the report you receive. |
| [Acceptance matrix template](acceptance-matrix.md) | The pass/fail contract, agreed before any trial runs. |
| [Security packet](security-packet.md) | The posture summary a security or IT review asks for. |
| [Deployment boundaries](deployment-boundaries.md) | Where execution runs and where sensitive data lives. |
| [External Citrix zero-install brief](citrix-external-brief.md) | A workflow that lives behind Citrix or VDI. |
| [OpenAdapt Execute private-pilot guide](oem-brief.md) | A vendor that wants to embed verified execution. The API is available to approved private-pilot partners with scoped credentials. |
| [Invoke a program: Seal or halt](execute-api.md) | The Execute request, poll, Seal-shaped receipt, and webhook contract. |
| [Procurement FAQ](procurement-faq.md) | Procurement, legal, and vendor-risk questions. |

## How claims are bounded

These documents follow the same rules as the public site:

- No claimed certifications. SOC 2 status is stated plainly in the
  [security packet](security-packet.md).
- Bounded evidence stays bounded. Qualification evidence for one workflow,
  application, and environment is never presented as a general support claim.
- Commercial terms are established in a customer-specific written proposal and
  agreement, not in public templates.
