# Glossary

This page is where OpenAdapt defines its terms. The README, the other docs
pages and the package docs link here instead of defining them again. For the
same terms in plain language, see the
[plain-language glossary](../evaluate/glossary.md), which maps each plain term
to an entry on this page.

The three terms people confuse most are [qualify](#qualify),
[certify](#certify) and [admission](#admission). Qualifying produces evidence
that one workflow works in its environment. Certifying checks a bundle, or a
qualification result, against a [certification policy](#certification-policy).
An admission is the signed record that lets one exact qualified version run in
Production. The [Production admission](production-lifecycle.md#qualified-workflow)
page holds the contract that binds them.

## Admission

A signed record that lets one exact, sealed workflow version run in
Production. It binds the organization and workflow identity, the bundle
version and digest, the runtime release, the application and environment, the
input and action contracts, the policy, the identity and effect checks, and an
expiry and revocation state. A Production run refuses an absent, expired,
revoked, or mismatched admission. A changed bundle or bound contract needs a
new [qualification](#qualify) and admission. See
[Production admission](production-lifecycle.md).

## BYOC

**Bring your own cloud (BYOC)** is the existing OpenAdapt connector and
configuration name for a customer-owned cloud runner and storage boundary.

OpenAdapt Cloud can send bounded authorization and control metadata to that
runner. Cloud receives only the declared result and evidence permitted by the
deployment data boundary. Live screenshots, sensitive parameters, and verifier
values can remain inside the customer boundary.

The broader public term is **customer-controlled execution**. A
customer-controlled runner can also run on a workstation, server, or
on-premises virtual machine. Those deployments do not have to use BYOC.

BYOC does not mean bring your own compute. It does not mean customer-provided
source code. It does not grant unrestricted access to OpenAdapt Cloud.

See [Deployment boundaries](../commercial/deployment-boundaries.md) and
[Integrate OpenAdapt Execute](../commercial/execute-api.md).

## Bundle

The compiled program and the files that travel with it: the workflow
program, its effect contracts, and its metadata. A bundle is bound to one
[substrate](#substrate). See [The bundle format](bundle-format.md).

## Capability ladder

The ordered set of resolution strategies the replayer tries when re-finding a
step's target, from the cheapest deterministic rung (structural DOM/UIA/AX
identity, then template crop, OCR label, geometry landmarks) up to an optional
grounding model. The healthy path resolves on a deterministic rung with zero
model calls; a rung change is recorded in the run report. See
[The capability ladder](../concepts/capability-ladder.md).

## Certify

<a id="certification"></a>

To **certify** is to check a bundle against a
[certification policy](#certification-policy) and refuse it when it fails.
There are two ways to do it:

- `openadapt flow certify` checks a bundle against a policy and exits nonzero
  when it fails, so CI and deploy gates can refuse an unsafe bundle.
- Certifying a [qualification](#qualify) result also checks the evidence. It
  refuses unless every qualification case ran and passed and the bundle meets
  every rule of the policy, and then signs the result under that policy. This
  is the `--certify` option of `qualify` on Flow's `main` branch. It isn't in
  a Flow release yet.

Certification makes "runnable" distinct from "certified safe". Sealing a
bundle expires certification inherited from its source. See
[Policy and certify](../concepts/policy-and-certify.md) and the engine's
[qualification terms](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/QUALIFICATION_TERMS.md#certify).

## Certification policy

<a id="policy"></a>

A reviewable YAML document, or a built-in such as `clinical-write` or
`permissive`, that states what a bundle must satisfy to be trusted: which
steps must confirm the target before acting, which writes must be confirmed in
the system of record, which steps need screen checks, and what needs a
person's sign-off. Certification enforces it at the gate, and the run gate
enforces it at execution. See
[Write and enforce a policy](../guides/policy-and-certification.md) and the
[policy rules](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/QUALIFICATION_TERMS.md#certification-policy).

## Demonstration

A recording of a task in the real app. A person or an agent shows the task
while OpenAdapt watches. One or more demonstrations go into the compiler,
which turns them into a [bundle](#bundle). See
[The demonstration compiler](../concepts/demonstration-compiler.md) and
[Multi-trace induction](../concepts/multi-trace-induction.md).

## Effect contract

A step's typed declaration of the **business effect** its write must produce
in the system of record (for example: this record exists with this value).
Effect contracts are checked by an independent read — API, database, or
document hash, not the pixels — and a non-confirmed verdict halts the run.
Reports record them as one-way SHA-256 digests. See
[Effect verification](../concepts/effect-verification.md).

## Effect verifier

An **effect verifier** is the configured independent read that evaluates an
[effect contract](#effect-contract). It reads the system of record, such as an
API, database, audit feed, or document store. A verifier does not infer a
write from screen pixels. Its confirmed, refuted, or indeterminate result
decides whether the run can continue.

## Halt

The runtime's refusal to act: when identity, a postcondition, an
effect verdict, a policy gate, or an unhandled screen state does not match the
compiled expectation, the run stops and records what it observed instead of
guessing. A halt is a governed outcome, not a crash; it can be answered by an
operator (durable pause) or resolved permanently with `teach`. See
[Run outcomes and halt reasons](run-outcomes.md) and
[The halt-learn loop](../concepts/halt-learn-loop.md).

## Identity gate

The pre-click check on consequential steps that verifies the on-screen record
identifier against the run's expected identity evidence before acting (the
wrong-record guard). A conflict or an unreadable identity band halts the run
instead of clicking into the wrong record. See
[The identity gate](../concepts/identity-gate.md).

## Oracle tier

How a Seal checks the business effect. Tier 0 is visual / OCR. Tier 1 is a
second session or independent UI read. Tier 2 is a system-of-record read (API,
database, file, ack). Tier 3 is a counterparty artifact. Production Seals mint
only at 2 and 3. Charge those two. See [The Seal](../commercial/seal.md).

## Reconciliation

**Reconciliation** is a no-re-dispatch check after delivery is uncertain or an
effect conflicts with the requested result. The runner reads the required
postcondition and independent effect again. It reports a reconciled result only
when that read proves the effect; otherwise the run stays halted for review.

## Profile

A named runtime posture (`demo`, `standard`, or `regulated`) that selects
which requirements the run gate enforces (certification, identity coverage,
effect contracts and their minimum tier, encryption, durability) and how the
outcome may be described. Only Standard and Regulated runs can report
`VERIFIED`. See [Run outcomes](run-outcomes.md) and
[Regulated execution](../concepts/regulated-execution.md).

## Qualify

<a id="qualification"></a>

To **qualify** a workflow is to run its compiled bundle against a
representative case and a set of deliberate fault cases, several trials each,
before it may run unattended on a real system (`openadapt flow qualify`). It
passes only when the representative case completes and its write is confirmed
by a read of the system of record, not the screen, and every fault case halts
before anything is written.

The result is a **qualification**: recorded evidence for the exact workflow,
application, and environment it ran in. A different application version, a
changed screen, or a different system of record needs a new qualification. A
pass doesn't show that the workflow handles inputs or screens the cases didn't
exercise. Qualifying is optional for read-only tasks. Contrast with
[certify](#certify), the policy check. See
[Qualify a workflow](../guides/qualify-a-workflow.md), and the engine's
[qualification terms](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/QUALIFICATION_TERMS.md#qualify) for the fault cases and what gets signed.

## Runner

The computer that executes runs: one you control, or one OpenAdapt hosts. See
[Deployment boundaries](../commercial/deployment-boundaries.md).

## Seal

A signed attestation that one program version, identity, environment, and
independent effect produced `VERIFIED`, `HALTED`, or
`RECONCILIATION_REQUIRED`. The portable object is `ExecuteEvidenceReceiptV1`.
Execute issues it (`POST /api/v1/executions`). Local unsigned replay stays
free. Unsigned success is failure. See [The Seal](../commercial/seal.md).

## Substrate

The surface a workflow is recorded and executed on: a web browser, native
Windows, macOS or Linux, or a remote display such as RDP or Citrix. OpenAdapt
reads every substrate from what is on screen. Where a substrate also exposes
structure (the browser DOM, Windows UI Automation, macOS Accessibility, or
Linux AT-SPI), that structure adds evidence for the
[capability ladder](#capability-ladder) and the [identity gate](#identity-gate).
RDP and Citrix give pixels only. Bundles are bound to one substrate, and a
run never switches substrate silently. See
[The substrate model](../concepts/substrate-model.md) and
[backends](../concepts/backends.md).
