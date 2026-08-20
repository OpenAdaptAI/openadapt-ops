# Core GitHub protection policy

This directory contains the reviewed target policy for eight public core
repositories. The policy does not manage `openadapt-cloud`. It does not manage
a foreign repository.

The policy has these results:

- All changes to `main` use a pull request.
- No person, administrator, role, team, deploy key, or app can bypass the
  `main` rule.
- One review is necessary. A new push makes an old review invalid. A different
  person must approve the last push. All review threads must be complete.
- Each check in the policy comes from the GitHub Actions integration.
- The branch must be current with `main` before GitHub admits it.
- Only the `openadapt-release` GitHub App can create a release tag.
- A second ruleset prevents all identities, including the release app, from
  changing or deleting that tag.
- A protected environment admits only the exact branch or tag pattern in the
  policy.
- A required reviewer must approve each release environment use.
- The lifecycle environments prevent self-review. The founder reviews a run
  that the separate lifecycle App starts.
- The lifecycle App has no `main` bypass and no Contents permission.

GitHub documents the applicable [repository ruleset API](https://docs.github.com/en/rest/repos/rules),
[environment API](https://docs.github.com/en/rest/deployments/environments), and
[deployment policy API](https://docs.github.com/en/rest/deployments/branch-policies).

## Files

`core-protection-policy.json` is the source of truth. It records the exact
repository names, audited `main` commits, check names, tag patterns,
environments, and release workflow contracts.

`scripts/manage_github_protection.py` validates, plans, applies, and verifies
the policy. A plan and a verify operation use only GitHub `GET` requests.

## Read-only audit on 2026-08-20

The public GitHub API reported zero repository rulesets in all eight
repositories. GitHub marked these `main` branches as protected: `OpenAdapt`,
`openadapt-flow`, `openadapt-capture`, `openadapt-evals`, and `openadapt-web`.
It marked `openadapt-desktop`, `openadapt-ops`, and `.github` as not protected.

The public API did not expose the classic branch protection detail. The local
GitHub CLI tokens were invalid. Therefore, this audit does not claim the exact
classic protection settings for the five protected branches.

Flow and Evals had an unprotected `pypi` environment. Capture and OpenAdapt had
no release environment. Desktop had a protected `native-release` environment.
It admitted `desktop-v*` and `ffmpeg-runtime-v8.1.2-r1`. The target policy uses
`desktop-v*` and `ffmpeg-runtime-v*`. It also adds the release identity
environment and the PyPI environment. The tool does not change the Ops backup
environments.

The organization did not have an `openadapt-lifecycle` App installation. The
target policy keeps the App ID, bot actor ID, and installation ID unresolved.
The plan and apply operations refuse this state. Do not create a lifecycle
environment until the exact App installation exists.

Ops `main` had no protection. The existing `production-backup` and
`production-backup-monitor` environments had no protection rule, deployment
branch policy, or reviewer. This policy records that finding. It does not
change the two operational backup environments.

## Required check selection

The policy requires only a check that starts on every pull request. GitHub can
leave a path-filtered required workflow in a pending state when its paths do
not match. Such a workflow can then stop an unrelated pull request.

The policy records a path-scoped check in `path_scoped_checks`. It does not make
that check a global requirement. The target policy does require
`build-and-e2e` in `openadapt-web`, `validate-profile` in `.github`, and
`Validate Production lifecycle` in Ops. The tool refuses an apply while one of
these workflows has pull request path filters. Keep each exact check name. Use
a cheap internal path classifier when the expensive work does not apply.

## Documentation and lifecycle environments

Ops uses `github-pages` for the documentation deployment. It admits only
`main`. The registered `.github/workflows/sync.yml` contract requires the
`github-pages` environment, `pages: write`, and `id-token: write`.

Documentation synchronization uses a separate `openadapt-docs` App. The App is
not present. The policy keeps its App ID, bot actor ID, and installation ID
unresolved. It has an exact Ops-only scope. It has Actions write, Metadata read,
and Pull requests write. It has no Contents write and no ruleset bypass.

The dispatch job enters `production-docs-deploy`. This environment admits only
`main`, requires `abrichr`, and prevents self-review. `sync.yml` accepts only
`workflow_dispatch` when both the actor and triggering actor are
`openadapt-docs[bot]`. It binds the source repository,
source `main` ref, source commit, `push` event, and idempotency value. It checks
the source repository against the reviewed `repos.yml` allowlist. It verifies
that the source commit is the current default-branch commit before an effect.
The idempotency value is `docs-sync:` plus 64 lowercase hexadecimal characters.
It uses the `OpenAdapt docs sync dispatch v1` domain and binds the closed
repository, ref, commit, and event tuple. It does not accept
`repository_dispatch` or the old `repo-updated` event. After approval, the
workflow token can push only an automation branch. The docs App token creates
the pull request. A later approved `main` push enters `github-pages` and deploys
the site. The workflow must not push to `main` directly.

The global environment default stays at `prevent_self_review: false`. The five
lifecycle environments set an explicit override to `true`:

- `.github` uses `production-lifecycle-activation` only from
  `.github/workflows/production-lifecycle-activation.yml`.
- `.github` uses `qualification-authority-state` only from
  `.github/workflows/qualification-authority-state.yml`.
- `.github` uses `qualification-revocation-state` only from
  `.github/workflows/qualification-revocation-state.yml`.
- Evals uses `production-lifecycle-evidence` only from
  `.github/workflows/production-lifecycle-evidence.yml`.
- Ops uses `production-lifecycle-projection` only from
  `.github/workflows/production-lifecycle-projection.yml`.

Each environment admits only `main`. The required reviewer is `abrichr`. The
workflow actor and triggering actor must be `openadapt-lifecycle[bot]`. The
policy verifies the exact App ID, bot actor ID, installation ID, and repository
variables. The installation scope must contain only `.github`,
`openadapt-evals`, and `openadapt-ops`.

The two qualification workflows attest their exact candidate state and open a
reviewable pull request. They cannot push to `main`. The Ops projection accepts
only `production_lifecycle_ledger_changed` from exact `OpenAdaptAI/.github`
`main`. It binds the current 40-character source commit, the exact admissions
digest, the ledger-head digest, and the projection idempotency digest. Each
digest uses `sha256:` plus 64 lowercase hexadecimal characters. The ledger head
uses the `OpenAdapt production lifecycle ledger head v1\0` domain. Projection
idempotency uses the `OpenAdapt production lifecycle projection idempotency
v1\0` domain.

The lifecycle App has only these repository permissions:

- Actions: write
- Metadata: read
- Pull requests: write

It has no Contents write permission. It has no ruleset bypass. After the
founder approves the environment, the workflow `GITHUB_TOKEN` pushes the
automation branch. The lifecycle App token creates the pull request. The
normal pull request checks then run. A lifecycle workflow must not push to
`main` directly.

Actions write also permits the App to cancel or rerun workflow runs and delete
workflow artifacts. The exact repository scope limits this authority. The
policy inventories every workflow that accepts `workflow_dispatch` or
`repository_dispatch` in the three repositories. Only the five lifecycle
workflows can accept the lifecycle App actor. Each other manual path needs a
`reject-lifecycle-app` predecessor with no permission. It checks both
`github.actor` and `github.triggering_actor`. Each later job depends on that
predecessor and repeats both identity refusals before GitHub allocates a job.
A new or unguarded path blocks apply.

Each dispatch path uses a workflow-and-event-specific concurrency group. It
sets `cancel-in-progress` to `false`. A manual run cannot cancel a real run.
Production evidence remains content-addressed outside mutable Actions
artifacts.

## Release sequence

Use this sequence for each package repository:

1. A workflow on exact `main` enters the `release-identity` environment.
2. The workflow gets a short-lived `openadapt-release` App token.
3. The app opens a version pull request. It does not push to `main`.
4. The normal `main` rules admit the version pull request.
5. An approved workflow uses the app to create the exact release tag.
6. The tag starts the publication workflow.
7. The publication job enters `pypi` or `native-release`.
8. The job uses OIDC to publish the exact tag bytes.

An event from `GITHUB_TOKEN` does not normally start another workflow. GitHub
documents this behavior in the [GITHUB_TOKEN reference](https://docs.github.com/en/actions/concepts/security/github_token).
Use the release App token for the release pull request and tag events.

The current package release workflows still refer to `ADMIN_TOKEN`, or they do
not use both protected environments. The plan reports this state as a refusal.
Migrate these workflows before an apply operation.

## Commands

Validate only the local policy:

```bash
uv run python scripts/manage_github_protection.py validate-config
```

Create a live read-only plan:

```bash
export OPENADAPT_RELEASE_APP_ID=123456
export OPENADAPT_LIFECYCLE_APP_ID=234567
export OPENADAPT_LIFECYCLE_ACTOR_ID=345678
export OPENADAPT_LIFECYCLE_INSTALLATION_ID=456789
export OPENADAPT_DOCS_APP_ID=567890
export OPENADAPT_DOCS_ACTOR_ID=678901
export OPENADAPT_DOCS_INSTALLATION_ID=789012
uv run python scripts/manage_github_protection.py plan \
  --output /tmp/openadapt-github-protection-plan.json
```

The GitHub CLI token needs repository read access and organization installation
read access for the plan. It needs repository administration write access for
an apply operation. The tool checks all App identities, exact installation
permissions and scopes, repository identity variables, and the environment
reviewer ID against GitHub.

Inspect the plan. Resolve every refusal. Wait until all pull request checks are
complete. Then create a new plan. A plan expires after 15 minutes.

Apply that exact plan:

```bash
uv run python scripts/manage_github_protection.py apply \
  --plan /tmp/openadapt-github-protection-plan.json \
  --confirm "APPLY OpenAdaptAI CORE PROTECTION"
```

The apply operation checks every `main` commit again. It refuses a changed
commit, a changed action list, an active pull request check, a missing release
identity, a missing lifecycle identity, an unguarded dispatch workflow, or an
invalid workflow contract. It also refuses a missing docs identity.

The tool does not remove an extra environment deployment policy by default.
Inspect the planned deletion. Then add `--prune-environment-policies` if the
extra policy is not valid.

Verify the live result:

```bash
uv run python scripts/manage_github_protection.py verify \
  --output /tmp/openadapt-github-protection-verify.json
```

## Private repository plan limit

`openadapt-cloud` stays audit-only. The present organization plan cannot use
GitHub artifact attestations for a private repository. GitHub requires
Enterprise Cloud for that feature in a private repository. See the
[artifact attestation plan requirements](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

Keep the existing signed Ed25519 evidence envelope and the public verifier.
Do not claim GitHub private-repository attestation. Reassess this limit after a
move to GitHub Enterprise Cloud.
