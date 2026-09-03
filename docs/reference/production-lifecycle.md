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
counts. It must also include at least three expected uncertain-delivery fault
trials. Each fault trial must return `RECONCILIATION_REQUIRED` without a blind
retry or replay dispatch. A target-specific acceptance policy can require more
evidence.

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

The public workflow ledger is
[production-workflow-admissions.json](../production-workflow-admissions.json).
It currently lists seven synthetic admission records (bundle_version
`0.0.0-synthetic`, evidence class remote-safe-synthetic). Each record has a
null expiry, so none is actively admitted. These aren't customer workflows.
The source pin is OpenAdaptAI/.github
`078db7a9399702d0b725676e4a427b1b52fb19ff`.

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
It doesn't store a static `production: true` flag. A consumer must use the
pinned validator and derive the state at read time.

At the current source pin, all seven release records have a null expiry. No
target is actively admitted.

The documentation build runs that pinned validator. It verifies the signed
summary and its GitHub attestation before publishing the projection. At read
time, the browser requires the current admissions file to match the projected
digest. It then checks the signed summary, attestation bundle, retained
manifest, and current artifact-authority metadata. A failed request removes the
affected target from the active set.

This site derives each target label from that exact current admission. It
checks the current authority metadata for every admitted artifact and retained
evidence object. The five public package versions must match their admitted
PyPI releases. A record mismatch, expiry, revocation, artifact drift, or
authority outage removes the affected target from the current Production set.
The product-wide Production label appears only while all seven targets pass.

An installation, release, or successful demo cannot create Production state
without this complete evidence contract.
