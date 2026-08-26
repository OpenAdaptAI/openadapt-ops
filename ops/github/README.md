# Core GitHub protection policy

This directory contains the reviewed target policy for nine public core
repositories. It doesn't manage `openadapt-cloud` or a foreign repository.

The policy has these results:

- All changes to `main` use a pull request.
- No person, administrator, role, team, deploy key, or app can bypass the
  `main` rule.
- One review is necessary. A new push makes an old review invalid. A different
  person must approve the last push. All review threads must be complete.
- Each check in the policy comes from the GitHub Actions integration.
- The branch must be current with `main` before GitHub admits it.
- Only the `openadapt-release` GitHub App can create a release tag and its
  matching GitHub Release.
- The release App selects only the six public package repositories. It has
  Contents write and Metadata read. It can't open pull requests and has no
  access to private Cloud.
- A second ruleset prevents all identities, including the release app, from
  changing or deleting that tag.
- A protected environment admits only the exact branch or tag pattern in the
  policy.
- A required reviewer must approve each release environment use.
- Administrators can't bypass any managed environment. GitHub exposes this
  control in the environment settings page, but not in the REST update API.
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

## Read-only audit on 2026-08-26

The public GitHub API reported zero repository rulesets in all nine
repositories. GitHub marked these `main` branches as protected: `OpenAdapt`,
`openadapt-agent`, `openadapt-flow`, `openadapt-capture`, `openadapt-evals`,
and `openadapt-web`. It marked `openadapt-desktop`, `openadapt-ops`, and
`.github` as not protected.

An authenticated read returned the exact classic protection settings. Flow has
thirteen strict required checks but no review rule. Capture has four strict
checks. Evals has one non-strict check and permits force pushes. OpenAdapt,
Agent, Capture, and Web require zero approvals and don't enforce administrators.

Agent and Flow had an unprotected `pypi` environment. Evals had unprotected
`pypi` and `testpypi` environments. Capture and OpenAdapt had no package release
environment. Desktop had a protected `native-release` environment.
It admitted `desktop-v*` and `ffmpeg-runtime-v8.1.2-r1`. The target policy uses
`desktop-v*` and `ffmpeg-runtime-v*`. It also adds the release identity
environment and the PyPI environment. Agent also gets a separate
`mcp-registry` environment. The tool doesn't change the Ops backup environments.

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
workflows can accept the lifecycle App actor. Only the Docs sync job can accept
the Docs App actor. Each other manual path needs a `reject-lifecycle-app`
predecessor with no permission. Despite its historical name, that predecessor
rejects both `openadapt-lifecycle[bot]` and `openadapt-docs[bot]`. It checks
`github.actor` and `github.triggering_actor` for each App. Each later job
depends on that predecessor and repeats all four identity refusals before
GitHub allocates a job. A new or unguarded path blocks apply.

The workflow audit parses YAML. It recognizes mapping, scalar, and flow-list
trigger forms, including `workflow_dispatch: {}` and `repository_dispatch`.
Malformed YAML blocks the plan. For an authorized lifecycle or Docs path, the
audit checks the actor, protected environment, App inputs, token output, and
sensitive effect in the same job. A matching string elsewhere in the file
isn't enough.

Each App-token step names `OpenAdaptAI` and the exact repositories that its job
needs. A Release token names only its current package repository. A lifecycle
or Docs token names only its reviewed workflow scope. An omitted repository
list would grant the token its full installation scope, so the plan refuses it.

Each dispatch path uses a workflow-and-event-specific concurrency group. It
sets `cancel-in-progress` to `false`. A manual run cannot cancel a real run.
Production evidence remains content-addressed outside mutable Actions
artifacts.

## Release sequence

The plan also checks the runtime configuration for each App. Every package
repository needs an `OPENADAPT_RELEASE_APP_ID` variable with the reviewed App
ID. A private key must not exist as a repository secret or a repository
variable. It can exist only as an environment secret in an exact binding. For
the Release App, Launcher uses `release-identity` and `pypi`; Agent uses
`release-identity`; Capture, Evals, and Flow use `release-identity` and `pypi`;
Desktop uses `release-identity`, `pypi`, and `native-release`. For the
Lifecycle App, Profile uses its three lifecycle environments; Evals uses
`production-lifecycle-evidence`; Ops uses `production-lifecycle-projection`.
For the Docs App, Ops uses `production-docs-deploy`.

Evals does not hold the Docs App key. The target Evals dispatcher does not use
that identity. Ops owns the protected Docs sync job.

The plan reads secret and variable metadata from every repository environment.
It never requests a secret value. A missing key, an extra environment copy, or
a variable that shadows a private-key name blocks apply.

Every managed environment sets `can_admins_bypass` to `false`. If an
environment is absent, the field is missing, or GitHub reports `true`, the plan
does not offer a REST repair. Open the repository's **Settings > Environments**
page, create the named environment if needed, and clear **Allow administrators
to bypass configured protection rules**. Run a new plan after that one-time UI
change.

Use this sequence for each package repository:

1. A maintainer merges the reviewed version, changelog, lock, and candidate
   files through the normal `main` rules.
2. A manual run from that exact current `main` commit enters
   `release-identity`.
3. The workflow gets a short-lived `openadapt-release` App token.
4. The App creates one annotated release tag. It can't push a branch or open a
   pull request.
5. The tag run checks the original App actor and the exact protected-main
   commit before publication.
6. The publication job enters `pypi`, `mcp-registry`, or `native-release` and
   uses OIDC to publish the checked bytes.

Any job that creates, edits, or uploads a GitHub Release must create the
Release App token in that job. Its `GH_TOKEN` must reference that exact step's
output. The same job rule prevents a workflow from passing because an unrelated
job contains the right App strings. Evals and every other package follow the
same matching GitHub Release rule.

A tag push must use the App token through an authenticated checkout credential
or an explicit authenticated Git binding in the push step. An unused token
variable doesn't authorize a push.

Agent uses `mcp-registry` after its PyPI publication. Both publication jobs use
OIDC. The Agent release workflow can't accept an API-token fallback or
download an unpinned registry publisher.

A person with repository write access can rerun the exact tag workflow for
recovery. [GitHub keeps the original actor, ref, and commit on a
rerun](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).
The workflow refuses a different tag or artifact identity.

An event from `GITHUB_TOKEN` does not normally start another workflow. GitHub
documents this behavior in the [GITHUB_TOKEN reference](https://docs.github.com/en/actions/concepts/security/github_token).
Use the release App token only for the annotated tag and matching GitHub
Release. Never use it to push a branch or open a pull request.

A package release workflow that still refers to `ADMIN_TOKEN`, or that skips a
required protected environment, remains a plan refusal. Migrate every such
workflow before an apply operation.

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
permissions and scopes, repository identity variables, environment secret and
variable names, administrator-bypass state, and the environment reviewer ID
against GitHub.

Inspect the plan. Resolve every refusal. Wait until all pull request checks are
complete. If an audited `main` SHA changed, review the exact current workflows
and update the policy SHA before you create another plan. Drift is a refusal,
not a warning. A plan expires after 15 minutes.

The audit reads each workflow and complete workflow tree by that recorded
commit SHA. It reads the branch again after those checks. A branch change
during the audit refuses the plan.

Apply that exact plan:

```bash
uv run python scripts/manage_github_protection.py apply \
  --plan /tmp/openadapt-github-protection-plan.json \
  --confirm "APPLY OpenAdaptAI CORE PROTECTION"
```

The apply operation checks every `main` commit again immediately before the
first mutation. It refuses a changed commit, a changed action list, an active
pull request check, a missing release identity, a missing lifecycle identity,
an unguarded dispatch workflow, or an invalid workflow contract. It also
refuses a missing docs identity.

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
