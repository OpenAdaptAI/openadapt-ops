---
description: >-
  Add a question to a workflow that an authorized person answers from a fixed
  list, with one qualified branch for each answer.
---

# Add a human decision during qualification

Some workflows have a point where a person has to choose, for example which
reviewed path an item follows. A business decision makes that choice part of
the program. The run stops at the decision, an authorized person picks one of
two to four fixed answers, and the run continues on the branch for that
answer.

A business decision is not a halt. A halt is the engine stopping because it
can't confirm a step. A business decision is a choice you declare in advance,
with its answers, the roles that may answer, and where each answer leads. It
doesn't prove which record is open or that a save worked; the normal checks
still do that. A workflow with no such choice doesn't need one.

## Add one in Desktop

Open the workflow in OpenAdapt Desktop's qualification cockpit. Under
**Human judgment**, choose **Add a new decision** and fill in:

| Field | What to enter |
|---|---|
| Ask before this step | The existing step the question goes in front of |
| Question for the operator | One question, up to 500 characters |
| Authorized roles | The role names your operator sign-in provides, such as `supervisor` |
| Answer window | How long an answer is accepted, in minutes |
| Qualified answers and branches | Two to four answers, each with the step it continues to |
| Optional evidence requirements | Local evidence a person must attach for a given answer |
| Live check before the selected branch continues | Text that must still be visible, or a recorded target that must still be found |

Press **Add decision**. Desktop sends the form to Flow as an
`openadapt.business-decision/v1` contract, and Flow adds the decision and its
branches to the program.

The step you choose must be the start of the workflow or have exactly one step
leading to it, so one decision can't silently change several paths.

Saving advances the qualification revision and removes the existing
certification. Run the qualification cases again and certify the new version
before you use it in production. See
[Certify and qualify](certify-and-qualify.md).

## Add one from the command line

`qualify business-decision` takes the same contract as a JSON file:

```json
{
  "schema_version": "openadapt.business-decision-authoring/v1",
  "graph_id": "__program__",
  "state_id": "choose_path",
  "insert_before_state_id": "save",
  "decision": {
    "schema_version": "openadapt.business-decision/v1",
    "question": "Which reviewed path should this item follow?",
    "authorized_roles": ["supervisor"],
    "output_param": "path",
    "options": [
      {"id": "approve", "label": "Approve", "value": "approve", "target": "save"},
      {"id": "hold", "label": "Hold for review", "value": "hold", "target": "hold_note"}
    ],
    "expires_after_s": 3600,
    "revalidation": [{"kind": "text_present", "text": "Item details"}]
  }
}
```

```bash
openadapt flow qualify business-decision bundle --input decision.json
openadapt flow qualify business-decision bundle --check   # list the decisions
```

`graph_id` is `__program__` for the main program or the name of a subflow.
Omit `insert_before_state_id` to change a decision that already exists; its
`output_param` can't change.

## The contract

| Field | Rule |
|---|---|
| `question` | 1 to 500 characters |
| `authorized_roles` | At least one role |
| `output_param` | The parameter that receives the answer's `value` |
| `options` | Two to four, each with `id`, `label`, `value`, and `target` (the next step), and optional `required_evidence` |
| `evidence_requirements` | Optional `{id, label}` items that options can require |
| `expires_after_s` | 30 seconds to 7 days; 3600 by default |
| `revalidation` | At least one check of the live screen, run before the chosen branch continues |

A decision step can't contain an action, a loop, a subflow, or a result.
A repair can't change a decision or route around it; that needs a new
qualification.

## What happens at run time

1. The run reaches the decision, takes no action, and pauses where it can
   resume.
2. The runner writes a signed request for the decision, with its expiry.
3. An authorized person picks one answer. Flow checks the role, the answer,
   the expiry, and any required evidence, then writes a signed receipt.
4. When the run resumes, Flow takes a fresh screenshot and runs the live
   checks. At least one must confirm text or a target on screen; the answer
   itself can't satisfy them.
5. The run continues only to the step bound to that answer. Every later step
   still passes its own target, identity, and record checks.

One answer chooses one branch for one run. It doesn't change the workflow for
later runs. If a request expires while the run is still paused, the runner
writes a new one.

To answer through a customer-run service or from OpenAdapt Cloud, see
[Typed business decisions](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/BUSINESS_DECISIONS.md)
in the engine repository. Answering from Cloud also needs keys provisioned on
the runner and a reviewed delivery binding in the qualification.
