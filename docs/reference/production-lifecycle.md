# Production admission

OpenAdapt uses evidence to derive Production for an exact release. Production
is not a static repository label. A release enters the signed Production
channel only when its target-specific acceptance record passes the public
policy.

## Qualified workflow

A qualified workflow is one exact compiled workflow version that passed its
declared qualification contract on its bound execution environment. Its signed
identity binds the workflow bundle, runtime release, dependency set,
environment, input schema, policy, identity checks, effect checks, and
verification rules.

A Production runtime accepts only an exact qualified workflow identity. It
refuses an absent, expired, revoked, or mismatched qualification. A change to a
workflow version or any bound input requires a new qualification.

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

Runnable does not mean admitted. An installation, release, or successful demo
cannot create Production state without this complete evidence contract.
