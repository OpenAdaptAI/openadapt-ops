---
description: >-
  Define a finite, authorized human policy choice in a qualified OpenAdapt
  workflow. Keep it separate from an operational halt and verify all later
  actions.
---

# Typed business decisions

A typed business decision is a finite human policy choice inside a qualified
workflow. It preserves human authority when a workflow cannot derive one
business choice from the available facts.

For example, a request can meet both a standard route and an approved exception
route. The workflow can ask an authorized person which approved route applies.
It does not ask a model to invent a policy. It does not use an answer as proof
that a later write succeeded.

## Two different human paths

OpenAdapt has two separate ways to involve a person.

| Path | Why the run stops | What the person provides | What happens next |
|---|---|---|---|
| **Operational attention** | The runtime cannot prove a target, identity, state, delivery, or effect condition. | A bounded recovery action, such as prepare the live state, reconcile, teach, or escalate. | The runner repeats the required live checks. It resumes only when they pass. |
| **Typed business decision** | The qualified workflow reaches a declared policy choice. | One finite option from the reviewed decision contract. | The runner records the answer, revalidates the live state, then follows only the successor bound to that option. |

Do not turn an operational halt into a business decision. Do not use a business
decision to bypass an identity, target, policy, postcondition, or effect gate.

## Define the decision during qualification

The person who records, reviews, or deploys a workflow can define a decision.
A separate author role is not required. The qualification interface or a
qualification tool can propose the contract, but the certified workflow version
must contain the reviewed result before a production run can use it.

Each decision contract includes:

- one reviewed question;
- two or more finite options;
- the roles that can answer;
- one exact successor for each option;
- an expiry time;
- any local evidence required for an option; and
- affirmative live-state checks that must pass after an answer.

The workflow graph contains a `business_decision` state. That state has no GUI
action. It pauses before the next branch. The certified graph binds every
option to one exact successor. A repair cannot remove, alter, or route around
that decision. A decision change creates a new qualification revision.

## What the operator sees

The operator sees a focused question and only the approved options. For
example:

> This item qualifies for the standard route and an approved exception. Which
> reviewed route applies?

- Use the standard route
- Send to the exception reviewer
- Stop this item

The exact wording and option labels are reviewed static workflow content. They
are not inferred from a screenshot, OCR, application name, parameter, or a
model. A customer-controlled local surface can also show the protected evidence
that the decision requires. A hosted phone surface shows only the reviewed
remote-safe presentation and closed status data.

This distinction lets the same product support institutional choices such as an
exception disposition, a work priority, an approved service route, or a
customer-specific approval path. OpenAdapt records the answer. It does not
learn a new policy from one answer or silently promote that answer into future
workflow behavior.

## What happens after an answer

An operator answer is not a click command and it is not a `VERIFIED` result.

1. The operator route authenticates the person and their role.
2. It submits one signed option with one idempotency key.
3. The runner validates the task, role, option, expiry, evidence bindings, and
   one-use answer scope.
4. The runner stores a signed answer receipt.
5. The runner obtains a fresh settled observation and runs the selected
   option's declared revalidation checks.
6. The runner follows only the successor bound to that option.
7. Every later consequential action still requires its normal target, identity,
   postcondition, and effect verification.

If the live application no longer matches the declared state, OpenAdapt halts
before the successor action. If the runner stops after it stores an answer, it
recovers the same signed answer on restart. It does not accept a different
answer for the same request.

The answer receipt proves that an authorized person selected one reviewed
option. The terminal execution receipt separately proves the business effect.
Only the terminal receipt can report `VERIFIED`.

## Mobile delivery and privacy

Desktop, Cloud, and a customer-controlled operator service can deliver the
same decision contract. The runner keeps live record values, screenshots, OCR,
and local evidence inside the declared customer boundary. The portable remote
task carries opaque bindings, option IDs, digests, counts, and closed status
values. It does not carry the question or option text. The receiving surface
resolves those reviewed static strings from a presentation artifact whose digest
the signed delivery policy binds to the exact decision contract.

If an option requires protected local evidence, the decision stays on a local
operator surface. The system does not copy that evidence to a phone or use an
unreviewed free-text field to describe it.

## Related documentation

- Use [attended decisions and the halt-learn loop](halt-learn-loop.md) when a
  runtime condition needs correction, reconciliation, or teaching.
- Use [qualification-owned entity language](qualification-owned-entity-language.md)
  to set an optional static item class for an operator surface.
- Use [run outcomes and halt reasons](../reference/run-outcomes.md) to interpret
  `decision_required` and terminal receipts.
- Use [Integrate OpenAdapt Execute](../commercial/execute-api.md) when a partner
  must receive the signed decision event.
