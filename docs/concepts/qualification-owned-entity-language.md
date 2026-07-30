---
description: >-
  Define the safe entity language that OpenAdapt can show for one qualified
  workflow step without sending live record data outside the runner.
---

# Qualification-owned entity language

An attended decision can name the *kind* of item that OpenAdapt must check.
It must not name the live item itself.

For example, a decision can say:

- `patient record`;
- `insurance claim`; or
- `loan application`.

Those labels make an operator question clear. They do not contain a patient
name, account number, claim number, screen text, or another live identifier.

## Availability

The signed V2 decision schema and Cloud receiver now preserve a reviewed entity
class and a neutral fallback. The Flow command and Desktop control that set a
class are part of the coordinated V2 release work. Until that release, do not
edit a signed task or sealed artifact by hand to change its wording.

## Set the label during qualification

With the coordinated Flow and Desktop release, select one reviewed entity class
for an exact workflow step that can create an attended decision. The class
belongs to that step in that workflow version. It is not a setting for the
whole organization or for all workflows that use the same application.

The qualification contract records:

- the exact workflow bundle and revision;
- the exact step;
- the reviewed entity class; and
- a neutral fallback, normally `record` or `item`.

For example, an OpenEMR check step can use `patient record`. A lending workflow
can use `loan application`. A generic workflow can use `record`.

## What happens at run time

When the exact qualified step halts, Flow copies the approved class into the
signed decision task. Cloud and Desktop show that class only when they can
validate the task and recognize its reviewed remote-safe vocabulary.

The runner keeps the actual identity evidence in its declared customer
boundary. Before it resumes any action, it checks the live identity, current
workflow state, focus, and target again. The label never approves an action by
itself.

If the signed class is unavailable, unknown, or not supported by the receiving
surface, the surface shows the signed neutral fallback: `record` or `item`.

## What OpenAdapt does not do

OpenAdapt does not derive this label at run time. It does not use a screenshot,
OCR, DOM or UIA content, application name, input parameter, or an LLM to decide
that an item is a patient, claim, loan, or another domain object.

This rule keeps presentation language stable and prevents a remote decision
surface from receiving live entity information merely to choose its wording.

## Change control

The class is part of the qualification contract. A change creates a new
qualification revision and invalidates the previous certification. Review the
change, run the required cases, and certify the new sealed version before
deployment.

See [Qualify a workflow](../guides/qualify-a-workflow.md) for the full
qualification process and [attended decisions](halt-learn-loop.md) for the
operator path.
