# Core GitHub protection policy

This directory contains the reviewed target policy for nine public core
repositories. It also contains the public deployment authority for the private
`openadapt-cloud` repository. The tool does not change private Cloud settings.
It does not manage a foreign repository.

The policy has these results:

- All changes to `main` use a pull request.
- No person, administrator, role, team, deploy key, or app can bypass the
  `main` rule.
- One review is necessary. A new push makes an old review invalid. A different
  person must approve the last push. All review threads must be complete.
- Each check in the policy comes from the GitHub Actions integration.
- The branch must be current with `main` before GitHub admits it.
- Only the `openadapt-release` GitHub App can create a release tag.
- The release App selects only the nine public core repositories. It has no
  access to private Cloud.
- A second ruleset prevents all identities, including the release app, from
  changing or deleting that tag.
- A protected environment admits only the exact branch or tag pattern in the
  policy.
- A required reviewer must approve each release environment use.
- The lifecycle environments prevent self-review. The founder reviews a run
  that the separate lifecycle App starts.
- The lifecycle App has no `main` bypass and no Contents permission.
- A separate Cloud checkout App has Contents read on `openadapt-cloud` only.
- A protected public workflow deploys one exact authorized Cloud commit.
- The daily database backup environment admits protected Ops `main` only. It
  has no daily reviewer because the schedule must run without a person.

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

The public GitHub API reported zero repository rulesets in all nine
repositories. GitHub marked these `main` branches as protected: `OpenAdapt`,
`openadapt-agent`, `openadapt-flow`, `openadapt-capture`, `openadapt-evals`,
and `openadapt-web`. It marked `openadapt-desktop`, `openadapt-ops`, and
`.github` as not protected.

The public API did not expose the classic branch protection detail. The local
GitHub CLI tokens were invalid. Therefore, this audit does not claim the exact
classic protection settings for the six protected branches.

Flow, Evals, and Agent had an unprotected `pypi` environment. Capture and
OpenAdapt had no release environment. Desktop had a protected `native-release` environment.
It admitted `desktop-v*` and `ffmpeg-runtime-v8.1.2-r1`. The target policy uses
`desktop-v*` and `ffmpeg-runtime-v*`. It also adds the release identity
environment and the PyPI environment. Agent gets separate `release-identity`,
`pypi`, and `mcp-registry` environments.

The organization did not have an `openadapt-lifecycle` App installation. The
target policy keeps the App ID, bot actor ID, and installation ID unresolved.
The plan and apply operations refuse this state. Do not create a lifecycle
environment until the exact App installation exists.

The organization did not have an `openadapt-cloud-checkout` App installation.
The target policy keeps its App ID and installation ID unresolved. The plan
and apply operations refuse this state. The App installation must select only
`openadapt-cloud`. Its only repository permissions are Contents read and
Metadata read.

Ops `main` had no protection. The existing `production-backup` and
`production-backup-monitor` environments had no protection rule or deployment
branch policy. The policy gives `production-backup` an exact protected-main
policy. Only `.github/workflows/db-backup.yml` can name this environment. The
policy does not change `production-backup-monitor`.

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

The global environment default stays at `prevent_self_review: false`. The six
lifecycle environments set an explicit override to `true`:

- `.github` uses `production-lifecycle-activation` only from
  `.github/workflows/production-lifecycle-activation.yml`.
- `.github` uses `production-cloud-deploy` only from
  `.github/workflows/production-cloud-deploy.yml`.
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

The Cloud deploy workflow is not an admission authority. The lifecycle App
starts `Production Cloud deploy`. Its first job has no private Cloud access and
no production secret access. It creates a closed deployment authorization and
signs the exact canonical bytes with a Sigstore Public Good bundle. It opens a
registry pull request. The founder must merge that pull request. The signed
object has kind `production-cloud-deploy-authorization` and schema
`openadapt.production-cloud-deploy-authorization/v1`.

The authorization binds the exact Cloud source commit, deployment intent,
operation, public workflow run ID, run attempt, authority source commit,
provider idempotency digest, lifecycle policy and ledger state, prior Cloud
admission and revocation, prior registry head and revision, issue time, and
expiry. Its maximum life is one hour from the Sigstore Rekor time. A rerun has
a different run attempt and needs a new authorization. The authorization does
not contain a mutable `consumed` flag.

The protected job waits for the authorization merge and the founder environment
approval. Before it gets a checkout token or uses a production secret, it
verifies that the authorization and bundle are in the exact current protected
Profile `main` registry. It also verifies the direct registry lineage, exact
run and attempt, source and intent, bound provider idempotency digest, current
lifecycle ledger, Sigstore issuer and subject, workflow source commit, and
unchanged workflow bytes. A `default_change` needs an inactive Cloud target. A
`same_default_redeploy` needs the exact active source and deployment digests.

The lifecycle ledger input uses the digest of the exact stored ledger bytes.
The ledger-head digest is not the last admission and is not zero for an empty
ledger. It is the domain-separated digest of the exact schema version, policy
digest, and full admissions list. The domain is
`OpenAdapt production lifecycle ledger head v1\0`. The protected job compares
this value to `ledger_head_sha256` in the ledger.

The workflow then gets a short-lived checkout token from
`openadapt-cloud-checkout`. The token has Contents read on Cloud only. It checks
out the exact 40-character commit and does not retain credentials.

The public workflow builds and deploys that exact commit. It dispatches the
provider one time with the bound idempotency digest. It does not upload private
source or a private bundle to a public artifact. It verifies the production
secret source proof, immutable provider deployment digest, live readiness, and
live target attestation. It writes a separate signed result with schema
`openadapt.production-cloud-deployment-result/v1`. The result records one
dispatch, zero blind retries, zero replay dispatches, and either a verified
active provider or uncertain delivery that needs reconciliation. It never
blindly retries uncertain delivery.

The result is privacy-safe. A separate registry pull request carries it and its
Sigstore bundle. The result does not create Production. After verification, the
normal lifecycle activation creates a reviewable active Cloud admission. That
admission binds the actual deployment release ID, deployment digest, manifest
digest, and signed current-default source and provider projection. An admission
cannot authorize or replay a deployment.

The policy refuses apply if a private Cloud workflow can deploy, if the old
private deploy workflow remains, or if a named production deployment secret
remains in the private repository or one of its environments. The policy also
refuses `actions/upload-artifact`, a write checkout token, retained checkout
credentials, secret dumps, and direct `main` checkout in the public workflow.

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

The Production lifecycle feed uses a separate inactive App contract. Its slug,
bot login, App ID, actor ID, and installation ID are empty or zero. The plan
refuses this state. Do not reuse `openadapt-lifecycle`, because that App has no
Contents permission. The future feed App selects `.github` only. It has Contents
write and Metadata read. It can act only through
`.github/workflows/production-lifecycle-ref.yml`.

The feed ruleset targets `refs/heads/production-lifecycle-feed`. It has no
bypass. It prohibits deletion and non-fast-forward updates. It also requires
linear history. The update workflow must use the repository-ID API. It must
read and match the exact old commit, send `force: false`, and read the exact
postcondition. A person, administrator, or general workflow token must not
update this ref. This PR records the inactive contract only. It does not create
the App, ref, or ruleset.

Actions write also permits the App to cancel or rerun workflow runs and delete
workflow artifacts. The exact repository scope limits this authority. The
policy inventories every workflow that accepts `workflow_dispatch` or
`repository_dispatch` in the three repositories. Only the six lifecycle
workflows can accept the lifecycle App actor. Each other manual path needs a
`reject-lifecycle-app` predecessor with no permission. It checks both
`github.actor` and `github.triggering_actor`. Each later job depends on that
predecessor and repeats both identity refusals before GitHub allocates a job.
A new or unguarded path blocks apply.

Each lifecycle dispatch path uses a workflow-and-event-specific concurrency
group. It sets `cancel-in-progress` to `false`. A manual run cannot cancel a
real run. The database backup uses one `production-db-backup` group for both
schedule and manual events. This prevents two backup effects at the same time.
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

Agent uses a third publication environment named `mcp-registry`. The tag job
publishes the Python package through PyPI OIDC. A later job publishes
`server.json` through MCP registry OIDC. The workflow verifies the two
registries and writes an unadmitted lifecycle candidate. It cannot use a PyPI
token, an MCP personal token, or an unpinned latest publisher download.

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
export OPENADAPT_CLOUD_CHECKOUT_APP_ID=890123
export OPENADAPT_CLOUD_CHECKOUT_INSTALLATION_ID=901234
export OPENADAPT_LIFECYCLE_REF_APP_SLUG="REQUIRED_FOUNDER_REVIEWED_SLUG"
export OPENADAPT_LIFECYCLE_REF_ACTOR_LOGIN="REQUIRED_FOUNDER_REVIEWED_BOT_LOGIN"
export OPENADAPT_LIFECYCLE_REF_APP_ID="REQUIRED_FOUNDER_REVIEWED_APP_ID"
export OPENADAPT_LIFECYCLE_REF_ACTOR_ID="REQUIRED_FOUNDER_REVIEWED_ACTOR_ID"
export OPENADAPT_LIFECYCLE_REF_INSTALLATION_ID="REQUIRED_FOUNDER_REVIEWED_INSTALLATION_ID"
uv run python scripts/manage_github_protection.py plan \
  --output /tmp/openadapt-github-protection-plan.json
```

The GitHub CLI token needs repository read access and organization installation
read access for the plan. It needs repository administration write access for
an apply operation. The tool checks all App identities, exact installation
permissions and scopes, repository identity variables, and the environment
reviewer ID against GitHub.

Inspect the plan. Resolve every refusal. Merge or close each managed pull
request. Wait until all pull request checks are complete. Then create a new
plan. A plan expires after 15 minutes.

Apply that exact plan:

```bash
uv run python scripts/manage_github_protection.py apply \
  --plan /tmp/openadapt-github-protection-plan.json \
  --confirm "APPLY OpenAdaptAI CORE PROTECTION"
```

The apply operation checks every `main` commit again. It refuses a changed
commit, a changed action list, an active pull request check, a missing release
identity, a missing lifecycle identity, an unguarded dispatch workflow, or an
invalid workflow contract. It also refuses a missing docs identity, a missing
Cloud checkout identity, an unsafe private Cloud workflow, or a private Cloud
production deployment secret.

The tool does not remove an extra environment deployment policy by default.
Inspect the planned deletion. Then add `--prune-environment-policies` if the
extra policy is not valid.

Verify the live result:

```bash
uv run python scripts/manage_github_protection.py verify \
  --output /tmp/openadapt-github-protection-verify.json
```

## Database backup inventory

The read-only AWS inventory used `AWS_PROFILE=openadapt`. AWS returned account
`992382684924` and IAM user `claude-ops`. The account has no backup role. It has
one matching S3 bucket named `openadapt-procdoc`. That bucket has public access
blocked and AES-256 server-side encryption. It has no lifecycle policy. Its
name and configuration do not identify it as a database backup target. Do not
reuse it for this purpose.

The target needs a new least-privilege OIDC backup role and a private S3 bucket
in `us-east-1`. The bucket needs public access block, encryption, exact-account
write policy, and 90-day expiration. [AWS IAM](https://aws.amazon.com/iam/faqs/)
has no additional charge. An S3 bucket has no minimum charge. Storage, requests,
and transfer determine the cost. At the current
[S3 Standard rate](https://aws.amazon.com/s3/pricing/) of USD 0.023 per GB-month,
90 daily copies cost approximately USD 2.07 per source GB each month at steady state.
For example, a 10 GB daily backup set costs approximately USD 20.70 each month,
plus small request charges. Actual compressed database size determines the
cost.

The live `production-backup` environment has no variables and no secrets. It
needs `AWS_BACKUP_ROLE_ARN`, `AWS_BACKUP_BUCKET`, `SUPABASE_DB_URL`, and
`SUPABASE_PROJECT_REF`. The private Cloud `production` environment already has
a secret named `SUPABASE_PROJECT_REF`. A local customer-controlled
`openadapt-cloud/.env.deploy` file also has that name. Do not print or copy its
value during a policy review. No inspected GitHub setting or local deploy file
has `SUPABASE_DB_URL`. Get the production connection string from the exact
Supabase project through an approved secret-transfer step. Do not derive it
from a public project URL.

## Private Cloud plan boundary

GitHub Free cannot protect private Cloud `main` or its deployment environment.
The public Profile authority supplies the missing protection. The policy tool
manages only public rules and environments. It uses read-only Cloud API calls
to bind current Cloud `main`, scan all private workflow files, and list secret
names. It never changes private Cloud settings.

The public authority exposes workflow code and privacy-safe receipt digests.
It does not expose Cloud source, build bundles, provider configuration, secret
values, or live customer data. The tradeoff is a sensitive bridge: a public
runner executes an exact private commit with protected deployment secrets.
The one-use authorization, founder environment review, read-only checkout App,
exact-commit checkout, no-artifact rule, immutable deployment proof, and live
readiness proof limit this bridge. A dedicated external executor would reduce
public-runner trust, but it would add another production service and secret
boundary. The public authority is the smallest complete control for the
current GitHub plan.
