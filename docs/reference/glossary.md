# Glossary

Short definitions for terms used across OpenAdapt.

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

## Capability ladder

The ordered set of resolution strategies the replayer tries when re-finding a
step's target, from the cheapest deterministic rung (structural DOM/UIA/AX
identity, then template crop, OCR label, geometry landmarks) up to an optional
grounding model. The healthy path resolves on a deterministic rung with zero
model calls; a rung change is recorded in the run report. See
[The capability ladder](../concepts/capability-ladder.md).

## Certification

The **enforced gate** over a bundle: `openadapt flow certify` evaluates a
[policy](#policy) against the bundle and exits nonzero when it fails, so CI
and deploy gates can refuse an unsafe bundle. Certification makes "runnable"
distinct from "certified safe"; sealing a bundle expires certification
inherited from its source. Contrast with [qualification](#qualification),
which is evidence that the workflow behaves correctly on its target. See
[Policy and certify](../concepts/policy-and-certify.md).

## Effect contract

A step's typed declaration of the **business effect** its write must produce
in the system of record (for example: this record exists with this value).
Effect contracts are checked by an independent read — API, database, or
document hash, not the pixels — and a non-confirmed verdict halts the run.
Reports record them as one-way SHA-256 digests. See
[Effect verification](../concepts/effect-verification.md).

## Halt

The runtime's fail-closed refusal to act: when identity, a postcondition, an
effect verdict, a policy gate, or an unhandled screen state does not match the
compiled expectation, the run stops and records what it observed instead of
guessing. A halt is a governed outcome, not a crash; it can be answered by an
operator (durable pause) or resolved permanently with `teach`. See
[Run outcomes and halt reasons](run-outcomes.md) and
[The halt-learn loop](../concepts/halt-learn-loop.md).

## Identity gate

The pre-click check on consequential steps that verifies the on-screen record
identifier against the run's expected identity evidence before acting — the
wrong-record guard. A conflict or an unreadable identity band halts the run
rather than clicking into the wrong record. See
[The identity gate](../concepts/identity-gate.md).

## Policy

A reviewable YAML document (or built-in, such as `clinical-write`) stating
what a bundle must satisfy to be trusted: which risks need identity arming,
what postconditions and effect strength writes require, and what is refused
outright. A policy is enforced by [certification](#certification) at the gate
and by the run gate at execution. See
[Write and enforce a policy](../guides/policy-and-certification.md).

## Profile

A named runtime posture — `demo`, `standard`, or `regulated` — that selects
which requirements the run gate enforces (certification, identity coverage,
effect contracts and their minimum tier, encryption, durability) and how the
outcome may be described. Only Standard and Regulated runs can report
`VERIFIED`. See [Run outcomes](run-outcomes.md) and
[Fail-closed regulated execution](../concepts/regulated-execution.md).

## Qualification

Structured **evidence** that one workflow behaves correctly on its target
application and surface: representative cases plus deterministic fault cases
that must halt, executed and recorded (`openadapt flow qualify`). A
qualification belongs to the exact workflow, application, and environment; it
is the artifact a pilot or deployment reviews. Contrast with
[certification](#certification), the policy gate. See
[Qualify a workflow](../guides/qualify-a-workflow.md).

## Substrate

The surface a workflow is recorded and executed on: web (browser DOM), native
Windows (UIA), macOS (AX), Linux (AT-SPI), or a remote display such as RDP or
Citrix (pixels). The substrate determines what structural evidence exists for
the capability ladder and the identity gate; bundles are surface-bound and a
cross-surface run is never silent. See
[The substrate model](../concepts/substrate-model.md) and
[backends](../concepts/backends.md).
