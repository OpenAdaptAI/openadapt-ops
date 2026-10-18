---
description: >-
  How OpenAdapt qualifies one of your workflows: the qualification sprint,
  what you provide, how acceptance is judged, and what you receive.
---

# Engagements

Most production work starts with a qualification sprint: a fixed-scope
assessment of one workflow, in one application and one environment, that ends
in a signed go or no-go decision backed by evidence. "Don't automate this" is
a valid result. Prices are on the [pricing page](https://openadapt.ai/pricing);
the written proposal sets the scope, timeline, and payment terms. Start at
[openadapt.ai/qualify](https://openadapt.ai/qualify).

## What you provide

**The workflow**

- One named workflow with a clear start and a clear finish.
- A person who does it today and can show it end to end.
- Rough monthly volume and minutes per run, for the cost model.
- What happens if it goes wrong: the wrong record, a duplicate, a missed
  entry. This sets how strong the record check must be.

**Access**

- Working credentials in the environment the sprint uses: a test tenant,
  sandbox, cloned virtual machine, or a production boundary you control, with
  written approval.
- For RDP or Citrix, a session an OpenAdapt engineer can reach, with the
  client, resolution, and display scaling used in production.
- VPN, MFA, jump-host, and allowlist steps done for the named engineers.
- Confirmation that automated input is allowed by the application's terms
  and your policies.

**Test data**

- Records that cover the workflow's real variety, safe to create, change, and
  delete.
- De-identified data, or a decision to run inside a boundary you control
  where real data may appear on screen. See
  [Deployment boundaries](deployment-boundaries.md).
- A way to reset test records between trials.

**A way to read the record back**, at least one of:

- an API, such as REST or FHIR, that reads what the workflow saves;
- read-only database access or a scheduled export;
- a report or file the system produces after the save;
- if none exist, a read-only second session. This is a weaker check, and a
  high-risk workflow may be a no-go without one of the others.

**People**

- The workflow owner, for the demonstration, a midpoint review, and judging
  fault results.
- A security contact and an IT contact.
- The person who will act on the decision, at the final walkthrough.

## How acceptance is judged

Each trial ends in one of four ways:

- **Verified:** the run finished and the record check confirmed the save.
- **Stopped:** the run stopped, named what it couldn't confirm, and handed
  off to a person. For a fault case, this is the correct result.
- **Reconciled:** a duplicate was found, removed by a configured undo, and
  the record check then confirmed the result.
- **Silent wrong success:** the run reported success while the record
  disagreed. The target is zero in every row. One occurrence fails
  acceptance.

The acceptance matrix uses at least three trials per row. A typical set:

| Fault | What changes | Expected result |
|---|---|---|
| None | Normal run | Verified |
| Wrong record on screen | A different record is open | Stopped before the save |
| Ambiguous target | Two plausible buttons or rows | Stopped |
| Stale target | The recorded control is gone | Stopped |
| Small layout drift | Theme, position, or label changes | Verified, with the change logged for review |
| Large layout drift | A redesign beyond what the program can find | Stopped |
| Duplicate save | The same write happens twice | Reconciled or stopped; one record remains |
| Rejected save | The write is rejected after the form is submitted | Stopped |
| Partial save | A field doesn't reach the record | Stopped |
| Record check unreachable | The API fails or a token expires | Stopped; never read as "no record" |
| Unexpected dialog | A pop-up appears mid-run | Stopped |
| Focus stolen | Another window takes focus before an action | Stopped before input |

RDP and Citrix scopes add rows for a disconnected session, a change of
window size or display scaling, stale frames, and compression artifacts.

A "go" also needs zero model calls on healthy runs, and every gap,
exclusion, and condition that would require requalification listed in the
report.

## No-go criteria

The report recommends against automating a workflow, and says why, when for
example:

- Nothing outside the screen can confirm the save, and the workflow's risk
  doesn't allow a screen-only check.
- The work needs judgment that can't be turned into checkable rules, record
  identities, and expected results.
- The application changes too often, with no test environment, for a
  bounded requalification schedule.
- An API or batch interface already does the job. The report says to use it.
- The volume and value don't clear an agreed economic threshold.

## What you receive

1. **A qualification report** with the signed decision:
    - what was tested: the bundle digest, application and environment, and
      engine version;
    - the decision, its reasons, and what would change it;
    - the workflow's steps, which ones are protected by a right-record check,
      and which saves have record checks, at what strength;
    - normal-run and fault-case results;
    - the deployment analysis and the cost model.
2. **The evidence:** run reports, fault results, and hashes that tie them to
   the exact bundle.
3. **The bundle**, when the decision is go.

When no exceptions are found, a production admission for that bundle can
follow; see
[Certify and qualify a workflow](../how-to/certify-and-qualify.md#admission).

## What a sprint excludes

- Saves to production without written authorization for that workflow.
- New features or integrations in your application.
- Any compliance certification. See [Security and procurement](index.md).
