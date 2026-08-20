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

## Required check selection

The policy requires only a check that starts on every pull request. GitHub can
leave a path-filtered required workflow in a pending state when its paths do
not match. Such a workflow can then stop an unrelated pull request.

The policy records a path-scoped check in `path_scoped_checks`. It does not make
that check a global requirement. The target policy does require
`build-and-e2e` in `openadapt-web` and `validate-profile` in `.github`. The tool
refuses an apply while either workflow has pull request path filters. Keep each
exact check name. Use a cheap internal path classifier when the expensive work
does not apply.

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
uv run python scripts/manage_github_protection.py plan \
  --output /tmp/openadapt-github-protection-plan.json
```

The GitHub CLI token needs repository read access and organization installation
read access for the plan. It needs repository administration write access for
an apply operation. The tool checks the app ID, installation scope, and the
environment reviewer ID against GitHub.

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
identity, or an invalid workflow contract.

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
