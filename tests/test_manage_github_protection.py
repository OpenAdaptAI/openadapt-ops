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
    _parse_workflow_document,
    _workflow_triggers,
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
        path_filtered_repo: str | None = None,
        missing_lifecycle_app: bool = False,
        missing_docs_app: bool = False,
        extra_dispatch_repo: str | None = None,
        unguarded_dispatch_repo: str | None = None,
        unauthorized_environment_repo: str | None = None,
        cancelling_dispatch_repo: str | None = None,
        release_app_all_repositories: bool = False,
        release_app_permissions_mismatch: bool = False,
        release_app_extra_repository: bool = False,
        null_deployment_policy_repo: str | None = None,
        missing_variable: tuple[str, str] | None = None,
        repository_secret: tuple[str, str] | None = None,
        missing_environment_secret: tuple[str, str, str] | None = None,
        extra_environment_secret: tuple[str, str, str] | None = None,
        repository_variable_shadow: tuple[str, str] | None = None,
        environment_variable_shadow: tuple[str, str, str] | None = None,
        missing_environment: tuple[str, str] | None = None,
        admin_bypass_environment: tuple[str, str] | None = None,
        omitted_admin_bypass_environment: tuple[str, str] | None = None,
        main_drift_repo: str | None = None,
        advance_main_during_plan_repo: str | None = None,
        workflow_overrides: Mapping[tuple[str, str], str] | None = None,
    ) -> None:
        self.config = config
        self.active_repo = active_repo
        self.path_filtered_repo = path_filtered_repo
        self.missing_lifecycle_app = missing_lifecycle_app
        self.missing_docs_app = missing_docs_app
        self.extra_dispatch_repo = extra_dispatch_repo
        self.unguarded_dispatch_repo = unguarded_dispatch_repo
        self.unauthorized_environment_repo = unauthorized_environment_repo
        self.cancelling_dispatch_repo = cancelling_dispatch_repo
        self.release_app_all_repositories = release_app_all_repositories
        self.release_app_permissions_mismatch = release_app_permissions_mismatch
        self.release_app_extra_repository = release_app_extra_repository
        self.null_deployment_policy_repo = null_deployment_policy_repo
        self.missing_variable = missing_variable
        self.repository_secret = repository_secret
        self.missing_environment_secret = missing_environment_secret
        self.extra_environment_secret = extra_environment_secret
        self.repository_variable_shadow = repository_variable_shadow
        self.environment_variable_shadow = environment_variable_shadow
        self.missing_environment = missing_environment
        self.admin_bypass_environment = admin_bypass_environment
        self.omitted_admin_bypass_environment = omitted_admin_bypass_environment
        self.main_drift_repo = main_drift_repo
        self.advance_main_during_plan_repo = advance_main_during_plan_repo
        self.workflow_overrides = dict(workflow_overrides or {})
        self.writes: list[tuple[str, str, Mapping[str, Any]]] = []
        self.gets: list[str] = []
        self.main_reads: dict[str, int] = {}
        self.by_name = {repo["name"]: repo for repo in config["repositories"]}
        self.repository_ids = {
            repo["name"]: 1000 + index
            for index, repo in enumerate(config["repositories"])
        }

    def get(self, path: str, *, optional: bool = False) -> Any:
        self.gets.append(path)
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
        if path == "/users/openadapt-lifecycle%5Bbot%5D":
            return {"id": 881100, "login": "openadapt-lifecycle[bot]"}
        if path == "/users/openadapt-docs%5Bbot%5D":
            return {"id": 882200, "login": "openadapt-docs[bot]"}
        if path == "/users/abrichr":
            return {"id": 774615, "login": "abrichr"}
        if path == "/orgs/OpenAdaptAI/installations?per_page=100":
            return {
                "installations": [
                    {
                        "id": 551100,
                        "app_id": 991122,
                        "app_slug": "openadapt-release",
                        "repository_selection": (
                            "all" if self.release_app_all_repositories else "selected"
                        ),
                        "permissions": (
                            {
                                "contents": "write",
                                "metadata": "read",
                                "pull_requests": "write",
                            }
                            if self.release_app_permissions_mismatch
                            else {"contents": "write", "metadata": "read"}
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
                ]
            }
        if path == "/user/installations/551100/repositories?per_page=100":
            return {
                "repositories": [
                    {"name": name}
                    for name in sorted(
                        {
                            "OpenAdapt",
                            "openadapt-agent",
                            "openadapt-capture",
                            "openadapt-desktop",
                            "openadapt-evals",
                            "openadapt-flow",
                        }
                        | (
                            {"unexpected-public-repo"}
                            if self.release_app_extra_repository
                            else set()
                        )
                    )
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
        if path == "/user/installations/761100/repositories?per_page=100":
            return {"repositories": [{"name": "openadapt-ops"}]}
        if path.startswith("/repositories/"):
            parts = path.split("?")[0].split("/")
            repository_id = int(parts[2])
            name = next(
                repo_name
                for repo_name, candidate_id in self.repository_ids.items()
                if candidate_id == repository_id
            )
            environment_name = parts[4]
            secret_name = (
                self.environment_variable_shadow[2]
                if self.environment_variable_shadow is not None
                and self.environment_variable_shadow[:2] == (name, environment_name)
                else None
            )
            variables = [] if secret_name is None else [{"name": secret_name}]
            return {"total_count": len(variables), "variables": variables}
        parts = path.split("?")[0].split("/")
        if len(parts) >= 4 and parts[1] == "repos":
            name = parts[3]
            repo = self.by_name[name]
            if len(parts) == 4:
                return {
                    "id": self.repository_ids[name],
                    "full_name": f"OpenAdaptAI/{name}",
                    "private": False,
                    "default_branch": "main",
                }
            if parts[4] == "commits" and parts[5] == "main":
                self.main_reads[name] = self.main_reads.get(name, 0) + 1
                return {
                    "sha": (
                        "f" * 40
                        if name == self.main_drift_repo
                        or (
                            name == self.advance_main_during_plan_repo
                            and self.main_reads[name] > 1
                        )
                        else repo["audited_main_sha"]
                    )
                }
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
                if name == self.active_repo:
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
                environments = repo["release_environments"] + repo.get(
                    "lifecycle_environments", []
                )
                environment_by_name = {item["name"]: item for item in environments}
                if self.extra_environment_secret is not None:
                    extra_repo, extra_environment, _ = self.extra_environment_secret
                    if name == extra_repo:
                        environment_by_name[extra_environment] = {
                            "name": extra_environment
                        }
                if len(parts) == 5:
                    values = [
                        {"name": environment_name}
                        for environment_name in sorted(environment_by_name)
                        if self.missing_environment != (name, environment_name)
                    ]
                    return {"total_count": len(values), "environments": values}
                environment_name = parts[5]
                if self.missing_environment == (name, environment_name):
                    return None
                if len(parts) >= 7 and parts[6] == "secrets":
                    secret_names = {
                        identity["private_key_secret"]
                        for identity in (
                            self.config["release_identity"],
                            self.config["lifecycle_identity"],
                            self.config["docs_identity"],
                        )
                        if environment_name
                        in identity.get("private_key_environment_bindings", {}).get(
                            name, []
                        )
                    }
                    if self.missing_environment_secret is not None:
                        missing_repo, missing_environment, missing_name = (
                            self.missing_environment_secret
                        )
                        if (name, environment_name) == (
                            missing_repo,
                            missing_environment,
                        ):
                            secret_names.discard(missing_name)
                    if self.extra_environment_secret is not None:
                        extra_repo, extra_environment, extra_name = (
                            self.extra_environment_secret
                        )
                        if (name, environment_name) == (extra_repo, extra_environment):
                            secret_names.add(extra_name)
                    return {
                        "total_count": len(secret_names),
                        "secrets": [
                            {"name": secret_name}
                            for secret_name in sorted(secret_names)
                        ],
                    }
                if len(parts) >= 7 and parts[6] == "deployment-branch-policies":
                    policies = [
                        {"id": index + 1, **policy}
                        for index, policy in enumerate(
                            environment_by_name[environment_name].get(
                                "deployment_policies", []
                            )
                        )
                    ]
                    return {"branch_policies": policies}
                environment = environment_by_name[environment_name]
                if name == self.null_deployment_policy_repo:
                    return {
                        "can_admins_bypass": False,
                        "protection_rules": [],
                        "deployment_branch_policy": None,
                    }
                response = {
                    "protection_rules": [
                        {
                            "type": "required_reviewers",
                            "prevent_self_review": environment.get(
                                "prevent_self_review",
                                self.config["environment_defaults"][
                                    "prevent_self_review"
                                ],
                            ),
                            "reviewers": [
                                {
                                    "type": "User",
                                    "reviewer": {"id": 774615},
                                }
                            ],
                        }
                    ],
                    "deployment_branch_policy": {
                        "protected_branches": False,
                        "custom_branch_policies": True,
                    },
                }
                if self.omitted_admin_bypass_environment != (name, environment_name):
                    response["can_admins_bypass"] = self.admin_bypass_environment == (
                        name,
                        environment_name,
                    )
                return response
            if parts[4:6] == ["actions", "variables"]:
                variable = parts[6]
                if self.missing_variable == (name, variable):
                    return None
                if self.repository_variable_shadow == (name, variable):
                    return {"name": variable, "value": "shadow"}
                values = {
                    "OPENADAPT_RELEASE_APP_ID": "991122",
                    "OPENADAPT_LIFECYCLE_APP_ID": "771100",
                    "OPENADAPT_LIFECYCLE_ACTOR_ID": "881100",
                    "OPENADAPT_LIFECYCLE_INSTALLATION_ID": "661100",
                    "OPENADAPT_DOCS_APP_ID": "772200",
                    "OPENADAPT_DOCS_ACTOR_ID": "882200",
                    "OPENADAPT_DOCS_INSTALLATION_ID": "761100",
                }
                if variable not in values:
                    return None
                return {"name": variable, "value": values[variable]}
            if parts[4:6] == ["actions", "secrets"]:
                secret_names: set[str] = set()
                if self.repository_secret is not None:
                    secret_repo, secret_name = self.repository_secret
                    if name == secret_repo:
                        secret_names.add(secret_name)
                return {
                    "total_count": len(secret_names),
                    "secrets": [
                        {"name": secret_name} for secret_name in sorted(secret_names)
                    ],
                }
            if parts[4:6] == ["git", "trees"]:
                configured = set()
                for field in (
                    "release_workflows",
                    "admission_workflows",
                    "lifecycle_workflows",
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
        override = self.workflow_overrides.get((repo_name, path))
        if override is not None:
            return override
        repo = self.by_name[repo_name]
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
            lifecycle_token_repositories = (
                "          repositories: |\n"
                "            .github\n"
                "            openadapt-evals\n"
                "            openadapt-ops\n"
                if repo_name == "openadapt-ops"
                else f"          repositories: {repo_name}\n"
            )
            projection_steps = (
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: lifecycle-app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_LIFECYCLE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_LIFECYCLE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                f"{lifecycle_token_repositories}"
                "          permission-actions: write\n"
                "          permission-metadata: read\n"
                "          permission-pull-requests: write\n"
            )
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
                projection_steps += (
                    "      - run: gh api repos/OpenAdaptAI/.github/commits/main\n"
                    "      - run: python scripts/prepare_production_lifecycle_projection.py\n"
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
                '        run: git push origin "HEAD:refs/heads/automation-lifecycle"\n'
                "      - env:\n"
                "          GH_TOKEN: ${{ steps.lifecycle-app.outputs.token }}\n"
                "        run: gh pr create\n"
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
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: docs-app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_DOCS_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_DOCS_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-ops\n"
                "          permission-actions: write\n"
                "          permission-metadata: read\n"
                "          permission-pull-requests: write\n"
                "      - run: gh api repos/source/commits/main\n"
                "      - run: python scripts/validate_docs_sync.py --repositories repos.yml\n"
                "      - run: echo '${{ vars.OPENADAPT_DOCS_APP_ID }} "
                "${{ vars.OPENADAPT_DOCS_INSTALLATION_ID }} "
                "${{ secrets.OPENADAPT_DOCS_APP_PRIVATE_KEY }}'\n"
                "      - env:\n"
                "          GH_TOKEN: ${{ github.token }}\n"
                '        run: git push origin "HEAD:refs/heads/automation-docs"\n'
                "      - env:\n"
                "          GH_TOKEN: ${{ steps.docs-app.outputs.token }}\n"
                "        run: gh pr create\n"
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
            if (
                repo_name == "openadapt-evals"
                and path == ".github/workflows/release.yml"
            ):
                return (
                    "name: Release fixture\n"
                    "on:\n"
                    "  workflow_dispatch:\n"
                    "  push:\n"
                    "    tags:\n"
                    "      - 'v*'\n"
                    "permissions:\n"
                    "  contents: read\n"
                    "concurrency:\n"
                    "  group: ${{ github.workflow }}-${{ github.event_name }}\n"
                    f"  cancel-in-progress: {cancel_value}\n"
                    "jobs:\n"
                    + (
                        "  reject-lifecycle-app:\n"
                        "    if: github.event_name == 'workflow_dispatch'\n"
                        "    permissions: {}\n"
                        "    runs-on: ubuntu-latest\n"
                        "    steps:\n"
                        "      - env:\n"
                        "          ACTOR: ${{ github.actor }}\n"
                        "          TRIGGERING_ACTOR: ${{ github.triggering_actor }}\n"
                        "        run: |\n"
                        "          test \"$ACTOR\" != 'openadapt-lifecycle[bot]'\n"
                        "          test \"$TRIGGERING_ACTOR\" != 'openadapt-lifecycle[bot]'\n"
                        "          test \"$ACTOR\" != 'openadapt-docs[bot]'\n"
                        "          test \"$TRIGGERING_ACTOR\" != 'openadapt-docs[bot]'\n"
                        if guarded
                        else ""
                    )
                    + "  authorize-release-tag:\n"
                    "    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')\n"
                    "    permissions: {}\n"
                    "    runs-on: ubuntu-latest\n"
                    "    steps:\n"
                    "      - run: test \"$GITHUB_ACTOR\" = 'openadapt-release[bot]'\n"
                    "  create-release-tag:\n"
                    "    needs: reject-lifecycle-app\n"
                    "    if: >-\n"
                    "      github.event_name == 'workflow_dispatch' &&\n"
                    "      github.actor != 'openadapt-lifecycle[bot]' &&\n"
                    "      github.triggering_actor != 'openadapt-lifecycle[bot]' &&\n"
                    "      github.actor != 'openadapt-docs[bot]' &&\n"
                    "      github.triggering_actor != 'openadapt-docs[bot]'\n"
                    "    environment: release-identity\n"
                    "    runs-on: ubuntu-latest\n"
                    "    steps:\n"
                    "      - uses: actions/create-github-app-token@deadbeef\n"
                    "        id: release_app\n"
                    "        with:\n"
                    "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                    "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                    "          owner: OpenAdaptAI\n"
                    "          repositories: openadapt-evals\n"
                    "          permission-contents: write\n"
                    "      - run: test OpenAdaptAI/openadapt-evals = OpenAdaptAI/openadapt-evals && test refs/heads/main = refs/heads/main\n"
                    "      - run: python scripts/verify_release_lock.py\n"
                    "      - uses: actions/checkout@deadbeef\n"
                    "        with:\n"
                    "          token: ${{ steps.release_app.outputs.token }}\n"
                    "      - run: |\n"
                    "          git tag -a v1.2.3 -m release\n"
                    '          git push origin "refs/tags/v1.2.3"\n'
                    "  publish-pypi:\n"
                    "    needs: authorize-release-tag\n"
                    "    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') && github.actor == 'openadapt-release[bot]'\n"
                    "    environment: pypi\n"
                    "    permissions:\n"
                    "      id-token: write\n"
                    "    runs-on: ubuntu-latest\n"
                    "    steps:\n"
                    "      - run: python scripts/check_source_boundary.py --require-dist\n"
                    "      - uses: pypa/gh-action-pypi-publish@deadbeef\n"
                    "        with:\n"
                    "          skip-existing: true\n"
                    "      - uses: actions/create-github-app-token@deadbeef\n"
                    "        id: release-app\n"
                    "        with:\n"
                    "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                    "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                    "          owner: OpenAdaptAI\n"
                    "          repositories: openadapt-evals\n"
                    "          permission-contents: write\n"
                    "      - env:\n"
                    "          GH_TOKEN: ${{ steps.release-app.outputs.token }}\n"
                    "        run: gh release create v1.2.3\n"
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
                    "        run: |\n"
                    "          test \"$ACTOR\" != 'openadapt-lifecycle[bot]'\n"
                    "          test \"$TRIGGERING_ACTOR\" != 'openadapt-lifecycle[bot]'\n"
                    "          test \"$ACTOR\" != 'openadapt-docs[bot]'\n"
                    "          test \"$TRIGGERING_ACTOR\" != 'openadapt-docs[bot]'\n"
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
                        "      github.triggering_actor != 'openadapt-lifecycle[bot]' &&\n"
                        "      github.actor != 'openadapt-docs[bot]' &&\n"
                        "      github.triggering_actor != 'openadapt-docs[bot]'\n"
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

        if repo_name == "OpenAdapt":
            return (
                "on:\n"
                "  workflow_dispatch:\n"
                "  push:\n"
                "    tags:\n"
                '      - "v*"\n'
                "jobs:\n"
                "  create-release-tag:\n"
                "    environment: release-identity\n"
                "    steps:\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release-app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: OpenAdapt\n"
                "          permission-contents: write\n"
                "      - run: test refs/heads/main = refs/heads/main && test OpenAdaptAI/OpenAdapt = OpenAdaptAI/OpenAdapt\n"
                "      - run: test \"$GITHUB_ACTOR\" = 'openadapt-release[bot]'\n"
                "      - uses: actions/checkout@deadbeef\n"
                "        with:\n"
                "          token: ${{ steps.release-app.outputs.token }}\n"
                "      - run: |\n"
                "          git tag -a v1.2.3 -m release\n"
                '          git push origin "refs/tags/v1.2.3"\n'
                "  build-and-attest:\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - run: python scripts/check_source_boundary.py\n"
                "      - run: python scripts/verify_release_artifacts.py\n"
                "  publish-pypi:\n"
                "    environment: pypi\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - uses: pypa/gh-action-pypi-publish@deadbeef\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release-app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: OpenAdapt\n"
                "          permission-contents: write\n"
                "      - env:\n"
                "          GH_TOKEN: ${{ steps.release-app.outputs.token }}\n"
                "        run: gh release create v1.2.3\n"
                "  verify-publication:\n"
                "    steps:\n"
                "      - run: python scripts/validate_platform_manifest.py\n"
            )

        if repo_name == "openadapt-agent":
            return (
                "on:\n"
                "  workflow_dispatch:\n"
                "  push:\n"
                '    tags: ["v*"]\n'
                "permissions:\n"
                "  contents: read\n"
                "jobs:\n"
                "  tag:\n"
                "    environment: release-identity\n"
                "    steps:\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-agent\n"
                "          permission-contents: write\n"
                "      - run: test \"$GITHUB_ACTOR\" = 'openadapt-release[bot]'\n"
                "      - uses: actions/checkout@deadbeef\n"
                "        with:\n"
                "          token: ${{ steps.release_app.outputs.token }}\n"
                "      - run: |\n"
                "          git tag v1.2.3\n"
                "          git push origin v1.2.3\n"
                "  pypi:\n"
                "    environment: pypi\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - run: python scripts/check_release_artifacts.py dist\n"
                "      - run: python scripts/check_source_boundary.py --require-dist\n"
                "      - uses: pypa/gh-action-pypi-publish@deadbeef\n"
                "  mcp:\n"
                "    environment: mcp-registry\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - run: ./mcp-publisher login github-oidc\n"
                "      - run: python scripts/verify_release_registries.py\n"
                "      - run: test -f production-admission-candidate.json\n"
            )

        if repo_name in {"openadapt-flow", "openadapt-capture"}:
            archive_checks = (
                "      - run: python scripts/check_release_consistency.py --require-dist\n"
                if repo_name == "openadapt-flow"
                else (
                    "      - run: python scripts/verify_distribution.py dist/*\n"
                    "      - run: python scripts/check_source_boundary.py --require-dist\n"
                )
            )
            flow_dispatch_contract = (
                "concurrency:\n"
                "  group: engine-release-${{ github.ref }}\n"
                "  cancel-in-progress: false\n"
                if repo_name == "openadapt-flow"
                else ""
            )
            flow_refusal_job = (
                "  authorize-release-dispatch:\n"
                "    name: Refuse an invalid engine release dispatch\n"
                "    permissions: {}\n"
                "    steps:\n"
                "      - run: true\n"
                if repo_name == "openadapt-flow"
                else ""
            )
            return (
                "on:\n"
                "  workflow_dispatch:\n"
                "  push:\n"
                '    tags: ["v*"]\n'
                f"{flow_dispatch_contract}"
                "jobs:\n"
                f"{flow_refusal_job}"
                "  create-release-tag:\n"
                "    environment: release-identity\n"
                "    steps:\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                f"          repositories: {repo_name}\n"
                "          permission-contents: write\n"
                "      - run: test refs/heads/main = refs/heads/main\n"
                "      - uses: actions/checkout@deadbeef\n"
                "        with:\n"
                "          token: ${{ steps.release_app.outputs.token }}\n"
                "      - run: |\n"
                "          git tag --annotate v1.2.3 -m release\n"
                '          git push origin "refs/tags/v1.2.3"\n'
                "  publish:\n"
                "    environment: pypi\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - run: test \"$GITHUB_ACTOR\" = 'openadapt-release[bot]'\n"
                + archive_checks
                + "      - run: python scripts/verify_release_publication.py\n"
                "      - uses: pypa/gh-action-pypi-publish@deadbeef\n"
            )

        if repo_name == "openadapt-desktop" and path == ".github/workflows/release.yml":
            return (
                "on:\n"
                "  workflow_dispatch:\n"
                "  push:\n"
                "    tags:\n"
                "      - 'v*'\n"
                "concurrency:\n"
                "  group: engine-release-${{ github.ref }}\n"
                "  cancel-in-progress: false\n"
                "jobs:\n"
                "  authorize-release-dispatch:\n"
                "    name: Refuse an invalid engine release dispatch\n"
                "    permissions: {}\n"
                "  create-release-tag:\n"
                "    environment: release-identity\n"
                "    steps:\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-desktop\n"
                "          permission-contents: write\n"
                "      - run: test OpenAdaptAI/openadapt-desktop = OpenAdaptAI/openadapt-desktop && test refs/heads/main = refs/heads/main\n"
                "      - run: python scripts/verify_release_lock.py\n"
                "      - uses: actions/checkout@deadbeef\n"
                "        with:\n"
                "          token: ${{ steps.release_app.outputs.token }}\n"
                "      - run: |\n"
                "          git tag -a v1.2.3 -m release\n"
                '          git push origin "refs/tags/v1.2.3"\n'
                "  publish:\n"
                "    if: github.actor == 'openadapt-release[bot]'\n"
                "    environment: pypi\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - run: test \"$GITHUB_ACTOR\" = 'openadapt-release[bot]'\n"
                "      - run: python scripts/check_source_boundary.py --require-dist\n"
                "      - uses: pypa/gh-action-pypi-publish@deadbeef\n"
                "        with:\n"
                "          skip-existing: true\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-desktop\n"
                "          permission-contents: write\n"
                "      - env:\n"
                "          GH_TOKEN: ${{ steps.release_app.outputs.token }}\n"
                "        run: gh release create v1.2.3\n"
            )

        if (
            repo_name == "openadapt-desktop"
            and path == ".github/workflows/native-freshness.yml"
        ):
            return (
                "on:\n"
                "  release:\n"
                "  workflow_dispatch:\n"
                "permissions:\n"
                "  contents: read\n"
                "concurrency:\n"
                "  group: native-freshness-check\n"
                "  cancel-in-progress: false\n"
                "jobs:\n"
                "  validate:\n"
                "    steps:\n"
                "      - run: test refs/heads/main = refs/heads/main\n"
            )

        if (
            repo_name == "openadapt-desktop"
            and path == ".github/workflows/native-release.yml"
        ):
            return (
                "on:\n"
                "  workflow_dispatch:\n"
                "  push:\n"
                "    tags: ['desktop-v*']\n"
                "concurrency:\n"
                "  group: native-release\n"
                "  cancel-in-progress: false\n"
                "jobs:\n"
                "  authorize-native-dispatch:\n"
                "    name: Refuse an invalid native release dispatch\n"
                "    permissions: {}\n"
                "  create-native-tag:\n"
                "    environment: release-identity\n"
                "    steps:\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-desktop\n"
                "          permission-contents: write\n"
                "      - uses: actions/checkout@deadbeef\n"
                "        with:\n"
                "          token: ${{ steps.release_app.outputs.token }}\n"
                "      - run: |\n"
                "          git tag --annotate desktop-v1.2.3 -m release\n"
                '          git push origin "refs/tags/desktop-v1.2.3"\n'
                "  recover-published-native:\n"
                "    steps:\n"
                "      - run: echo state=absent state=partial state=complete\n"
                "  publish-native:\n"
                "    environment: native-release\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - run: test \"$GITHUB_ACTOR\" = 'openadapt-release[bot]'\n"
                "      - uses: actions/attest@deadbeef\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-desktop\n"
                "          permission-contents: write\n"
                "      - env:\n"
                "          GH_TOKEN: ${{ steps.release_app.outputs.token }}\n"
                "        run: gh release create desktop-v1.2.3\n"
            )

        if (
            repo_name == "openadapt-desktop"
            and path == ".github/workflows/ffmpeg-runtime.yml"
        ):
            return (
                "on:\n"
                "  workflow_dispatch:\n"
                "  push:\n"
                "    tags: ['ffmpeg-runtime-v*']\n"
                "concurrency:\n"
                "  group: ffmpeg-runtime-${{ github.ref }}\n"
                "  cancel-in-progress: false\n"
                "env:\n"
                "  SOURCE_SIGNATURE_SHA256: deadbeef\n"
                "  SIGNING_KEY_SHA256: deadbeef\n"
                "jobs:\n"
                "  authorize-runtime-dispatch:\n"
                "    name: Refuse an invalid managed-runtime dispatch\n"
                "    permissions: {}\n"
                "  create-runtime-tag:\n"
                "    environment: release-identity\n"
                "    steps:\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-desktop\n"
                "          permission-contents: write\n"
                "      - uses: actions/checkout@deadbeef\n"
                "        with:\n"
                "          token: ${{ steps.release_app.outputs.token }}\n"
                "      - run: |\n"
                "          git tag --annotate ffmpeg-runtime-v1.2.3-r1 -m release\n"
                '          git push origin "refs/tags/ffmpeg-runtime-v1.2.3-r1"\n'
                "  publish:\n"
                "    environment: native-release\n"
                "    permissions:\n"
                "      id-token: write\n"
                "    steps:\n"
                "      - run: test \"$GITHUB_ACTOR\" = 'openadapt-release[bot]'\n"
                "      - uses: actions/create-github-app-token@deadbeef\n"
                "        id: release_app\n"
                "        with:\n"
                "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n"
                "          private-key: ${{ secrets.OPENADAPT_RELEASE_APP_PRIVATE_KEY }}\n"
                "          owner: OpenAdaptAI\n"
                "          repositories: openadapt-desktop\n"
                "          permission-contents: write\n"
                "      - env:\n"
                "          GH_TOKEN: ${{ steps.release_app.outputs.token }}\n"
                "        run: gh release create ffmpeg-runtime-v1.2.3-r1\n"
            )

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
    assert value["plan_constraints"] == [
        {
            "repository": "openadapt-cloud",
            "visibility": "private",
            "mode": "audit-only",
            "managed": False,
            "current_plan": "GitHub Free organization",
            "constraint": (
                "GitHub artifact attestations for private repositories require "
                "GitHub Enterprise Cloud."
            ),
            "required_fallback": (
                "Keep the existing signed Ed25519 evidence envelope and public verifier "
                "until the organization has GitHub Enterprise Cloud."
            ),
            "apply_rule": "This tool must never mutate openadapt-cloud.",
        }
    ]


def test_lifecycle_identity_is_separate_and_least_privilege() -> None:
    value = load_config(CONFIG_PATH)
    release = value["release_identity"]
    lifecycle = value["lifecycle_identity"]
    assert release["app_slug"] == "openadapt-release"
    assert release["required_repository_permissions"] == [
        "Contents: write",
        "Metadata: read",
    ]
    assert release["repository_scope"] == [
        "OpenAdapt",
        "openadapt-agent",
        "openadapt-capture",
        "openadapt-desktop",
        "openadapt-evals",
        "openadapt-flow",
    ]
    assert release["repository_variables"] == {"app_id": "OPENADAPT_RELEASE_APP_ID"}
    assert release["private_key_secret"] == "OPENADAPT_RELEASE_APP_PRIVATE_KEY"
    assert release["private_key_environment_bindings"] == {
        "OpenAdapt": ["release-identity", "pypi"],
        "openadapt-agent": ["release-identity"],
        "openadapt-capture": ["release-identity", "pypi"],
        "openadapt-desktop": ["release-identity", "pypi", "native-release"],
        "openadapt-evals": ["release-identity", "pypi"],
        "openadapt-flow": ["release-identity", "pypi"],
    }
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
    assert lifecycle["private_key_secret"] == ("OPENADAPT_LIFECYCLE_APP_PRIVATE_KEY")
    assert lifecycle["private_key_environment_bindings"] == {
        ".github": [
            "production-lifecycle-activation",
            "qualification-authority-state",
            "qualification-revocation-state",
        ],
        "openadapt-evals": ["production-lifecycle-evidence"],
        "openadapt-ops": ["production-lifecycle-projection"],
    }
    assert lifecycle["workflow_paths"][".github"] == [
        ".github/workflows/production-lifecycle-activation.yml",
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
    assert docs["private_key_secret"] == "OPENADAPT_DOCS_APP_PRIVATE_KEY"
    assert docs["private_key_environment_bindings"] == {
        "openadapt-ops": ["production-docs-deploy"]
    }
    audit = value["dispatch_privilege_audit"]
    assert audit["openadapt_ops_main_protected"] is False
    assert set(audit["unprotected_operational_environments"]) == {
        "production-backup",
        "production-backup-monitor",
    }
    assert audit["lifecycle_app_installation"] == "absent"
    assert audit["docs_app_installation"] == "absent"


def test_lifecycle_environments_override_the_unchanged_default() -> None:
    value = load_config(CONFIG_PATH)
    assert value["environment_defaults"] == {
        "wait_timer": 0,
        "prevent_self_review": False,
        "can_admins_bypass": False,
    }
    expected = {
        ".github": [
            (
                "production-lifecycle-activation",
                ".github/workflows/production-lifecycle-activation.yml",
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
                "can_admins_bypass": False,
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

    assert all(
        environment["can_admins_bypass"] is False
        for repo in value["repositories"]
        for environment in (
            repo["release_environments"] + repo.get("lifecycle_environments", [])
        )
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
            "can_admins_bypass": False,
            "deployment_policies": [{"type": "branch", "name": "main"}],
            "exclusive_workflow": ".github/workflows/sync.yml",
        },
        {
            "name": "production-docs-deploy",
            "can_admins_bypass": False,
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
    assert "inputs\\.source_event" in sync["required_patterns"]
    assert "repo-updated" in sync["forbidden_patterns"]
    assert "scripts/validate_docs_sync\\.py" in sync["required_patterns"]

    projection = ops["lifecycle_workflows"][0]
    assert projection["path"] == ".github/workflows/production-lifecycle-projection.yml"
    for exact_pattern in (
        "inputs\\.candidate_admissions_sha256",
        "inputs\\.candidate_ledger_head_sha256",
        "inputs\\.idempotency_key",
        "scripts/prepare_production_lifecycle_projection\\.py",
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


def test_path_scoped_check_cannot_also_be_required() -> None:
    value = config()
    value["repositories"][0]["path_scoped_checks"].append(
        value["repositories"][0]["required_checks"][0]
    )
    with pytest.raises(PolicyError, match="path-scoped checks cannot be required"):
        validate_config(value)


def test_config_rejects_private_key_binding_or_admin_bypass_drift() -> None:
    value = config()
    value["release_identity"]["private_key_environment_bindings"]["OpenAdapt"].append(
        "unreviewed-release"
    )
    with pytest.raises(PolicyError, match="private-key bindings are not exact"):
        validate_config(value)

    value = config()
    value["repositories"][0]["release_environments"][0]["can_admins_bypass"] = True
    with pytest.raises(PolicyError, match="can_admins_bypass false"):
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

    web = next(
        item for item in value["repositories"] if item["name"] == "openadapt-web"
    )
    web_by_name = {item["name"]: item for item in desired_rulesets(value, web, actor)}
    assert web_by_name["OpenAdapt policy: release tag creation"]["bypass_actors"] == []


def test_plan_is_read_only_and_never_manages_private_cloud(
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
    assert all(repo["actions"] for repo in plan["repositories"])


@pytest.mark.parametrize(
    ("fixture_kwargs", "expected_code"),
    [
        ({"release_app_all_repositories": True}, "release_identity_repository_scope"),
        ({"release_app_extra_repository": True}, "release_identity_repository_scope"),
        (
            {"release_app_permissions_mismatch": True},
            "release_identity_permissions_mismatch",
        ),
    ],
)
def test_release_identity_requires_exact_public_scope_and_permissions(
    monkeypatch: pytest.MonkeyPatch,
    fixture_kwargs: dict[str, bool],
    expected_code: str,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(ReadOnlyFixtureGitHub(value, **fixture_kwargs), value)

    assert plan["safe_to_apply"] is False
    assert expected_code in {item["code"] for item in plan["global_blockers"]}


def test_missing_release_app_variable_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value,
            missing_variable=("openadapt-desktop", "OPENADAPT_RELEASE_APP_ID"),
        ),
        value,
    )

    desktop = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-desktop"
    )
    assert plan["safe_to_apply"] is False
    assert {item["code"] for item in desktop["blockers"]} >= {
        "openadapt-release_variable_missing"
    }


@pytest.mark.parametrize(
    ("repository", "environment", "secret_name", "expected_code"),
    [
        (
            "openadapt-desktop",
            "native-release",
            "OPENADAPT_RELEASE_APP_PRIVATE_KEY",
            "openadapt-release_environment_private_key_missing",
        ),
        (
            "openadapt-evals",
            "production-lifecycle-evidence",
            "OPENADAPT_LIFECYCLE_APP_PRIVATE_KEY",
            "openadapt-lifecycle_environment_private_key_missing",
        ),
        (
            "openadapt-ops",
            "production-docs-deploy",
            "OPENADAPT_DOCS_APP_PRIVATE_KEY",
            "openadapt-docs_environment_private_key_missing",
        ),
    ],
)
def test_missing_app_private_key_secret_keeps_plan_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    repository: str,
    environment: str,
    secret_name: str,
    expected_code: str,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value,
            missing_environment_secret=(repository, environment, secret_name),
        ),
        value,
    )

    target = next(repo for repo in plan["repositories"] if repo["name"] == repository)
    assert plan["safe_to_apply"] is False
    assert expected_code in {item["code"] for item in target["blockers"]}


@pytest.mark.parametrize(
    ("fixture_kwargs", "expected_code"),
    [
        (
            {
                "repository_secret": (
                    "OpenAdapt",
                    "OPENADAPT_RELEASE_APP_PRIVATE_KEY",
                )
            },
            "openadapt-release_repository_private_key_present",
        ),
        (
            {
                "repository_variable_shadow": (
                    "OpenAdapt",
                    "OPENADAPT_RELEASE_APP_PRIVATE_KEY",
                )
            },
            "openadapt-release_repository_private_key_variable_present",
        ),
        (
            {
                "environment_variable_shadow": (
                    "OpenAdapt",
                    "pypi",
                    "OPENADAPT_RELEASE_APP_PRIVATE_KEY",
                )
            },
            "openadapt-release_environment_private_key_variable_present",
        ),
        (
            {
                "extra_environment_secret": (
                    "OpenAdapt",
                    "unreviewed-release",
                    "OPENADAPT_RELEASE_APP_PRIVATE_KEY",
                )
            },
            "openadapt-release_environment_private_key_out_of_scope",
        ),
    ],
)
def test_private_key_metadata_must_match_exact_environment_bindings(
    monkeypatch: pytest.MonkeyPatch,
    fixture_kwargs: dict[str, Any],
    expected_code: str,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(ReadOnlyFixtureGitHub(value, **fixture_kwargs), value)
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert plan["safe_to_apply"] is False
    assert expected_code in {item["code"] for item in launcher["blockers"]}


@pytest.mark.parametrize(
    "fixture_kwargs",
    [
        {"admin_bypass_environment": ("openadapt-agent", "pypi")},
        {"omitted_admin_bypass_environment": ("openadapt-agent", "pypi")},
        {"missing_environment": ("openadapt-agent", "pypi")},
    ],
)
def test_admin_bypass_requires_one_time_ui_setup_and_emits_no_false_repair(
    monkeypatch: pytest.MonkeyPatch,
    fixture_kwargs: dict[str, Any],
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(ReadOnlyFixtureGitHub(value, **fixture_kwargs), value)
    agent = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-agent"
    )

    assert "environment_admin_bypass_not_disabled" in {
        item["code"] for item in agent["blockers"]
    }
    assert not any(
        action["kind"] == "put_environment" and action["environment"] == "pypi"
        for action in agent["actions"]
    )


def test_audited_main_drift_is_a_blocker(monkeypatch: pytest.MonkeyPatch) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, main_drift_repo="openadapt-flow"), value
    )
    flow = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-flow"
    )

    assert plan["safe_to_apply"] is False
    assert "audited_main_drift" in {item["code"] for item in flow["blockers"]}
    assert "audit_snapshot_advanced" not in {item["code"] for item in flow["warnings"]}


def test_plan_reads_workflows_by_audited_sha_and_detects_mid_audit_advance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    github = ReadOnlyFixtureGitHub(
        value, advance_main_during_plan_repo="openadapt-flow"
    )
    plan = build_plan(github, value)
    flow_policy = next(
        repo for repo in value["repositories"] if repo["name"] == "openadapt-flow"
    )
    flow = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-flow"
    )

    assert "audited_main_changed_during_plan" in {
        item["code"] for item in flow["blockers"]
    }
    assert any(
        path.endswith(f"?ref={flow_policy['audited_main_sha']}")
        and "/openadapt-flow/contents/.github/workflows/" in path
        for path in github.gets
    )
    assert not any(
        "/openadapt-flow/contents/.github/workflows/" in path
        and path.endswith("?ref=main")
        for path in github.gets
    )


def test_unprotected_existing_environment_produces_a_safe_repair_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value,
            null_deployment_policy_repo="openadapt-agent",
        ),
        value,
    )

    agent = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-agent"
    )
    assert "environment_admin_bypass_not_disabled" not in {
        item["code"] for item in agent["blockers"]
    }
    assert any(
        action["kind"] == "put_environment" and action["environment"] == "pypi"
        for action in agent["actions"]
    )


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
        "dispatch_workflow_accepts_privileged_app"
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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("on:\n  workflow_dispatch: {}\njobs: {}\n", {"workflow_dispatch"}),
        ("on: repository_dispatch\njobs: {}\n", {"repository_dispatch"}),
        (
            "on: [workflow_dispatch, repository_dispatch]\njobs: {}\n",
            {"workflow_dispatch", "repository_dispatch"},
        ),
    ],
)
def test_dispatch_trigger_parser_covers_yaml_forms(
    source: str, expected: set[str]
) -> None:
    document = _parse_workflow_document(
        source, "OpenAdaptAI", "openadapt-evals", ".github/workflows/test.yml"
    )
    assert _workflow_triggers(document) == expected


def test_malformed_workflow_yaml_blocks_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/complex-visual.yml"
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value,
            workflow_overrides={
                ("openadapt-evals", path): "on: [workflow_dispatch\njobs: {}\n"
            },
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert plan["safe_to_apply"] is False
    assert "dispatch_workflow_yaml_invalid" in {
        item["code"] for item in evals["blockers"]
    }


@pytest.mark.parametrize(
    "actor_login", ["openadapt-lifecycle[bot]", "openadapt-docs[bot]"]
)
def test_non_authorized_dispatch_rejects_each_privileged_app_actor(
    monkeypatch: pytest.MonkeyPatch, actor_login: str
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/complex-visual.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("openadapt-evals", path).replace(
        actor_login, "ordinary-user"
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-evals", path): source}
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert "dispatch_workflow_accepts_privileged_app" in {
        item["code"] for item in evals["blockers"]
    }


def test_non_authorized_dispatch_rejects_bypassed_job_condition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/complex-visual.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("openadapt-evals", path).replace(
        "      github.triggering_actor != 'openadapt-docs[bot]'\n",
        "      github.triggering_actor != 'openadapt-docs[bot]' || true\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-evals", path): source}
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert "dispatch_workflow_accepts_privileged_app" in {
        item["code"] for item in evals["blockers"]
    }


def test_non_authorized_dispatch_rejects_bypassed_shell_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/complex-visual.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    original = fixture._workflow_content("openadapt-evals", path)
    source = original.replace(
        "          test \"$TRIGGERING_ACTOR\" != 'openadapt-docs[bot]'\n",
        "          test \"$TRIGGERING_ACTOR\" != 'openadapt-docs[bot]' || true\n",
        1,
    )
    assert source != original
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-evals", path): source}
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert "dispatch_workflow_accepts_privileged_app" in {
        item["code"] for item in evals["blockers"]
    }


def test_non_authorized_dispatch_rejects_echo_only_shell_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/complex-visual.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("openadapt-evals", path).replace(
        '        run: |\n          test "$ACTOR"',
        '        run: |\n          echo test "$ACTOR"',
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-evals", path): source}
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert "dispatch_workflow_accepts_privileged_app" in {
        item["code"] for item in evals["blockers"]
    }


def test_non_authorized_dispatch_rejects_test_with_true_alternative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/complex-visual.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("openadapt-evals", path).replace(
        "          test \"$ACTOR\" != 'openadapt-lifecycle[bot]'\n",
        "          test \"$ACTOR\" != 'openadapt-lifecycle[bot]' -o 1 = 1\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-evals", path): source}
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert "dispatch_workflow_accepts_privileged_app" in {
        item["code"] for item in evals["blockers"]
    }


def test_non_authorized_dispatch_rejects_quoted_condition_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/complex-visual.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("openadapt-evals", path).replace(
        "      github.actor != 'openadapt-lifecycle[bot]' &&\n",
        "      contains(\"github.actor != 'openadapt-lifecycle[bot]'\", 'github') &&\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-evals", path): source}
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert "dispatch_workflow_accepts_privileged_app" in {
        item["code"] for item in evals["blockers"]
    }


def test_tag_only_exemption_rejects_quoted_condition_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    original = fixture._workflow_content("openadapt-evals", path)
    source = original.replace(
        "    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')\n",
        "    if: contains(\"github.event_name == 'push' refs/tags/\", 'github')\n",
        1,
    )
    assert source != original
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-evals", path): source}
        ),
        value,
    )
    evals = next(
        repo for repo in plan["repositories"] if repo["name"] == "openadapt-evals"
    )

    assert "dispatch_workflow_accepts_privileged_app" in {
        item["code"] for item in evals["blockers"]
    }


@pytest.mark.parametrize(
    ("repository", "path", "token_reference", "expected_code"),
    [
        (
            "openadapt-evals",
            ".github/workflows/production-lifecycle-evidence.yml",
            "steps.lifecycle-app.outputs.token",
            "lifecycle-only_workflow_semantic_contract",
        ),
        (
            "openadapt-ops",
            ".github/workflows/sync.yml",
            "steps.docs-app.outputs.token",
            "docs-only_workflow_semantic_contract",
        ),
    ],
)
def test_authorized_dispatch_effect_must_use_its_same_job_app_token(
    monkeypatch: pytest.MonkeyPatch,
    repository: str,
    path: str,
    token_reference: str,
    expected_code: str,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content(repository, path).replace(
        token_reference, "github.token"
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={(repository, path): source}),
        value,
    )
    target = next(repo for repo in plan["repositories"] if repo["name"] == repository)

    assert expected_code in {item["code"] for item in target["blockers"]}


def test_authorized_dispatch_rejects_quoted_condition_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/sync.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("openadapt-ops", path).replace(
        "      github.repository == 'OpenAdaptAI/openadapt-ops' &&\n",
        "      contains(\"github.repository == 'OpenAdaptAI/openadapt-ops'\", 'github') &&\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-ops", path): source}
        ),
        value,
    )
    ops = next(repo for repo in plan["repositories"] if repo["name"] == "openadapt-ops")

    assert "docs-only_workflow_semantic_contract" in {
        item["code"] for item in ops["blockers"]
    }


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("environment: production-docs-deploy", "environment: github-pages"),
        ("permission-actions: write", "permission-actions: read"),
        (
            "github.actor == 'openadapt-docs[bot]'",
            "github.actor == 'ordinary-user'",
        ),
    ],
)
def test_docs_dispatch_job_binds_actor_environment_and_app_permissions(
    monkeypatch: pytest.MonkeyPatch, old: str, new: str
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/sync.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("openadapt-ops", path).replace(old, new, 1)
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value, workflow_overrides={("openadapt-ops", path): source}
        ),
        value,
    )
    ops = next(repo for repo in plan["repositories"] if repo["name"] == "openadapt-ops")

    assert "docs-only_workflow_semantic_contract" in {
        item["code"] for item in ops["blockers"]
    }


def test_launcher_github_release_requires_same_job_release_app_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path)
    prefix, publish = source.split("  publish-pypi:\n", 1)
    publish = publish.replace("id: release-app", "id: unrelated-app", 1)
    plan = build_plan(
        ReadOnlyFixtureGitHub(
            value,
            workflow_overrides={
                ("OpenAdapt", path): prefix + "  publish-pypi:\n" + publish
            },
        ),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "github_release_app_token_not_bound" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_tag_push_requires_same_job_release_app_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          token: ${{ steps.release-app.outputs.token }}\n",
        "      - env:\n"
        "          APP_TOKEN: ${{ steps.release-app.outputs.token }}\n"
        "        run: echo App token is present\n"
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          token: ${{ github.token }}\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_app_token_not_bound" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_tag_push_accepts_explicit_app_authenticated_git_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          token: ${{ steps.release-app.outputs.token }}\n"
        "      - run: |\n"
        "          git tag -a v1.2.3 -m release\n"
        '          git push origin "refs/tags/v1.2.3"\n',
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          persist-credentials: false\n"
        "          token: ${{ steps.release-app.outputs.token }}\n"
        "      - env:\n"
        "          APP_TOKEN: ${{ steps.release-app.outputs.token }}\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          git tag -a v1.2.3 -m release\n"
        "          auth=$(printf 'x-access-token:%s' \"${APP_TOKEN}\" | base64 | tr -d '\\n')\n"
        "          export GIT_CONFIG_COUNT=1\n"
        "          export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader\n"
        '          export GIT_CONFIG_VALUE_0="AUTHORIZATION: basic ${auth}"\n'
        "          git push origin refs/tags/v1.2.3\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_app_token_not_bound" not in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_tag_push_rejects_decorative_auth_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          token: ${{ steps.release-app.outputs.token }}\n"
        "      - run: |\n"
        "          git tag -a v1.2.3 -m release\n"
        '          git push origin "refs/tags/v1.2.3"\n',
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          persist-credentials: false\n"
        "      - env:\n"
        "          APP_TOKEN: ${{ steps.release-app.outputs.token }}\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          echo 'x-access-token AUTHORIZATION:' \"${APP_TOKEN}\"\n"
        "          git tag -a v1.2.3 -m release\n"
        "          git push origin refs/tags/v1.2.3\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_app_token_not_bound" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_tag_push_rejects_reassigned_app_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          token: ${{ steps.release-app.outputs.token }}\n"
        "      - run: |\n"
        "          git tag -a v1.2.3 -m release\n"
        '          git push origin "refs/tags/v1.2.3"\n',
        "      - uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          persist-credentials: false\n"
        "      - env:\n"
        "          APP_TOKEN: ${{ steps.release-app.outputs.token }}\n"
        "          DEFAULT_TOKEN: ${{ github.token }}\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          APP_TOKEN="$DEFAULT_TOKEN"\n'
        "          auth=$(printf 'x-access-token:%s' \"$APP_TOKEN\" | base64)\n"
        "          export GIT_CONFIG_COUNT=1\n"
        "          export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader\n"
        '          export GIT_CONFIG_VALUE_0="AUTHORIZATION: basic ${auth}"\n'
        "          git tag -a v1.2.3 -m release\n"
        "          git push origin refs/tags/v1.2.3\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_app_token_not_bound" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_tag_push_rejects_checkout_credential_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "      - run: |\n"
        "          git tag -a v1.2.3 -m release\n"
        '          git push origin "refs/tags/v1.2.3"\n',
        "      - env:\n"
        "          DEFAULT_TOKEN: ${{ github.token }}\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          git remote set-url origin "https://x-access-token:${DEFAULT_TOKEN}@github.com/OpenAdaptAI/OpenAdapt.git"\n'
        "          git tag -a v1.2.3 -m release\n"
        "          git push origin refs/tags/v1.2.3\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_app_token_not_bound" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_tag_push_rejects_intervening_credential_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "      - run: |\n"
        "          git tag -a v1.2.3 -m release\n"
        '          git push origin "refs/tags/v1.2.3"\n',
        "      - env:\n"
        "          DEFAULT_TOKEN: ${{ github.token }}\n"
        '        run: git remote set-url origin "https://x-access-token:${DEFAULT_TOKEN}@github.com/OpenAdaptAI/OpenAdapt.git"\n'
        "      - run: |\n"
        "          git tag -a v1.2.3 -m release\n"
        '          git push origin "refs/tags/v1.2.3"\n',
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_app_token_not_bound" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_workflow_rejects_effect_named_but_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "        run: gh release create v1.2.3\n",
        "        name: gh release create v1.2.3\n"
        "        run: echo gh release create v1.2.3\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "github_release_effect_missing" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_workflow_rejects_echoed_tag_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    original = fixture._workflow_content("OpenAdapt", path)
    source = original.replace(
        "          git tag -a v1.2.3 -m release\n"
        '          git push origin "refs/tags/v1.2.3"\n',
        "          echo git tag -a v1.2.3 -m release\n"
        '          echo git push origin "refs/tags/v1.2.3"\n',
        1,
    )
    assert source != original
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_effect_missing" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_workflow_rejects_ignored_tag_push_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    original = fixture._workflow_content("OpenAdapt", path)
    source = original.replace(
        '          git push origin "refs/tags/v1.2.3"\n',
        '          git push origin "refs/tags/v1.2.3" || true\n',
        1,
    )
    assert source != original
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_effect_missing" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_workflow_rejects_continued_ignored_tag_push_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    original = fixture._workflow_content("OpenAdapt", path)
    source = original.replace(
        '          git push origin "refs/tags/v1.2.3"\n',
        ('          git push origin "refs/tags/v1.2.3" \\\\\n          || true\n'),
        1,
    )
    assert source != original
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_tag_effect_missing" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_workflow_rejects_ignored_github_release_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    original = fixture._workflow_content("OpenAdapt", path)
    source = original.replace(
        "        run: gh release create v1.2.3\n",
        "        run: gh release create v1.2.3 || true\n",
        1,
    )
    assert source != original
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "github_release_effect_missing" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_workflow_rejects_continued_ignored_github_release_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    original = fixture._workflow_content("OpenAdapt", path)
    source = original.replace(
        "        run: gh release create v1.2.3\n",
        (
            "        run: |\n"
            "          gh release create v1.2.3 \\\\\n"
            "          || true\n"
        ),
        1,
    )
    assert source != original
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "github_release_effect_missing" in {
        item["code"] for item in launcher["blockers"]
    }


def test_github_release_rejects_compound_token_expression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "          GH_TOKEN: ${{ steps.release-app.outputs.token }}\n",
        "          GH_TOKEN: ${{ steps.release-app.outputs.token || github.token }}\n",
        1,
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "github_release_app_token_not_bound" in {
        item["code"] for item in launcher["blockers"]
    }


def test_release_app_token_requires_exact_repository_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(
        "          repositories: OpenAdapt\n", "", 1
    )
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_effect_app_token_missing" in {
        item["code"] for item in launcher["blockers"]
    }


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            "          owner: OpenAdaptAI\n",
            "          owner: ${{ github.repository_owner && 'OtherOwner' }}\n",
        ),
        (
            "          repositories: OpenAdapt\n",
            "          repositories: ${{ github.event.repository.name && 'openadapt-ops' }}\n",
        ),
        (
            "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID }}\n",
            "          app-id: ${{ vars.OPENADAPT_RELEASE_APP_ID || vars.OTHER_APP_ID }}\n",
        ),
    ],
)
def test_release_app_token_rejects_compound_scope_expressions(
    monkeypatch: pytest.MonkeyPatch, old: str, new: str
) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    path = ".github/workflows/release-and-publish.yml"
    fixture = ReadOnlyFixtureGitHub(value)
    source = fixture._workflow_content("OpenAdapt", path).replace(old, new, 1)
    plan = build_plan(
        ReadOnlyFixtureGitHub(value, workflow_overrides={("OpenAdapt", path): source}),
        value,
    )
    launcher = next(
        repo for repo in plan["repositories"] if repo["name"] == "OpenAdapt"
    )

    assert "release_effect_app_token_missing" in {
        item["code"] for item in launcher["blockers"]
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
    assert {item["code"] for item in flow["blockers"]} == {"active_pull_request_checks"}


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


def test_apply_rechecks_every_main_before_first_mutation() -> None:
    value = config()
    audited = next(
        repo["audited_main_sha"]
        for repo in value["repositories"]
        if repo["name"] == "OpenAdapt"
    )
    plan = {
        "organization": "OpenAdaptAI",
        "repositories": [
            {
                "name": "OpenAdapt",
                "default_branch": "main",
                "main_sha": audited,
                "requires_environment_policy_prune": False,
                "actions": [
                    {
                        "kind": "create_ruleset",
                        "name": "test",
                        "payload": {"name": "test"},
                    }
                ],
            }
        ],
    }
    github = ReadOnlyFixtureGitHub(value, main_drift_repo="OpenAdapt")

    with pytest.raises(PolicyError, match="changed after preflight"):
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
