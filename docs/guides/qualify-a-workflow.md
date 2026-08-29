---
description: >-
  Review a compiled workflow, assign risk, bind identity and effect checks, run
  qualification cases, certify it, and export a sealed governed artifact.
---

# Qualify a workflow

Qualification turns a compiled demonstration into a governed artifact tied to
one application, version, execution surface, and environment. It is the review
between **compiled** and **ready to deploy**.

OpenAdapt Desktop provides the complete guided path. The same contract is
available through `openadapt flow qualify` for automation and integration.

## Open the qualification cockpit

In Desktop, open a compiled workflow and choose **Qualification**. For a new
project, define:

- the execution surface: Browser, Windows, macOS, Linux, RDP, or Citrix;
- the application and version;
- a stable environment identifier shared with the qualification runner;
- any required runner capabilities; and
- the minimum acceptable effect-verification tier.

Starting the project retains the compiled workflow and creates a versioned
qualification contract. Later edits advance its revision and invalidate stale
case evidence and certification.

## Review the compiled graph and every action

The **Workflow structure** view shows actions, branches, loops, exception paths,
terminal outcomes, and the retained targeting ladder. Review the inferred
program before assigning safety contracts.

For every action, confirm one business-risk class:

- **Read-only** observes without changing business state.
- **State-changing** changes UI or transient application state.
- **Consequential** can change a meaningful business record or trigger an
  external effect.
- **Irreversible** is consequential and cannot be safely undone through the
  qualified workflow.

The cockpit explains unresolved classifications and coverage gaps under **What
must be resolved**. Certification refuses an unreviewed action rather than
guessing.

## Arm identity before consequential actions

Select a consequential action under **Arm identity and bind the business
effect**. Identity can use the canonical evidence ladder or a quorum of explicit
signals such as application, session, workflow state, subject name, record ID,
and secondary identifier.

Each signal declares its source, exact or normalized comparison, and, when
needed, its screen region, parameter binding, or extraction rule. Duplicate or
conflicting records remain refusal conditions.

## Safe entity language for attended decisions

The released `HumanDecisionTaskV2` schema and Cloud receiver define the target
contract for an approved entity class and neutral fallback. Flow 1.30.0 emits
only `HumanDecisionTaskV1`: it does not yet store or emit the V2
qualification-bound entity class. Until the coordinated Flow and Desktop
release, use the neutral `record` or `item` wording and do not edit a signed
task or sealed artifact by hand.

The class is optional presentation metadata. It does not require a separate
author role, and its absence does not block qualification, certification, or
execution.

With the coordinated release, the person or tool that prepares the
qualification can select a static class for a step that can halt for an
operator. For example, use `patient record`, `insurance claim`, or `loan
application`. This class describes the kind of item. It never contains the
live identity of the item.

The target contract binds the class and a neutral `record` or `item` fallback
to the exact qualification. A signed V2 decision task carries the approved
class to a remote operator surface. The receiver renders only reviewed safe
classes and uses the fallback when no class was set or when it cannot validate
the class. A class change creates a new qualification revision and requires
recertification.

OpenAdapt never infers this language from a screen, OCR, parameters, an
application name, or a model. See [qualification-owned entity
language](../concepts/qualification-owned-entity-language.md) for the complete
rule and current release status.

## Bind the resulting business effect

Identity proves OpenAdapt is acting on the intended record. Effect verification
proves the intended state persisted. Bind each consequential write to a verifier
and choose the minimum accepted strength:

1. **Independent system**: API, database, audit feed, or downstream record.
2. **Independent session**: a separate read-only session retrieves the result.
3. **Persisted-state reacquisition**: leave the record, find it again, and read
   the saved value.
4. **Immediate screen**: the current field, banner, or notification.

The workflow-level minimum and each effect binding are both enforced. A weaker
observation cannot be promoted to `VERIFIED` merely because the UI looked
successful.

## Run representative and fault cases

Add the normal cases the workflow must complete and the uncertainty cases it
must refuse. The cockpit supports representative, ambiguity, wrong-identity,
stale-identity, weak-effect, and missing-effect cases.

Choose the local execution target and optional deployment config, then select
**Run and sign case**. Case parameters stay in the local fixture store outside
the workflow. Secret values are refused there and remain runner credential
references. Desktop retains the raw report locally and adds a signed receipt
containing its hash, outcome, required and passed contracts, evidence classes,
model-call count, and external-network-call count.

Signed results from another customer-controlled qualification runner can be
imported. The signature, workflow revision, environment, runner capabilities,
and evidence hashes must match the project.

## Certify and publish an immutable version

When action review, identity coverage, effect coverage, and required cases all
pass, choose **Run certification**. Every refusal remains visible with the exact
action and contract that must be resolved.

The artifact controls then provide the normal production lifecycle:

1. **Create working version** preserves the previous revision.
2. **Seal and encrypt version** creates a protected candidate and stores only
   its key reference in the operating-system credential store.
3. Run the required cases and certify that exact sealed version.
4. **Export qualified artifact** creates a deterministic archive with a
   SHA-256 digest, or **Deploy qualified artifact** prepares the reviewed,
   sanitized Cloud path.

Raw recordings, reports, screenshots, case inputs, and secret values remain
inside the declared local boundary. Deployment never turns a pending local
review into an upload.

## Script the same contract

The CLI exposes the same versioned project:

```bash
openadapt flow qualify init bundle \
  --target citrix \
  --application Accuro \
  --application-version 2026.1 \
  --environment-digest "$QUALIFIED_ENVIRONMENT_SHA256" \
  --minimum-tier 3

openadapt flow qualify inspect bundle --policy clinical-write
openadapt flow qualify set-risk bundle \
  --step step_012 \
  --classification consequential \
  --explanation "Writes the appointment record"
openadapt flow qualify explain bundle --policy clinical-write
openadapt flow qualify certify bundle \
  --policy clinical-write \
  --evidence-root qualification-evidence
```

Use `openadapt flow qualify schema` for the machine-readable project schema and
[`openadapt flow qualify --help`](../reference/cli.md#qualify) for identity,
effect, case, runner-trust, requalification, report, and certification commands.
