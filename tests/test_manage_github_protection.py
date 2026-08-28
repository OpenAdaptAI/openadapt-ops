from __future__ import annotations

import base64
import json
import pathlib
import sys
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from manage_github_protection import (
    GhApiClient,
    GitHubError,
    PolicyError,
    ReleaseActor,
    _apply_actions,
    build_plan,
    desired_environment,
    desired_rulesets,
    load_config,
    validate_config,
    validate_plan_for_apply,
)

CONFIG_PATH = REPO_ROOT / "ops/github/core-protection-policy.json"


class ReadOnlyFixtureGitHub:
    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        active_repo: str | None = None,
        open_repo: str | None = None,
        release_app_permissions_mismatch: bool = False,
        path_filtered_repo: str | None = None,
        missing_lifecycle_app: bool = False,
        missing_docs_app: bool = False,
        missing_cloud_checkout_app: bool = False,
        unsafe_private_cloud: bool = False,
        private_cloud_production_secret: bool = False,
        misordered_cloud_authorization: bool = False,
        extra_dispatch_repo: str | None = None,
        unguarded_dispatch_repo: str | None = None,
        unauthorized_environment_repo: str | None = None,
        cancelling_dispatch_repo: str | None = None,
        unprotected_environment_repo: str | None = None,
    ) -> None:
        self.config = config
        self.active_repo = active_repo
        self.open_repo = open_repo
        self.release_app_permissions_mismatch = release_app_permissions_mismatch
        self.path_filtered_repo = path_filtered_repo
        self.missing_lifecycle_app = missing_lifecycle_app
        self.missing_docs_app = missing_docs_app
        self.missing_cloud_checkout_app = missing_cloud_checkout_app
        self.unsafe_private_cloud = unsafe_private_cloud
        self.private_cloud_production_secret = private_cloud_production_secret
        self.misordered_cloud_authorization = misordered_cloud_authorization
        self.extra_dispatch_repo = extra_dispatch_repo
        self.unguarded_dispatch_repo = unguarded_dispatch_repo
        self.unauthorized_environment_repo = unauthorized_environment_repo
        self.cancelling_dispatch_repo = cancelling_dispatch_repo
        self.unprotected_environment_repo = unprotected_environment_repo
        self.writes: list[tuple[str, str, Mapping[str, Any]]] = []
        self.by_name = {repo["name"]: repo for repo in config["repositories"]}

    def get(self, path: str, *, optional: bool = False) -> Any:
        if path == "/apps/openadapt-release":
            return {"id": 991122, "slug": "openadapt-release"}
        if path == "/apps/openadapt-lifecycle":
            if self.missing_lifecycle_app:
                return None
            return {"id": 771100, "slug": "openadapt-lifecycle"}
        if path == "/apps/openadapt-docs":
            if self.missing_docs_app:
                return None
            return {"id": 772200, "slug": "openadapt-docs"}
        if path == "/apps/openadapt-cloud-checkout":
            if self.missing_cloud_checkout_app:
                return None
            return {"id": 773300, "slug": "openadapt-cloud-checkout"}
        if path == "/apps/test-lifecycle-ref":
            return {"id": 774400, "slug": "test-lifecycle-ref"}
        if path == "/users/openadapt-lifecycle%5Bbot%5D":
            return {"id": 881100, "login": "openadapt-lifecycle[bot]"}
        if path == "/users/openadapt-docs%5Bbot%5D":
            return {"id": 882200, "login": "openadapt-docs[bot]"}
        if path == "/users/test-lifecycle-ref%5Bbot%5D":
            return {"id": 884400, "login": "test-lifecycle-ref[bot]"}
        if path == "/users/abrichr":
            return {"id": 774615, "login": "abrichr"}
        if path == "/orgs/OpenAdaptAI/installations?per_page=100":
            return {
                "installations": [
                    {
                        "id": 551100,
                        "app_id": 991122,
                        "app_slug": "openadapt-release",
                        "repository_selection": "selected",
                        "permissions": (
                            {"contents": "write", "metadata": "read"}
                            if self.release_app_permissions_mismatch
                            else {
                                "contents": "write",
                                "metadata": "read",
                                "pull_requests": "write",
                            }
                        ),
                    },
                    {
                        "id": 661100,
                        "app_id": 771100,
                        "app_slug": "openadapt-lifecycle",
                        "repository_selection": "selected",
                        "permissions": {
                            "actions": "write",
                            "metadata": "read",
                            "pull_requests": "write",
                        },
                    },
                    {
                        "id": 761100,
                        "app_id": 772200,
                        "app_slug": "openadapt-docs",
                        "repository_selection": "selected",
                        "permissions": {
                            "actions": "write",
                            "metadata": "read",
                            "pull_requests": "write",
                        },
                    },
                    {
                        "id": 861100,
                        "app_id": 773300,
                        "app_slug": "openadapt-cloud-checkout",
                        "repository_selection": "selected",
                        "permissions": {
                            "contents": "read",
                            "metadata": "read",
                        },
                    },
                    {
                        "id": 864400,
                        "app_id": 774400,
                        "app_slug": "test-lifecycle-ref",
                        "repository_selection": "selected",
                        "permissions": {
                            "contents": "write",
                            "metadata": "read",
                        },
                    },
                ]
            }
        if path == "/user/installations/661100/repositories?per_page=100":
            return {
                "repositories": [
                    {"name": ".github"},
                    {"name": "openadapt-evals"},
                    {"name": "openadapt-ops"},
                ]
            }
        if path == "/user/installations/551100/repositories?per_page=100":
            return {"repositories": [{"name": name} for name in sorted(self.by_name)]}
        if path == "/user/installations/761100/repositories?per_page=100":
            return {"repositories": [{"name": "openadapt-ops"}]}
        if path == "/user/installations/861100/repositories?per_page=100":
            return {"repositories": [{"name": "openadapt-cloud"}]}
        if path == "/user/installations/864400/repositories?per_page=100":
            return {"repositories": [{"name": ".github"}]}
        if (
            path
            == "/repositories/1300570990/environments/production/secrets?per_page=100"
        ):
            secrets = (
                [{"name": "SUPABASE_ACCESS_TOKEN"}]
                if self.private_cloud_production_secret
                else []
            )
            return {"total_count": len(secrets), "secrets": secrets}
        parts = path.split("?")[0].split("/")
        if len(parts) >= 4 and parts[1] == "repos":
            name = parts[3]
            if name == "openadapt-cloud":
                if len(parts) == 4:
                    return {
                        "id": 1300570990,
                        "full_name": "OpenAdaptAI/openadapt-cloud",
                        "private": True,
                        "default_branch": "main",
                    }
                if parts[4] == "commits":
                    return {
                        "sha": self.config["private_cloud_authority"][
                            "audited_main_sha"
                        ]
                    }
                if parts[4:6] == ["git", "trees"]:
                    workflows = [".github/workflows/ci.yml"]
                    if self.unsafe_private_cloud:
                        workflows.append(".github/workflows/deploy.yml")
                    return {
                        "truncated": False,
                        "tree": [{"path": item, "type": "blob"} for item in workflows],
                    }
                if parts[4] == "contents":
                    workflow_path = "/".join(parts[5:])
                    workflow = (
                        "on:\n  workflow_dispatch:\njobs:\n  deploy:\n"
                        "    steps:\n      - run: node scripts/deploy.mjs\n"
                        if workflow_path == ".github/workflows/deploy.yml"
                        else "on:\n  pull_request:\njobs:\n  test:\n    steps:\n      - run: true\n"
                    )
                    return {
                        "type": "file",
                        "content": base64.b64encode(workflow.encode()).decode(),
                    }
                if parts[4:6] == ["actions", "secrets"]:
                    return {"total_count": 0, "secrets": []}
                if parts[4] == "environments":
                    return {"environments": [{"name": "production"}]}
                raise AssertionError(f"unexpected private Cloud GET {path}")
            repo = self.by_name[name]
            if len(parts) == 4:
                return {
                    "full_name": f"OpenAdaptAI/{name}",
                    "private": False,
                    "default_branch": "main",
                }
            if parts[4] == "commits" and parts[5] == "main":
                return {"sha": repo["audited_main_sha"]}
            if parts[4] == "commits" and parts[-1] == "check-runs":
                if name == self.active_repo:
                    return {
                        "check_runs": [
                            {
                                "name": "test",
                                "status": "in_progress",
                                "conclusion": None,
                            }
                        ]
                    }
                return {"check_runs": []}
            if parts[4] == "pulls":
                if name in {self.active_repo, self.open_repo}:
                    return [
                        {
                            "number": 12,
                            "draft": False,
                            "head": {"sha": "f" * 40},
                        }
                    ]
                return []
            if parts[4] == "rulesets":
                return []
            if parts[4] == "environments":
                if name == self.unprotected_environment_repo:
                    return {
                        "protection_rules": [],
                        "deployment_branch_policy": None,
                    }
                return None
            if parts[4:6] == ["actions", "variables"]:
                variable = parts[6]
                values = {
                    "OPENADAPT_LIFECYCLE_APP_ID": "771100",
                    "OPENADAPT_LIFECYCLE_ACTOR_ID": "881100",
                    "OPENADAPT_LIFECYCLE_INSTALLATION_ID": "661100",
                    "OPENADAPT_DOCS_APP_ID": "772200",
                    "OPENADAPT_DOCS_ACTOR_ID": "882200",
                    "OPENADAPT_DOCS_INSTALLATION_ID": "761100",
                    "OPENADAPT_CLOUD_CHECKOUT_APP_ID": "773300",
                    "OPENADAPT_CLOUD_CHECKOUT_INSTALLATION_ID": "861100",
                    "OPENADAPT_LIFECYCLE_REF_APP_ID": "774400",
                    "OPENADAPT_LIFECYCLE_REF_ACTOR_ID": "884400",
                    "OPENADAPT_LIFECYCLE_REF_INSTALLATION_ID": "864400",
                }
                return {"name": variable, "value": values[variable]}
            if parts[4:6] == ["git", "trees"]:
                configured = set()
                for field in (
                    "release_workflows",
                    "admission_workflows",
                    "lifecycle_workflows",
                    "operational_workflows",
                    "dispatch_workflow_inventory",
                ):
                    configured.update(item["path"] for item in repo.get(field, []))
                if name == self.extra_dispatch_repo:
                    configured.add(".github/workflows/uninventoried.yml")
                if name == self.unauthorized_environment_repo:
                    configured.add(".github/workflows/unauthorized.yml")
                return {
                    "truncated": False,
                    "tree": [
                        {"path": item, "type": "blob"} for item in sorted(configured)
                    ],
                }
            if parts[4] == "contents":
                workflow_path = "/".join(parts[5:])
                workflow = self._workflow_content(name, workflow_path)
                return {
                    "type": "file",
                    "content": base64.b64encode(workflow.encode()).decode(),
                }
        raise AssertionError(f"unexpected GET {path}")

    def _workflow_content(self, repo_name: str, path: str) -> str:
        repo = self.by_name[repo_name]
        if repo_name == "openadapt-agent" and path == ".github/workflows/release.yml":
            return (
                "name: Release\n"
                "on:\n  push:\n    tags: ['v*']\n  workflow_dispatch:\n"
                "permissions:\n  contents: read\n"
                "jobs:\n"
                "  create-tag:\n"
                "    environment: release-identity\n"
                "    steps:\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          permission-contents: write\n"
                "      - run: git tag v2.0.3 && git push origin v2.0.3\n"
                "  pypi:\n"
                "    environment: pypi\n"
                "    permissions:\n      id-token: write\n"
                "    steps:\n"
                "      - uses: pypa/gh-action-pypi-publish@deadbeef\n"
                "      - run: python scripts/check_release_artifacts.py dist && "
                "python scripts/check_source_boundary.py --require-dist\n"
                "  mcp:\n"
                "    environment: mcp-registry\n"
                "    permissions:\n      id-token: write\n"
                "    steps:\n"
                "      - run: ./mcp-publisher login github-oidc\n"
                "  parity:\n"
                "    steps:\n"
                "      - run: python scripts/verify_release_registries.py --output "
                "release-metadata/production-admission-candidate.json\n"
            )
        if repo_name == "openadapt-ops" and path == ".github/workflows/db-backup.yml":
            return (
                "name: Production DB logical backup\n"
                "on:\n  workflow_dispatch:\n  schedule:\n    - cron: '23 7 * * *'\n"
                "concurrency:\n  group: production-db-backup\n  cancel-in-progress: false\n"
                "jobs:\n"
                "  reject-lifecycle-app:\n"
                "    permissions: {}\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: test '${{ github.actor }}' != 'openadapt-lifecycle[bot]' "
                "-a '${{ github.triggering_actor }}' != 'openadapt-lifecycle[bot]'\n"
                "  dump:\n"
                "    needs: reject-lifecycle-app\n"
                "    if: github.actor != 'openadapt-lifecycle[bot]' && "
                "github.triggering_actor != 'openadapt-lifecycle[bot]'\n"
                "    runs-on:\n      group: production-backup\n      labels: self-hosted\n"
                "    environment: production-backup\n"
                "    permissions:\n      id-token: write\n"
                "    env:\n"
                "      BACKUP_ROLE_ARN: ${{ vars.AWS_BACKUP_ROLE_ARN }}\n"
                "      BACKUP_BUCKET: ${{ vars.AWS_BACKUP_BUCKET }}\n"
                "      SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}\n"
                "      SUPABASE_PROJECT_REF: ${{ secrets.SUPABASE_PROJECT_REF }}\n"
                "      GITHUB_REF_PROTECTED: ${{ github.ref_protected }}\n"
                "    steps:\n"
                "      - run: test '${GITHUB_REF}' = refs/heads/main\n"
                "      - run: python scripts/check_github_environment_gate.py\n"
                "      - uses: aws-actions/configure-aws-credentials@deadbeef\n"
                "        with:\n"
                "          role-to-assume: ${{ env.BACKUP_ROLE_ARN }}\n"
                "          allowed-account-ids: '992382684924'\n"
                "      - run: scripts/check_live_database_backup_target.sh && "
                "aws s3 cp x s3://x --expected-bucket-owner 992382684924\n"
            )
        if (
            repo_name == ".github"
            and path == ".github/workflows/production-cloud-deploy.yml"
        ):
            workflow = (
                "name: Production Cloud deploy\n"
                "on:\n  workflow_dispatch:\n    inputs:\n"
                "      source_commit:\n"
                "      deployment_intent_id:\n"
                "      provider_idempotency_key:\n"
                "      operation:\n"
                "      expected_lifecycle_ledger_head_sha256:\n"
                "      expected_lifecycle_ledger_sha256:\n"
                "      expected_registry_head_sha256:\n"
                "      expected_registry_revision:\n"
                "permissions:\n  attestations: write\n  id-token: write\n  contents: read\n"
                "concurrency:\n  group: ${{ github.workflow }}-${{ github.event_name }}\n"
                "  cancel-in-progress: false\n"
                "jobs:\n  deploy:\n"
                "    if: github.repository == 'OpenAdaptAI/.github' && "
                "github.ref == 'refs/heads/main' && "
                "github.event_name == 'workflow_dispatch' && "
                "github.actor == 'openadapt-lifecycle[bot]' && "
                "github.triggering_actor == 'openadapt-lifecycle[bot]' && "
                "github.actor_id == vars.OPENADAPT_LIFECYCLE_ACTOR_ID\n"
                "    environment: production-cloud-deploy\n"
                "    steps:\n"
                "      - run: echo 'openadapt.production-cloud-deploy-authorization/v1 "
                "production-cloud-deploy-authorization "
                "openadapt.production-cloud-deploy-authorization-sigstore-bundle/v1 "
                "production-cloud-deploy-authorization-sigstore-bundle "
                "OpenAdapt production cloud deploy authorization v1\\0 "
                "openadapt.production-cloud-deployment-registry/v1 "
                "openadapt.production-cloud-deployment-registry-entry/v1 "
                "OpenAdapt production cloud deployment registry v1\\0 "
                "production-cloud-deployment-registry.json "
                "authorization_id deployment_intent_id source_commit "
                "authority_source_commit deploy_workflow_run_id "
                "deploy_workflow_run_attempt provider_idempotency_key "
                "lifecycle_policy_sha256 lifecycle_ledger_sha256 "
                "lifecycle_ledger_head_sha256 "
                "OpenAdapt production lifecycle ledger head v1\\0 "
                "prior_admission_sha256 "
                "prior_revocation_sha256 prior_registry_head_sha256 "
                "prior_registry_revision issued_at expires_at target cloud "
                "default_change same_default_redeploy ${{ github.run_id }} "
                "${{ github.run_attempt }} ${{ inputs.source_commit }} "
                "${{ inputs.deployment_intent_id }} "
                "${{ inputs.provider_idempotency_key }} ${{ inputs.operation }} "
                "${{ inputs.expected_lifecycle_ledger_head_sha256 }} "
                "${{ inputs.expected_lifecycle_ledger_sha256 }} "
                "${{ inputs.expected_registry_head_sha256 }} "
                "${{ inputs.expected_registry_revision }} sigstore "
                "https://github.com/OpenAdaptAI/.github/.github/workflows/"
                "production-cloud-deploy.yml@refs/heads/main "
                "repo:OpenAdaptAI/.github:ref:refs/heads/main "
                "token.actions.githubusercontent.com github.ref_protected'\n"
                "      - run: sigstore sign authorization && "
                "actions/attest authorization\n"
                "      - run: gh pr create --title authorization\n"
                "      - run: scripts/verify-deployment-authorization-registry.mjs\n"
                "      - id: token\n        uses: actions/create-github-app-token@deadbeef\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_CLOUD_CHECKOUT_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_CLOUD_CHECKOUT_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-cloud\n"
                "          permission-contents: read\n"
                "      - uses: actions/checkout@deadbeef\n"
                "        with:\n"
                "          repository: OpenAdaptAI/openadapt-cloud\n"
                "          ref: ${{ inputs.source_commit }}\n"
                "          token: ${{ steps.token.outputs.token }}\n"
                "          persist-credentials: false\n"
                "      - run: npm run build && scripts/write-deployment-manifest.mjs\n"
                "      - run: scripts/deploy.mjs && curl "
                "https://app.openadapt.ai/api/internal/production-secret-source-proof\n"
                "      - run: curl https://app.openadapt.ai/api/health/ready\n"
                "      - run: curl https://app.openadapt.ai/api/internal/"
                "execute-acceptance/target/attestation\n"
                "      - run: echo 'openadapt.production-cloud-deployment-result/v1 "
                "production-cloud-deployment-result "
                "openadapt.production-cloud-deployment-result-sigstore-bundle/v1 "
                "production-cloud-deployment-result-sigstore-bundle "
                "OpenAdapt production cloud deployment result v1\\0 "
                "authorization_registry_source_commit dispatch_count "
                "delivery_status provider_active provider_effect_commitment_sha256 "
                "blind_retry_count replay_dispatch_count reconciliation_required "
                "dispatched_at verified_at "
                "repo:OpenAdaptAI/.github:environment:production-cloud-deploy'\n"
                "      - uses: actions/attest@deadbeef\n"
                "      - run: gh pr create --title result\n"
                "      - run: gh workflow run production-lifecycle-activation.yml\n"
            )
            if self.misordered_cloud_authorization:
                workflow = workflow.replace(
                    "      - run: scripts/verify-deployment-authorization-registry.mjs\n",
                    "",
                ).replace(
                    "      - uses: actions/checkout@deadbeef\n",
                    "      - run: scripts/verify-deployment-authorization-registry.mjs\n"
                    "      - uses: actions/checkout@deadbeef\n",
                    1,
                )
            return workflow
        lifecycle_path = next(
            (
                item["exclusive_workflow"]
                for item in repo.get("lifecycle_environments", [])
                if item["exclusive_workflow"] == path
            ),
            None,
        )
        if lifecycle_path is not None:
            environment = next(
                item["name"]
                for item in repo["lifecycle_environments"]
                if item["exclusive_workflow"] == path
            )
            job_names = {
                ".github/workflows/production-lifecycle-activation.yml": (
                    "activate",
                    "Create Production lifecycle activation PR",
                ),
                ".github/workflows/production-cloud-deploy.yml": (
                    "deploy",
                    "Deploy exact Cloud commit",
                ),
                ".github/workflows/qualification-authority-state.yml": (
                    "update",
                    "Create qualification authority state PR",
                ),
                ".github/workflows/qualification-revocation-state.yml": (
                    "update",
                    "Create qualification revocation state PR",
                ),
                ".github/workflows/production-lifecycle-evidence.yml": (
                    "produce",
                    "Produce Production lifecycle evidence",
                ),
                ".github/workflows/production-lifecycle-projection.yml": (
                    "project",
                    "Project canonical Production lifecycle",
                ),
            }
            job_id, job_name = job_names[path]
            projection_inputs = ""
            projection_conditions = ""
            projection_steps = ""
            if path == ".github/workflows/production-lifecycle-projection.yml":
                projection_inputs = (
                    "    inputs:\n"
                    "      source_event:\n"
                    "      source_repository:\n"
                    "      source_ref:\n"
                    "      source_commit:\n"
                    "      candidate_admissions_sha256:\n"
                    "      candidate_ledger_head_sha256:\n"
                    "      idempotency_key:\n"
                )
                projection_conditions = (
                    " &&\n"
                    "      inputs.source_event == 'production_lifecycle_ledger_changed' &&\n"
                    "      inputs.source_repository == 'OpenAdaptAI/.github' &&\n"
                    "      inputs.source_ref == 'refs/heads/main'\n"
                )
                projection_steps = (
                    "      - run: gh api repos/OpenAdaptAI/.github/commits/main && "
                    "test sha =~ '[0-9a-f]{40}'\n"
                    "      - run: test digests =~ 'sha256:[0-9a-f]{64}'\n"
                    "      - run: echo 'OpenAdapt production lifecycle ledger head v1\\0'\n"
                    "      - run: echo 'OpenAdapt production lifecycle projection idempotency v1\\0'\n"
                    "      - run: echo '${{ inputs.source_commit }} "
                    "${{ inputs.candidate_admissions_sha256 }} "
                    "${{ inputs.candidate_ledger_head_sha256 }} "
                    "${{ inputs.idempotency_key }}'\n"
                )
            return (
                "name: Lifecycle fixture\n"
                "on:\n"
                "  workflow_dispatch:\n"
                f"{projection_inputs}"
                "permissions:\n"
                "  attestations: write\n"
                "  contents: write\n"
                "  id-token: write\n"
                "concurrency:\n"
                "  group: ${{ github.workflow }}-${{ github.event_name }}\n"
                "  cancel-in-progress: false\n"
                "jobs:\n"
                f"  {job_id}:\n"
                f"    name: {job_name}\n"
                "    if: >-\n"
                f"      github.repository == 'OpenAdaptAI/{repo_name}' &&\n"
                "      github.ref == 'refs/heads/main' &&\n"
                "      github.event_name == 'workflow_dispatch' &&\n"
                "      github.actor == 'openadapt-lifecycle[bot]' &&\n"
                "      github.triggering_actor == 'openadapt-lifecycle[bot]' &&\n"
                "      github.actor_id == vars.OPENADAPT_LIFECYCLE_ACTOR_ID"
                f"{projection_conditions}"
                "\n"
                "    environment:\n"
                f"      name: {environment}\n"
                "    steps:\n"
                "      - uses: actions/attest@deadbeef\n"
                f"{projection_steps}"
                "      - run: echo '${{ vars.OPENADAPT_LIFECYCLE_APP_ID }} "
                "${{ vars.OPENADAPT_LIFECYCLE_INSTALLATION_ID }} "
                "${{ secrets.OPENADAPT_LIFECYCLE_APP_PRIVATE_KEY }}'\n"
                "      - env:\n"
                "          GH_TOKEN: ${{ github.token }}\n"
                "        run: git push origin HEAD && gh pr create\n"
            )

        inventory_mode = next(
            (
                item["mode"]
                for item in repo.get("dispatch_workflow_inventory", [])
                if item["path"] == path
            ),
            None,
        )
        if path == ".github/workflows/uninventoried.yml":
            inventory_mode = "reject-lifecycle-app"
        if inventory_mode == "docs-only":
            return (
                "name: Documentation sync fixture\n"
                "on:\n"
                "  push:\n"
                "    branches: [main]\n"
                "  workflow_dispatch:\n"
                "    inputs:\n"
                "      source_repository:\n"
                "      source_ref:\n"
                "      source_commit:\n"
                "      source_event:\n"
                "      idempotency_key:\n"
                "permissions:\n"
                "  contents: write\n"
                "  pages: write\n"
                "  id-token: write\n"
                "concurrency:\n"
                "  group: ${{ github.workflow }}-${{ github.event_name }}\n"
                "  cancel-in-progress: false\n"
                "jobs:\n"
                "  sync-docs:\n"
                "    if: >-\n"
                "      github.repository == 'OpenAdaptAI/openadapt-ops' &&\n"
                "      github.ref == 'refs/heads/main' &&\n"
                "      github.event_name == 'workflow_dispatch' &&\n"
                "      github.actor == 'openadapt-docs[bot]' &&\n"
                "      github.triggering_actor == 'openadapt-docs[bot]' &&\n"
                "      github.actor_id == vars.OPENADAPT_DOCS_ACTOR_ID &&\n"
                "      inputs.source_repository == 'OpenAdaptAI/openadapt-evals' &&\n"
                "      inputs.source_ref == 'refs/heads/main' &&\n"
                "      inputs.source_event == 'push' &&\n"
                "      inputs.source_commit != '' && inputs.idempotency_key != ''\n"
                "    environment: production-docs-deploy\n"
                "    steps:\n"
                "      - run: gh api repos/source/commits/main && test sha =~ '[0-9a-f]{40}'\n"
                "      - run: python scripts/validate_docs_sync.py repos.yml 'OpenAdapt docs sync dispatch v1' sha256\n"
                "      - run: test '${{ inputs.idempotency_key }}' =~ '^docs-sync:[0-9a-f]{64}$'\n"
                "      - run: echo '${{ vars.OPENADAPT_DOCS_APP_ID }} "
                "${{ vars.OPENADAPT_DOCS_INSTALLATION_ID }} "
                "${{ secrets.OPENADAPT_DOCS_APP_PRIVATE_KEY }}'\n"
                "      - env:\n"
                "          GH_TOKEN: ${{ github.token }}\n"
                "        run: git push origin HEAD:automation-docs && gh pr create\n"
                "  deploy-pages:\n"
                "    if: github.event_name == 'push'\n"
                "    environment:\n"
                "      name: github-pages\n"
                "    steps:\n"
                "      - run: true\n"
            )
        if inventory_mode == "reject-lifecycle-app":
            guarded = repo_name != self.unguarded_dispatch_repo
            cancel_value = (
                "true" if repo_name == self.cancelling_dispatch_repo else "false"
            )
            extra = ""
            if path == ".github/workflows/profile-consistency.yml":
                extra = "  pull_request:\n"
                if repo_name == self.path_filtered_repo:
                    extra += "    paths-ignore:\n      - docs/**\n"
                job_id = "validate-profile"
                job_name = "Validate profile"
            elif path == ".github/workflows/production-lifecycle-policy.yml":
                extra = "  pull_request:\n"
                if repo_name == self.path_filtered_repo:
                    extra += "    paths-ignore:\n      - docs/**\n"
                job_id = "validate"
                job_name = "Validate Production lifecycle"
            else:
                job_id = "run"
                job_name = "Run"
            pages = ""
            if path == ".github/workflows/sync.yml":
                pages = (
                    "permissions:\n"
                    "  contents: write\n"
                    "  pages: write\n"
                    "  id-token: write\n"
                )
                environment = "    environment:\n      name: github-pages\n"
            else:
                pages = "permissions:\n  contents: read\n"
                environment = ""
            return (
                "name: Dispatch fixture\n"
                "on:\n"
                "  workflow_dispatch:\n"
                f"{extra}"
                f"{pages}"
                "concurrency:\n"
                "  group: ${{ github.workflow }}-${{ github.event_name }}\n"
                f"  cancel-in-progress: {cancel_value}\n"
                "jobs:\n"
                + (
                    "  reject-lifecycle-app:\n"
                    "    permissions: {}\n"
                    "    runs-on: ubuntu-latest\n"
                    "    steps:\n"
                    "      - env:\n"
                    "          ACTOR: ${{ github.actor }}\n"
                    "          TRIGGERING_ACTOR: ${{ github.triggering_actor }}\n"
                    "        run: test \"$ACTOR\" != 'openadapt-lifecycle[bot]' "
                    "-a \"$TRIGGERING_ACTOR\" != 'openadapt-lifecycle[bot]'\n"
                    if guarded
                    else ""
                )
                + (
                    f"  {job_id}:\n"
                    f"    name: {job_name}\n"
                    + (
                        "    needs: reject-lifecycle-app\n"
                        "    if: >-\n"
                        "      github.actor != 'openadapt-lifecycle[bot]' &&\n"
                        "      github.triggering_actor != 'openadapt-lifecycle[bot]'\n"
                        if guarded
                        else ""
                    )
                    + (
                        f"{environment}"
                        "    runs-on: ubuntu-latest\n"
                        "    steps:\n"
                        "      - run: true\n"
                    )
                )
            )

        if path == ".github/workflows/unauthorized.yml":
            environment = repo["lifecycle_environments"][0]["name"]
            return f"on:\n  push:\njobs:\n  run:\n    environment: {environment}\n"

        workflow = (
            "on:\n"
            "  pull_request:\n"
            "permissions:\n"
            "  id-token: write\n"
            "jobs:\n"
            "  prepare:\n"
            "    environment: release-identity\n"
            "  pypi:\n"
            "    environment: pypi\n"
            "  native:\n"
            "    environment: native-release\n"
        )
        if repo_name == self.path_filtered_repo:
            workflow = workflow.replace(
                "  pull_request:\n",
                "  pull_request:\n    paths-ignore:\n      - docs/**\n",
            )
        return workflow

    def write(
        self, method: str, path: str, payload: Mapping[str, Any] | None = None
    ) -> Any:
        self.writes.append((method, path, payload or {}))
        return {}


def config() -> dict[str, Any]:
    value = load_config(CONFIG_PATH)
    value["release_identity"]["actor_id"] = 991122
    value["lifecycle_identity"]["app_id"] = 771100
    value["lifecycle_identity"]["actor_id"] = 881100
    value["lifecycle_identity"]["installation_id"] = 661100
    value["docs_identity"]["app_id"] = 772200
    value["docs_identity"]["actor_id"] = 882200
    value["docs_identity"]["installation_id"] = 761100
    value["cloud_checkout_identity"]["app_id"] = 773300
    value["cloud_checkout_identity"]["installation_id"] = 861100
    value["lifecycle_ref_identity"]["app_slug"] = "test-lifecycle-ref"
    value["lifecycle_ref_identity"]["app_id"] = 774400
    value["lifecycle_ref_identity"]["actor_login"] = "test-lifecycle-ref[bot]"
    value["lifecycle_ref_identity"]["actor_id"] = 884400
    value["lifecycle_ref_identity"]["installation_id"] = 864400
    return value


def test_policy_has_only_the_reviewed_owned_repositories() -> None:
    value = load_config(CONFIG_PATH)
    assert {repo["name"] for repo in value["repositories"]} == {
        ".github",
        "OpenAdapt",
        "openadapt-agent",
        "openadapt-capture",
        "openadapt-desktop",
        "openadapt-evals",
        "openadapt-flow",
        "openadapt-ops",
        "openadapt-web",
    }
    cloud = value["plan_constraints"][0]
    assert cloud["repository"] == "openadapt-cloud"
    assert cloud["mode"] == "public-deployment-authority"
    assert cloud["managed"] is True
    assert cloud["private_repository_mutation"] is False


def test_lifecycle_identity_is_separate_and_least_privilege() -> None:
    value = load_config(CONFIG_PATH)
    release = value["release_identity"]
    lifecycle = value["lifecycle_identity"]
    assert release["app_slug"] == "openadapt-release"
    assert release["required_repository_permissions"] == [
        "Contents: write",
        "Pull requests: write",
        "Metadata: read",
    ]
    assert lifecycle["app_slug"] == "openadapt-lifecycle"
    assert lifecycle["actor_login"] == "openadapt-lifecycle[bot]"
    assert lifecycle["repository_scope"] == [
        ".github",
        "openadapt-evals",
        "openadapt-ops",
    ]
    assert lifecycle["required_repository_permissions"] == [
        "Actions: write",
        "Metadata: read",
        "Pull requests: write",
    ]
    assert lifecycle["forbidden_repository_permissions"] == ["Contents: write"]
    assert lifecycle["ruleset_bypass"] is False
    assert lifecycle["workflow_paths"][".github"] == [
        ".github/workflows/production-lifecycle-activation.yml",
        ".github/workflows/production-cloud-deploy.yml",
        ".github/workflows/qualification-authority-state.yml",
        ".github/workflows/qualification-revocation-state.yml",
    ]
    assert set(lifecycle["actions_write_risk"]["capabilities"]) == {
        "Dispatch repository workflows",
        "Cancel or rerun workflow runs",
        "Delete workflow artifacts",
    }
    docs = value["docs_identity"]
    assert docs["app_slug"] == "openadapt-docs"
    assert docs["actor_login"] == "openadapt-docs[bot]"
    assert docs["repository_scope"] == ["openadapt-ops"]
    assert docs["required_repository_permissions"] == [
        "Actions: write",
        "Metadata: read",
        "Pull requests: write",
    ]
    assert docs["forbidden_repository_permissions"] == ["Contents: write"]
    assert docs["ruleset_bypass"] is False
    checkout = value["cloud_checkout_identity"]
    assert checkout["app_slug"] == "openadapt-cloud-checkout"
    assert checkout["repository_scope"] == ["openadapt-cloud"]
    assert checkout["required_repository_permissions"] == [
        "Contents: read",
        "Metadata: read",
    ]
    assert checkout["ruleset_bypass"] is False
    audit = value["dispatch_privilege_audit"]
    assert audit["openadapt_ops_main_protected"] is False
    assert set(audit["unprotected_operational_environments"]) == {
        "production-backup",
        "production-backup-monitor",
    }
    assert audit["lifecycle_app_installation"] == "absent"
    assert audit["docs_app_installation"] == "absent"
    assert audit["cloud_checkout_app_installation"] == "absent"


def test_lifecycle_environments_override_the_unchanged_default() -> None:
    value = load_config(CONFIG_PATH)
    assert value["environment_defaults"] == {
        "wait_timer": 0,
        "prevent_self_review": False,
    }
    expected = {
        ".github": [
            (
                "production-lifecycle-activation",
                ".github/workflows/production-lifecycle-activation.yml",
            ),
            (
                "production-cloud-deploy",
                ".github/workflows/production-cloud-deploy.yml",
            ),
            (
                "qualification-authority-state",
                ".github/workflows/qualification-authority-state.yml",
            ),
            (
                "qualification-revocation-state",
                ".github/workflows/qualification-revocation-state.yml",
            ),
        ],
        "openadapt-evals": [
            (
                "production-lifecycle-evidence",
                ".github/workflows/production-lifecycle-evidence.yml",
            )
        ],
        "openadapt-ops": [
            (
                "production-lifecycle-projection",
                ".github/workflows/production-lifecycle-projection.yml",
            )
        ],
    }
    by_name = {repo["name"]: repo for repo in value["repositories"]}
    for repo_name, expected_environments in expected.items():
        environments = by_name[repo_name]["lifecycle_environments"]
        assert environments == [
            {
                "name": environment_name,
                "wait_timer": 0,
                "prevent_self_review": True,
                "deployment_policies": [{"type": "branch", "name": "main"}],
                "exclusive_workflow": workflow_path,
            }
            for environment_name, workflow_path in expected_environments
        ]
        assert all(
            desired_environment(value, environment)["prevent_self_review"] is True
            for environment in environments
        )


def test_pages_and_lifecycle_required_checks_are_exact() -> None:
    value = load_config(CONFIG_PATH)
    by_name = {repo["name"]: repo for repo in value["repositories"]}
    ops = by_name["openadapt-ops"]
    profile = by_name[".github"]
    assert "Validate Production lifecycle" in ops["required_checks"]
    assert profile["required_checks"] == ["validate-profile"]
    assert ops["release_environments"] == [
        {
            "name": "github-pages",
            "deployment_policies": [{"type": "branch", "name": "main"}],
            "exclusive_workflow": ".github/workflows/sync.yml",
        },
        {
            "name": "production-docs-deploy",
            "wait_timer": 0,
            "prevent_self_review": True,
            "deployment_policies": [{"type": "branch", "name": "main"}],
            "exclusive_workflow": ".github/workflows/sync.yml",
        },
    ]
    sync = ops["release_workflows"][0]
    assert sync["path"] == ".github/workflows/sync.yml"
    assert any(
        "pages" in pattern and "write" in pattern
        for pattern in sync["required_patterns"]
    )
    assert any(
        "id-token" in pattern and "write" in pattern
        for pattern in sync["required_patterns"]
    )
    assert "inputs\\.source_event\\s*==\\s*['\"]push['\"]" in sync["required_patterns"]
    assert "repo-updated" in sync["forbidden_patterns"]
    assert "docs-sync:" in sync["required_patterns"]

    projection = ops["lifecycle_workflows"][0]
    assert projection["path"] == ".github/workflows/production-lifecycle-projection.yml"
    for exact_pattern in (
        "inputs\\.candidate_admissions_sha256",
        "inputs\\.candidate_ledger_head_sha256",
        "inputs\\.idempotency_key",
        "OpenAdapt production lifecycle ledger head v1\\\\0",
        "OpenAdapt production lifecycle projection idempotency v1\\\\0",
    ):
        assert exact_pattern in projection["required_patterns"]

    qualification = [
        item
        for item in profile["lifecycle_workflows"]
        if "qualification-" in item["path"]
    ]
    assert len(qualification) == 2
    assert all("actions/attest" in item["required_patterns"] for item in qualification)
    assert all(
        any("git\\s+push" in pattern for pattern in item["forbidden_patterns"])
        for item in profile["lifecycle_workflows"]
    )


def test_agent_package_and_mcp_release_contract_is_exact() -> None:
    value = load_config(CONFIG_PATH)
    agent = next(
        repo for repo in value["repositories"] if repo["name"] == "openadapt-agent"
    )
    assert agent["audited_main_sha"] == "be253dd558a95bfb457c18715d258854aba79f69"
    assert agent["required_checks"] == [
        "Analyze (python)",
        "dependency-review",
        "gitleaks",
        "test (3.10, floor)",
        "test (3.11, current)",
        "test (3.12, current)",
    ]
    assert agent["path_scoped_checks"] == ["Build + validate (dry run, no publish)"]
    assert [item["name"] for item in agent["release_environments"]] == [
        "release-identity",
        "pypi",
        "mcp-registry",
    ]
    workflow = agent["release_workflows"][0]
    for required in (
        "actions/create-github-app-token",
        "pypa/gh-action-pypi-publish",
        "mcp-publisher\\s+login\\s+github-oidc",
        "scripts/verify_release_registries\\.py",
        "production-admission-candidate\\.json",
    ):
        assert required in workflow["required_patterns"]
    assert {"PYPI_API_TOKEN", "MCP_GITHUB_TOKEN"} <= set(workflow["forbidden_patterns"])


def test_backup_environment_is_automatic_but_exact_main_only() -> None:
    value = load_config(CONFIG_PATH)
    ops = next(
        repo for repo in value["repositories"] if repo["name"] == "openadapt-ops"
    )
    assert ops["operational_environments"] == [
        {
            "name": "production-backup",
            "wait_timer": 0,
            "prevent_self_review": False,
            "required_reviewers": False,
            "deployment_policies": [{"type": "branch", "name": "main"}],
            "exclusive_workflow": ".github/workflows/db-backup.yml",
        }
    ]
    desired = desired_environment(value, ops["operational_environments"][0])
    assert desired["reviewers"] == []
    assert desired["deployment_branch_policy"] == {
        "protected_branches": False,
        "custom_branch_policies": True,
    }
    workflow = ops["operational_workflows"][0]
    assert "github\\.ref_protected" in workflow["required_patterns"]
    assert "allowed-account-ids:\\s*'992382684924'" in workflow["required_patterns"]
    assert {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"} <= set(
        workflow["forbidden_patterns"]
    )


def test_unprotected_existing_environment_produces_target_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, unprotected_environment_repo="openadapt-agent"),
        value,
    )
    agent = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-agent"
    )
    assert any(item["kind"] == "put_environment" for item in agent["actions"])


def test_cloud_authorization_and_receipt_are_distinct() -> None:
    value = load_config(CONFIG_PATH)
    authority = value["private_cloud_authority"]
    assert authority["authorization_schema"] == (
        "openadapt.production-cloud-deploy-authorization/v1"
    )
    assert authority["result_schema"] == (
        "openadapt.production-cloud-deployment-result/v1"
    )
    assert authority["authorization_fields"] == [
        "schema_version",
        "kind",
        "authorization_id",
        "deployment_intent_id",
        "target",
        "operation",
        "source_commit",
        "authority_source_commit",
        "deploy_workflow_run_id",
        "deploy_workflow_run_attempt",
        "provider_idempotency_key",
        "lifecycle_policy_sha256",
        "lifecycle_ledger_sha256",
        "lifecycle_ledger_head_sha256",
        "prior_admission_sha256",
        "prior_revocation_sha256",
        "prior_registry_head_sha256",
        "prior_registry_revision",
        "issued_at",
        "expires_at",
    ]
    assert "provider_effect_commitment_sha256" not in authority["authorization_fields"]
    assert "provider_effect_commitment_sha256" in authority["result_fields"]
    assert authority["authorization_max_age_seconds"] == 3600
    profile = next(repo for repo in value["repositories"] if repo["name"] == ".github")
    workflow = next(
        item
        for item in profile["lifecycle_workflows"]
        if item["path"] == ".github/workflows/production-cloud-deploy.yml"
    )
    assert "actions/upload-artifact" in workflow["forbidden_patterns"]
    assert "permission-contents:\\s*read" in workflow["required_patterns"]


def test_cloud_authorization_verification_must_precede_checkout_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, misordered_cloud_authorization=True), value
    )
    profile = next(repo for repo in plan["repositories"] if repo["name"] == ".github")
    assert {item["code"] for item in profile["blockers"]} >= {
        "lifecycle_workflow_order_invalid"
    }


def test_path_scoped_check_cannot_also_be_required() -> None:
    value = config()
    value["repositories"][0]["path_scoped_checks"].append(
        value["repositories"][0]["required_checks"][0]
    )
    with pytest.raises(PolicyError, match="path-scoped checks cannot be required"):
        validate_config(value)


def test_main_has_no_bypass_and_tag_immutability_has_no_bypass() -> None:
    value = config()
    repo = value["repositories"][0]
    actor = ReleaseActor(actor_id=991122, app_slug="openadapt-release")
    by_name = {item["name"]: item for item in desired_rulesets(value, repo, actor)}

    main = by_name["OpenAdapt policy: protected main"]
    creation = by_name["OpenAdapt policy: release tag creation"]
    immutable = by_name["OpenAdapt policy: immutable release tags"]
    assert main["bypass_actors"] == []
    assert creation["bypass_actors"] == [
        {
            "actor_id": 991122,
            "actor_type": "Integration",
            "bypass_mode": "always",
        }
    ]
    assert creation["rules"] == [{"type": "creation"}]
    assert immutable["bypass_actors"] == []
    assert {rule["type"] for rule in immutable["rules"]} == {
        "update",
        "deletion",
        "non_fast_forward",
    }


def test_profile_lifecycle_feed_ref_is_linear_and_has_no_bypass() -> None:
    value = config()
    profile = next(repo for repo in value["repositories"] if repo["name"] == ".github")
    actor = ReleaseActor(actor_id=991122, app_slug="openadapt-release")
    by_name = {item["name"]: item for item in desired_rulesets(value, profile, actor)}
    feed = by_name["OpenAdapt policy: Production lifecycle feed"]
    assert feed["conditions"] == {
        "ref_name": {
            "include": ["refs/heads/production-lifecycle-feed"],
            "exclude": [],
        }
    }
    assert feed["bypass_actors"] == []
    assert {rule["type"] for rule in feed["rules"]} == {
        "deletion",
        "non_fast_forward",
        "required_linear_history",
    }


def test_inactive_lifecycle_ref_identity_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    identity = value["lifecycle_ref_identity"]
    for field in ("app_slug", "actor_login"):
        identity[field] = ""
        monkeypatch.delenv(identity[f"{field}_environment"], raising=False)
    for field in ("app_id", "actor_id", "installation_id"):
        identity[field] = 0
        monkeypatch.delenv(identity[f"{field}_environment"], raising=False)
    plan = build_plan(ReadOnlyFixtureGitHub(value), value)
    assert plan["safe_to_apply"] is False
    assert {item["code"] for item in plan["global_blockers"]} >= {
        "lifecycle_ref_identity_app_slug_unresolved",
        "lifecycle_ref_identity_actor_login_unresolved",
        "lifecycle_ref_identity_app_id_unresolved",
        "lifecycle_ref_identity_actor_id_unresolved",
        "lifecycle_ref_identity_installation_id_unresolved",
    }


def test_plan_is_read_only_and_manages_only_the_public_cloud_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    github = ReadOnlyFixtureGitHub(value)
    plan = build_plan(github, value)

    assert plan["safe_to_apply"] is True
    assert plan["blocker_count"] == 0
    assert github.writes == []
    assert {repo["name"] for repo in plan["repositories"]} == {
        repo["name"] for repo in value["repositories"]
    }
    assert "openadapt-cloud" not in {repo["name"] for repo in plan["repositories"]}
    assert plan["private_cloud_authority"]["name"] == "openadapt-cloud"
    assert plan["private_cloud_authority"]["actions"] == []
    assert all(repo["actions"] for repo in plan["repositories"])


def test_missing_cloud_checkout_app_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, missing_cloud_checkout_app=True), value
    )
    assert plan["safe_to_apply"] is False
    assert plan["cloud_checkout_app_id"] is None
    assert {item["code"] for item in plan["global_blockers"]} >= {
        "cloud_checkout_identity_app_not_found"
    }


def test_release_app_permissions_must_be_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, release_app_permissions_mismatch=True), value
    )
    assert plan["safe_to_apply"] is False
    assert {item["code"] for item in plan["global_blockers"]} >= {
        "release_identity_permissions_mismatch"
    }


def test_private_cloud_deploy_workflow_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(ReadOnlyFixtureGitHub(value, unsafe_private_cloud=True), value)
    assert plan["safe_to_apply"] is False
    assert {item["code"] for item in plan["private_cloud_authority"]["blockers"]} >= {
        "private_cloud_deploy_workflow_present",
        "private_cloud_workflow_can_deploy",
    }


def test_private_cloud_production_secret_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, private_cloud_production_secret=True), value
    )
    assert plan["safe_to_apply"] is False
    assert {item["code"] for item in plan["private_cloud_authority"]["blockers"]} >= {
        "private_cloud_production_secret_present"
    }


def test_missing_lifecycle_app_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    github = ReadOnlyFixtureGitHub(value, missing_lifecycle_app=True)
    plan = build_plan(github, value)
    assert plan["safe_to_apply"] is False
    assert plan["lifecycle_app_id"] is None
    assert {item["code"] for item in plan["global_blockers"]} >= {
        "lifecycle_identity_app_not_found"
    }
    assert github.writes == []


def test_missing_docs_app_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    github = ReadOnlyFixtureGitHub(value, missing_docs_app=True)
    plan = build_plan(github, value)
    assert plan["safe_to_apply"] is False
    assert plan["docs_app_id"] is None
    assert {item["code"] for item in plan["global_blockers"]} >= {
        "docs_identity_app_not_found"
    }
    assert github.writes == []


def test_uninventoried_dispatch_workflow_blocks_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, extra_dispatch_repo="openadapt-evals"), value
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )
    assert {item["code"] for item in evals["blockers"]} >= {
        "dispatch_workflow_not_inventoried"
    }


def test_dispatch_workflow_without_app_rejection_blocks_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, unguarded_dispatch_repo="openadapt-ops"), value
    )
    ops = next(repo for repo in plan["repositories"] if repo["name"] == "openadapt-ops")
    assert {item["code"] for item in ops["blockers"]} >= {
        "dispatch_workflow_accepts_lifecycle_app"
    }


def test_dispatch_workflow_cannot_cancel_an_active_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, cancelling_dispatch_repo="openadapt-evals"),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )
    assert {item["code"] for item in evals["blockers"]} >= {
        "dispatch_workflow_concurrency_not_isolated"
    }


def test_lifecycle_environment_reference_outside_exact_workflow_blocks_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, unauthorized_environment_repo="openadapt-evals"),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )
    assert {item["code"] for item in evals["blockers"]} >= {
        "lifecycle_environment_workflow_scope"
    }


def test_active_pull_request_check_blocks_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(ReadOnlyFixtureGitHub(value, active_repo="openadapt-flow"), value)
    flow = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-flow"
    )
    assert plan["safe_to_apply"] is False
    assert flow["active_checks"] == [
        {"pull_request": 12, "name": "test", "status": "in_progress"}
    ]
    assert {item["code"] for item in flow["blockers"]} == {
        "active_pull_request_checks",
        "open_pull_requests",
    }


def test_open_pull_request_blocks_apply_after_checks_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(ReadOnlyFixtureGitHub(value, open_repo="openadapt-agent"), value)
    agent = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-agent"
    )
    assert plan["safe_to_apply"] is False
    assert {item["code"] for item in agent["blockers"]} == {"open_pull_requests"}


def test_path_filtered_target_check_blocks_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, path_filtered_repo="openadapt-web"), value
    )
    web = next(repo for repo in plan["repositories"] if repo["name"] == "openadapt-web")
    assert plan["safe_to_apply"] is False
    assert {item["code"] for item in web["blockers"]} == {
        "admission_workflow_forbidden_pattern"
    }


def test_dry_run_client_refuses_a_mutation_before_starting_gh() -> None:
    with pytest.raises(GitHubError, match="dry-run client refused"):
        GhApiClient(allow_writes=False).write("PUT", "/repos/example/example", {})


def test_apply_refuses_unconfirmed_environment_policy_deletion() -> None:
    plan = {
        "organization": "OpenAdaptAI",
        "repositories": [
            {
                "name": "OpenAdapt",
                "requires_environment_policy_prune": True,
                "actions": [
                    {
                        "kind": "delete_environment_policy",
                        "environment": "pypi",
                        "policy_id": 3,
                    }
                ],
            }
        ],
    }
    github = ReadOnlyFixtureGitHub(config())
    with pytest.raises(PolicyError, match="--prune-environment-policies"):
        _apply_actions(github, plan, prune_environment_policies=False)
    assert github.writes == []


def test_apply_plan_must_be_fresh_and_unchanged() -> None:
    value = config()
    base = {
        "organization": "OpenAdaptAI",
        "generated_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "blocker_count": 0,
        "safe_to_apply": True,
        "config_sha256": "a",
        "release_actor_id": 1,
        "repositories": [],
    }
    with pytest.raises(PolicyError, match="stale"):
        validate_plan_for_apply(base, base, value)

    fresh = json.loads(json.dumps(base))
    fresh["generated_at"] = datetime.now(timezone.utc).isoformat()
    changed = json.loads(json.dumps(fresh))
    changed["release_actor_id"] = 2
    with pytest.raises(PolicyError, match="live state changed"):
        validate_plan_for_apply(fresh, changed, value)

    changed_lifecycle = json.loads(json.dumps(fresh))
    fresh["lifecycle_app_id"] = 771100
    fresh["lifecycle_actor_id"] = 881100
    fresh["lifecycle_installation_id"] = 661100
    changed_lifecycle.update(fresh)
    changed_lifecycle["lifecycle_actor_id"] = 881101
    with pytest.raises(PolicyError, match="live state changed"):
        validate_plan_for_apply(fresh, changed_lifecycle, value)
