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
It retains remote-safe-synthetic workflow-admission records and each bundle's
declared version. The projection includes tutorial bundles with
`bundle_version` `0.0.0-synthetic`. Its source descriptor binds the exact
OpenAdaptAI/.github commit and ledger hash.

A retained row doesn't establish current qualification. Verify the exact
workflow, admitted runtime, and current authority state before execution.
Synthetic evidence does not qualify a customer workflow.

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

The canonical admission verifier checks the signed evidence chain and the
current authority, revocation, and signer state. It hashes the supplied release
files against the admitted inventory. Publication checks depend on the recorded
release mode. Healthy-path model calls, silent incorrect success, wrong-record
effects, duplicate effects, collateral effects, and blind retry or replay after
uncertain delivery must all remain zero.

## Current-state derivation

Each target keeps an append-only hash chain of signed release identities. The
highest sequence is the current Production release. If its admission expires
or is revoked, that target has no current Production release. The validator
does not fall back to an older release.

The machine-readable [Production lifecycle record](../production-lifecycle.json)
contains the exact source commit, input hashes, policy, and admission history.
It doesn't store a static `production: true` flag. A consumer must use the
pinned validator and derive the state at read time.

For V2 admissions, the build retains a result from the canonical release
verifier in [production-lifecycle-verifications.json](../production-lifecycle-verifications.json).
Each result binds the exact admission object, signature bundle, release files,
and the trust state that the verifier checked. The generated result relies on
the reviewed documentation build; its own hash isn't an independent signature.
The build checks those retained bindings without changing the verification time.

At read time, the browser requires the live admissions ledger to match the
projection. It then verifies the latest admission's object and bundle hashes
against its generated result. Each signature statement in the evidence chain
must still be within its time window, and each used signer must remain active.
The browser reads the current canonical registry and
requires the same authority, revocation, and signer objects, with valid time
windows. An unrelated registry addition can leave those bindings intact. A new
trust object requires a new verification result.

Package checks read current PyPI and GitHub metadata. The default PyPI version
must match the admitted version, and each admitted file must keep its hash and
size and remain available without a yank. GitHub checks bind the release and
asset IDs, uploader identity, and the tag's resolved source commit. Public tag
ruleset fields must still match their recorded values.

The `already-published-pypi` mode supports releases that predate GitHub release
immutability. It doesn't require a release-app uploader or `immutable: true`.
The `draft-before-tag` mode keeps those requirements. GitHub's repository
immutability setting and ruleset bypass actors require authenticated access;
the public page retains their issuance-time observations and makes no claim
that it can read them in the browser.

A failed request or changed binding removes the target's active label. A
missing verification result never restores an older release. Cloud and Docs
retain their deployment admissions; a retained deployment URL alone cannot
prove current deployment state. Their active labels require a current public
deployment observation. The product-wide Production label requires all seven
targets to pass.

To refresh a V2 result after updating the exact source descriptors, use the
release files that the canonical verifier must check:

```bash
python scripts/generate_production_lifecycle_verification.py \
  --target flow --artifact-root /path/to/verified/release-files
python scripts/generate_production_lifecycle_verification.py --check
```

Generation fails without a successful canonical verification. Commit the
result with its source pin and review it before publishing the site.

An installation, release, or successful demo cannot create Production state
without this complete evidence contract.
