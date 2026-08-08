---
description: >-
  Add a reviewed human business decision to a qualified workflow without
  confusing it with an operational halt or an execution result.
---

# Human judgment in a workflow

Some workflow steps need a person to apply institutional policy. For example,
the available facts can support a priority review, a standard review, or a
supervisor route. OpenAdapt must not guess which policy applies.

OpenAdapt models this case as a **typed business decision**. It pauses at an
explicit graph node, asks one focused question, accepts one finite reviewed
option from an authorized role, then rechecks live state before it follows the
selected branch.

This page describes the product model. The runtime contract is available in
`openadapt-types` as `BusinessDecisionTaskV1` and
`BusinessDecisionAnswerReceiptV1`. A Cloud or Desktop delivery route must also
authenticate the person who answers. An answer receipt is not an execution
receipt and cannot report `VERIFIED`.

## Do not confuse the two human paths

| Path | Why the workflow pauses | What the person does | What OpenAdapt does next |
|---|---|---|---|
| [Operational attention](halt-learn-loop.md) | A target, identity, state, delivery, or effect check cannot be proven. | Correct the live state, reconcile, teach, escalate, or select another permitted recovery action. | Reacquire the live state and repeat the required checks. |
| Typed business decision | The workflow reaches a declared policy choice that automation cannot derive from the available facts. | Select one reviewed policy option. | Record the attributed answer, revalidate live state, and follow the exact branch for that option. |

An operational halt is a safety condition. A business decision is a declared
point of human authority. Do not use a business-decision node to bypass an
identity, target, postcondition, policy, or effect gate.

## Capture the decision during qualification

No special job title is required. The person who records, reviews, or deploys
the workflow can add the decision. A qualification tool can propose a draft.
The certified workflow version stores only the reviewed decision contract.

Direct authoring is the fast path. It works well when the organization already
has a clear written policy:

1. Add the decision node to the workflow graph.
2. Write one focused question in business language.
3. Add two or more finite options.
4. Assign the authorized role for each answer.
5. Bind each option to one exact successor.
6. State the live checks that must still pass before the successor can act.

When the policy is not yet clear, capture examples instead. Record several
realistic cases with the relevant facts and the human choice. Then record a
**counterfactual** case: change one fact that should change the decision, and
ask the reviewer to explain the permitted result. This separates a real policy
rule from a one-off preference or an accidental action.

The qualification review must preserve the distinction between these three
outcomes:

| Review result | Meaning | What the certified workflow does |
|---|---|---|
| **Automatic rule candidate** | The examples and counterfactuals support a repeatable rule with checkable facts. | Qualify the rule and its evidence checks. The rule still needs the normal certification tests. |
| **Human decision node** | The choice remains a valid human policy choice. | Keep the finite options and role requirement in the graph. |
| **More evidence required** | The cases do not identify a stable rule or a safe finite choice. | Request more examples or leave this part for a human. Do not infer a policy. |

Do not learn a production rule from one answer. A later review can promote a
rule candidate only by creating a new qualified workflow revision.

## What a reviewed decision contains

A decision contract includes:

- a static, reviewed question;
- two or more reviewed finite options;
- a permitted role or roles;
- an exact successor for every option;
- expiry and one-use scope;
- decision provenance: the workflow version, reviewer, policy source, and
  qualification revision; and
- the required state, identity, target, postcondition, and effect checks after
  the answer.

The task has no GUI action. It pauses before the next branch. A repair cannot
alter the option set or route around the node. A change to the question,
options, roles, or branches requires a new qualification revision.

The exact wording is reviewed workflow content. OpenAdapt does not create it
from screenshots, OCR, application names, input values, or a model during a
production run.

## Example: exception routing

An operations workflow receives a record that qualifies for either the normal
route or an approved exception. The qualified decision can ask:

> Which reviewed route applies to this item?

- Priority review
- Standard review
- Supervisor

The exact record identity remains on the customer-controlled runner. The
question does not ask the person to identify a record from a vague screen. The
runner checks the required record identity again before any later write.

## What happens after the person answers

The mobile or desktop surface shows one request, its reviewed context, and only
the options that the contract permits. It cannot add a new option or free-text
instruction.

1. The route authenticates the person and verifies their permitted role.
2. It submits one signed option with an idempotency key.
3. The runner validates the task, policy, presentation, role, option, expiry,
   and one-use binding.
4. The runner records a signed answer receipt.
5. The runner obtains a fresh settled observation and runs the selected
   branch's live-state checks.
6. The runner follows only the successor for that option.
7. Each later consequential action still requires target resolution, identity,
   postcondition, and effect verification.

If the application state changed, the task expired, the role is wrong, or the
answer was already used, the runner refuses the transition. It does not apply a
second answer. It does not replay a possibly consequential action without the
required checks.

The answer proves only this: an authorized person selected one reviewed option
for one task. It does not prove that an application changed. Only the terminal
execution receipt can report `VERIFIED`, and only after the configured effect
evidence passes.

## Data boundary

Raw examples, captured screens, OCR, identifiers, and full decision evidence
stay in the customer-controlled environment by default. A remote route receives
an opaque task binding and a reviewed presentation. The task carries identifiers,
digests, expiry, permitted option IDs, and closed status values. The reviewed
presentation carries the static question and labels that the operator may read.

The remote route does not receive raw cases or screen content. If a person must
inspect protected live evidence to make the choice, use the runner-local
operator surface or a customer-controlled delivery route.

## Related documentation

- [Attend a paused run and teach a correction](halt-learn-loop.md) for a
  runtime safety halt.
- [Qualify a workflow](../guides/qualify-a-workflow.md) for certification and
  versioning and the Desktop qualification cockpit.
- [Workflow IR](workflow-ir.md) for graph nodes and controlled branches.
- [Run outcomes and halt reasons](../reference/run-outcomes.md) for
  `decision_required` and terminal receipts.
- [OpenAdapt Types](https://github.com/OpenAdaptAI/openadapt-types) for the
  portable task and answer-receipt schemas.
- [OpenAdapt Flow](https://github.com/OpenAdaptAI/openadapt-flow) for the
  local runtime that validates the decision contract and performs the later
  revalidation.
