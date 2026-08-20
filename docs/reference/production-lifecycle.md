# Production admission

OpenAdapt uses evidence to derive Production for an exact release. Production
is not a static repository label. A release enters the signed Production
channel only when its target-specific acceptance record passes the public
policy.

## Qualified workflow

In this Production contract, a qualified workflow is one exact, sealed compiled
workflow version with an active signed admission. It passed its declared
acceptance cases on its bound execution environment. It is not a workflow
category and it is not a manual allowlist entry. The admission binds the
organization and workflow identity, bundle version and digest, admitted runtime
release, dependency set, application and environment, input and action
contracts, policy, identity checks, effect checks, verification rules, evidence
authority, issue time, expiry time, and revocation state.

For example, qualification can cover one invoice-entry bundle against one
declared application version, runner image, input schema, policy, and
independent saved-record check. It does not automatically cover another
application version, a changed bundle, or a different effect verifier.

The evidence must name the task, environment, condition, oracle, and failure
taxonomy. It must include at least three trials per task per condition. It must
report explicit silent-incorrect-success and over-halt counts, including zero
counts. A target-specific acceptance policy can require more evidence.

A Production run requires this exact qualified workflow identity. The run gate
must refuse an absent, expired, revoked, or mismatched qualification. A change
to a workflow version or any bound contract value, including the input schema,
requires a new qualification. Live input values that satisfy the admitted
schema do not each require requalification.

Workflow qualification and product release admission are separate contracts.
Workflow qualification proves the named business workflow in its environment.
Release admission proves that an exact OpenAdapt component or deployment passed
the target-specific product acceptance policy. A runtime can have a current
Production admission and still refuse an unqualified customer workflow.

## Release admission

The organization policy defines seven Production targets: the launcher, Flow,
Desktop, Cloud, Capture, Agent, and this documentation deployment. Each target
has its own claim scope, release shape, artifact authorities, and evidence
adapter. Evidence for one target cannot admit another target.

An admission binds:

- the exact target and claim scope;
- the monotonic Production release identity and its predecessor;
- the release or deployment and complete artifact inventory;
- the canonical lifecycle policy and acceptance policy;
- an independently attested, remote-safe acceptance summary;
- the oracle, task count, condition count, and trial count;
- every failure-taxonomy and reliability count; and
- an immutable evidence-retention record.

The admission validator checks current PyPI metadata, immutable GitHub release
metadata, or managed-evidence object metadata. It also verifies the GitHub
artifact attestation for the acceptance summary. Healthy-path model calls,
silent incorrect success, wrong-record effects, duplicate effects, collateral
effects, and uncertain delivery must all remain zero.

## Current-state derivation

Each target keeps an append-only hash chain of signed release identities. The
highest sequence is the current Production release. If its admission expires
or is revoked, that target has no current Production release. The validator
does not fall back to an older release.

The machine-readable [Production lifecycle record](../production-lifecycle.json)
contains the exact source commit, input hashes, policy, and admission history.
It does not store a static `production: true` flag. A consumer must use the
pinned validator and derive the state at read time.

This site derives each target label from that exact current admission. It shows
the product-wide Production label only when all seven targets have an active
admission and the current default versions of the five public packages match
those admitted releases on PyPI. Each version must retain an unyanked wheel and
source distribution. A record mismatch, expiry, revocation, version drift, or
authority outage suppresses the Production label.

Runnable does not mean admitted. An installation, release, or successful demo
cannot create Production state without this complete evidence contract.
