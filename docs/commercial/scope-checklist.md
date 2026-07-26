# Scope and prerequisite checklist

What the customer must provide before a
[Qualification Sprint](qualification-sprint.md) can start. The sprint clock
does not start until every required item is confirmed. Sending this list with
the proposal avoids the most common cause of stalled engagements: access that
arrives three weeks after signature.

## 1. The workflow

- [ ] One named workflow with a clear start state and a clear finished state.
- [ ] A workflow owner who performs it today and can demonstrate it end to end.
- [ ] Approximate monthly volume and minutes per manual execution (feeds the
      [ROI worksheet](roi-calculator.md)).
- [ ] The consequence of doing it wrong (wrong record, duplicate, missed
      entry), stated plainly. This drives the risk class and verification
      strength.

## 2. Application access

- [ ] Working credentials for the target application, in the environment the
      sprint will use.
- [ ] The environment named explicitly: test tenant, sandbox, cloned VM, or a
      customer-controlled production boundary with written approval.
- [ ] For RDP or Citrix scopes: a session an OpenAdapt engineer can reach, with
      the client, codec, resolution, and DPI representative of production. See
      the [external Citrix brief](citrix-external-brief.md).
- [ ] Any VPN, MFA, jump-host, or allowlisting steps completed for the named
      engineers.
- [ ] Confirmation that automated input against this environment is permitted
      by the application's terms and the customer's policies.

## 3. Test data

- [ ] Representative records that exercise the workflow's real variety
      (not only the happy path).
- [ ] Data that is safe to create, modify, and delete during trials.
- [ ] Either de-identified data, or an explicit decision that the sprint runs
      inside a customer-controlled boundary where real data may appear on
      screen (see [deployment boundaries](deployment-boundaries.md)).
- [ ] A way to reset or clean up test records between trials.

## 4. Verifier read path

Effect verification reads the system of record instead of trusting the screen
([how it works](../concepts/effect-verification.md)). Provide at least one:

- [ ] API access (REST, FHIR, or similar) that can read the records the
      workflow writes.
- [ ] Read-only database access or a scheduled export covering those records.
- [ ] A report or file the system produces that reflects the write.
- [ ] If none exist: a read-only second session for on-screen read-back, and
      acknowledgment that this is a weaker, same-surface check. High-risk
      workflows may be no-go without an independent read path.

## 5. People and security

- [ ] Workflow owner: available for the demonstration, midpoint review, and
      fault-case adjudication (roughly 4 to 8 hours across the sprint).
- [ ] Security contact: for data-boundary questions and access approvals.
- [ ] IT contact: for environment, VPN, and credential logistics.
- [ ] Any security review the customer requires of OpenAdapt started early;
      the [security packet](security-packet.md) and
      [security review guide](../guides/security-review.md) answer most
      questionnaires.

## 6. Decision authority

- [ ] The person who will act on the go/no-go recommendation is identified and
      attends the final walkthrough.
- [ ] Budget path for the next step (pilot, production) is understood, so a
      "go" does not stall for a quarter.
