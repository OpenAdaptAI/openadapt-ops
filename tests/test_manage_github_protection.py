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
    ) -> None:
        self.config = config
        self.active_repo = active_repo
        self.path_filtered_repo = path_filtered_repo
        self.writes: list[tuple[str, str, Mapping[str, Any]]] = []
        self.by_name = {repo["name"]: repo for repo in config["repositories"]}

    def get(self, path: str, *, optional: bool = False) -> Any:
        if path == "/apps/openadapt-release":
            return {"id": 991122, "slug": "openadapt-release"}
        if path == "/users/abrichr":
            return {"id": 774615, "login": "abrichr"}
        if path == "/orgs/OpenAdaptAI/installations?per_page=100":
            return {
                "installations": [
                    {
                        "id": 551100,
                        "app_id": 991122,
                        "app_slug": "openadapt-release",
                        "repository_selection": "all",
                    }
                ]
            }
        parts = path.split("?")[0].split("/")
        if len(parts) >= 4 and parts[1] == "repos":
            name = parts[3]
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
                            {"name": "test", "status": "in_progress", "conclusion": None}
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
                return None
            if parts[4] == "contents":
                workflow = (
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
                if name == self.path_filtered_repo:
                    workflow += "pull_request:\n    paths-ignore:\n      - docs/**\n"
                return {
                    "type": "file",
                    "content": base64.b64encode(workflow.encode()).decode(),
                }
        raise AssertionError(f"unexpected GET {path}")

    def write(
        self, method: str, path: str, payload: Mapping[str, Any] | None = None
    ) -> Any:
        self.writes.append((method, path, payload or {}))
        return {}


def config() -> dict[str, Any]:
    value = load_config(CONFIG_PATH)
    value["release_identity"]["actor_id"] = 991122
    return value


def test_policy_has_only_the_reviewed_owned_repositories() -> None:
    value = load_config(CONFIG_PATH)
    assert {repo["name"] for repo in value["repositories"]} == {
        ".github",
        "OpenAdapt",
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


def test_plan_is_read_only_and_never_manages_private_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_active_pull_request_check_blocks_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    value = config()
    monkeypatch.setenv("OPENADAPT_RELEASE_APP_ID", "991122")
    plan = build_plan(ReadOnlyFixtureGitHub(value, active_repo="openadapt-flow"), value)
    flow = next(repo for repo in plan["repositories"] if repo["name"] == "openadapt-flow")
    assert plan["safe_to_apply"] is False
    assert flow["active_checks"] == [
        {"pull_request": 12, "name": "test", "status": "in_progress"}
    ]
    assert {item["code"] for item in flow["blockers"]} == {
        "active_pull_request_checks"
    }


def test_path_filtered_target_check_blocks_apply(monkeypatch: pytest.MonkeyPatch) -> None:
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
