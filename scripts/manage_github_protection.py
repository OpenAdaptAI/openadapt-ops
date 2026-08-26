#!/usr/bin/env python3
"""Plan, apply, and verify the OpenAdapt core GitHub protection policy.

The plan and verify commands only issue GET requests. The apply command needs a
fresh plan, an exact confirmation value, and an unchanged main commit for every
managed repository. The tool does not delete an environment deployment policy
unless the operator adds the explicit prune flag.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import yaml

API_VERSION = "2026-03-10"
PLAN_MAX_AGE_SECONDS = 900
EXPECTED_REPOSITORIES = {
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
ACTIVE_CHECK_STATES = {"queued", "in_progress", "pending", "requested", "waiting"}
MANAGED_RULESET_NAMES = (
    "OpenAdapt policy: protected main",
    "OpenAdapt policy: release tag creation",
    "OpenAdapt policy: immutable release tags",
)
EXPECTED_PRIVATE_KEY_BINDINGS = {
    "openadapt-release": {
        "OpenAdapt": ["release-identity", "pypi"],
        "openadapt-agent": ["release-identity"],
        "openadapt-capture": ["release-identity", "pypi"],
        "openadapt-desktop": ["release-identity", "pypi", "native-release"],
        "openadapt-evals": ["release-identity", "pypi"],
        "openadapt-flow": ["release-identity", "pypi"],
    },
    "openadapt-lifecycle": {
        ".github": [
            "production-lifecycle-activation",
            "qualification-authority-state",
            "qualification-revocation-state",
        ],
        "openadapt-evals": ["production-lifecycle-evidence"],
        "openadapt-ops": ["production-lifecycle-projection"],
    },
    "openadapt-docs": {"openadapt-ops": ["production-docs-deploy"]},
}
EXPECTED_TOKEN_REPOSITORY_BINDINGS = {
    "openadapt-release": {
        "OpenAdapt": ["OpenAdapt"],
        "openadapt-agent": ["openadapt-agent"],
        "openadapt-capture": ["openadapt-capture"],
        "openadapt-desktop": ["openadapt-desktop"],
        "openadapt-evals": ["openadapt-evals"],
        "openadapt-flow": ["openadapt-flow"],
    },
    "openadapt-lifecycle": {
        ".github": [".github"],
        "openadapt-evals": ["openadapt-evals"],
        "openadapt-ops": [".github", "openadapt-evals", "openadapt-ops"],
    },
    "openadapt-docs": {"openadapt-ops": ["openadapt-ops"]},
}


class PolicyError(RuntimeError):
    """The policy or live state is unsafe or invalid."""


class GitHubError(RuntimeError):
    """A GitHub CLI request failed."""


class GitHubClient(Protocol):
    def get(self, path: str, *, optional: bool = False) -> Any:
        """Return one GitHub REST response."""

    def write(
        self, method: str, path: str, payload: Mapping[str, Any] | None = None
    ) -> Any:
        """Issue one GitHub REST mutation."""


class GhApiClient:
    """Small fail-closed wrapper around ``gh api``."""

    def __init__(self, *, allow_writes: bool = False) -> None:
        self.allow_writes = allow_writes

    @staticmethod
    def require_auth() -> None:
        result = subprocess.run(
            ["gh", "auth", "status", "--hostname", "github.com"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise GitHubError(f"GitHub authentication is not valid: {detail}")

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        optional: bool = False,
    ) -> Any:
        if method != "GET" and not self.allow_writes:
            raise GitHubError(f"dry-run client refused {method} {path}")
        command = [
            "gh",
            "api",
            "--method",
            method,
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            f"X-GitHub-Api-Version: {API_VERSION}",
            path,
        ]
        stdin = None
        if payload is not None:
            command.extend(["--input", "-"])
            stdin = json.dumps(payload, sort_keys=True)
        result = subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if optional and ("HTTP 404" in detail or "Not Found" in detail):
                return None
            raise GitHubError(f"{method} {path} failed: {detail}")
        if not result.stdout.strip():
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise GitHubError(f"{method} {path} returned invalid JSON") from exc

    def get(self, path: str, *, optional: bool = False) -> Any:
        return self._request("GET", path, optional=optional)

    def write(
        self, method: str, path: str, payload: Mapping[str, Any] | None = None
    ) -> Any:
        if method not in {"POST", "PUT", "PATCH", "DELETE"}:
            raise GitHubError(f"unsupported write method: {method}")
        return self._request(method, path, payload)


@dataclass(frozen=True)
class ReleaseActor:
    actor_id: int
    app_slug: str


@dataclass(frozen=True)
class LifecycleActor:
    app_id: int
    actor_id: int
    actor_login: str
    installation_id: int


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot read policy config {path}: {exc}") from exc
    validate_config(data)
    return data


def _require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise PolicyError(f"{field} must be a list")
    return value


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise PolicyError("schema_version must be 1")
    if config.get("organization") != "OpenAdaptAI":
        raise PolicyError("organization must be OpenAdaptAI")
    live_audit = config.get("live_audit")
    if not isinstance(live_audit, Mapping):
        raise PolicyError("live_audit must be an object")
    for field in (
        "repository_ruleset_counts",
        "main_protected",
        "release_environment_state",
    ):
        values = live_audit.get(field)
        if not isinstance(values, Mapping) or set(values) != EXPECTED_REPOSITORIES:
            raise PolicyError(
                f"live_audit.{field} must cover the nine core repositories"
            )
    dispatch_audit = config.get("dispatch_privilege_audit")
    if not isinstance(dispatch_audit, Mapping):
        raise PolicyError("dispatch_privilege_audit must be an object")
    if dispatch_audit.get("openadapt_ops_main_protected") is not False:
        raise PolicyError("dispatch audit must record unprotected Ops main")
    if set(dispatch_audit.get("unprotected_operational_environments", {})) != {
        "production-backup",
        "production-backup-monitor",
    }:
        raise PolicyError("dispatch audit must record both backup environments")
    if dispatch_audit.get("lifecycle_app_installation") != "absent":
        raise PolicyError("dispatch audit must record the missing lifecycle App")
    if dispatch_audit.get("docs_app_installation") != "absent":
        raise PolicyError("dispatch audit must record the missing docs App")
    actions_id = config.get("github_actions_integration_id")
    if not isinstance(actions_id, int) or actions_id <= 0:
        raise PolicyError("github_actions_integration_id must be a positive integer")
    environment_defaults = config.get("environment_defaults")
    if environment_defaults != {
        "wait_timer": 0,
        "prevent_self_review": False,
        "can_admins_bypass": False,
    }:
        raise PolicyError("environment_defaults must define the reviewed release gate")

    release_identity = config.get("release_identity")
    if not isinstance(release_identity, Mapping):
        raise PolicyError("release_identity must be an object")
    if (
        release_identity.get("actor_type") != "Integration"
        or release_identity.get("app_slug") != "openadapt-release"
        or release_identity.get("bypass_mode") != "always"
    ):
        raise PolicyError("release_identity is not exact")
    if release_identity.get("required_repository_permissions") != [
        "Contents: write",
        "Metadata: read",
    ]:
        raise PolicyError("release_identity repository permissions are not exact")
    release_repository_scope = _require_list(
        release_identity.get("repository_scope"),
        "release_identity.repository_scope",
    )
    if (
        not all(isinstance(item, str) for item in release_repository_scope)
        or set(release_repository_scope)
        != {
            "OpenAdapt",
            "openadapt-agent",
            "openadapt-capture",
            "openadapt-desktop",
            "openadapt-evals",
            "openadapt-flow",
        }
        or len(release_repository_scope) != 6
    ):
        raise PolicyError("release_identity repository scope is not exact")
    if release_identity.get("repository_variables") != {
        "app_id": "OPENADAPT_RELEASE_APP_ID"
    }:
        raise PolicyError("release_identity repository variables are not exact")
    if (
        release_identity.get("private_key_secret")
        != "OPENADAPT_RELEASE_APP_PRIVATE_KEY"
    ):
        raise PolicyError("release_identity private-key secret is not exact")
    if (
        release_identity.get("private_key_environment_bindings")
        != (EXPECTED_PRIVATE_KEY_BINDINGS["openadapt-release"])
    ):
        raise PolicyError("release_identity private-key bindings are not exact")
    if (
        release_identity.get("token_repository_bindings")
        != EXPECTED_TOKEN_REPOSITORY_BINDINGS["openadapt-release"]
    ):
        raise PolicyError("release_identity token repository bindings are not exact")

    lifecycle_identity = config.get("lifecycle_identity")
    if not isinstance(lifecycle_identity, Mapping):
        raise PolicyError("lifecycle_identity must be an object")
    if lifecycle_identity.get("app_slug") != "openadapt-lifecycle":
        raise PolicyError("lifecycle_identity must use the openadapt-lifecycle App")
    if lifecycle_identity.get("actor_login") != "openadapt-lifecycle[bot]":
        raise PolicyError("lifecycle_identity actor login is not exact")
    if lifecycle_identity.get("ruleset_bypass") is not False:
        raise PolicyError("lifecycle_identity must not have a ruleset bypass")
    expected_lifecycle_scope = {".github", "openadapt-evals", "openadapt-ops"}
    lifecycle_scope = _require_list(
        lifecycle_identity.get("repository_scope"),
        "lifecycle_identity.repository_scope",
    )
    if set(lifecycle_scope) != expected_lifecycle_scope or len(lifecycle_scope) != 3:
        raise PolicyError("lifecycle_identity repository scope is not exact")
    if lifecycle_identity.get("required_repository_permissions") != [
        "Actions: write",
        "Metadata: read",
        "Pull requests: write",
    ]:
        raise PolicyError("lifecycle_identity repository permissions are not exact")
    if lifecycle_identity.get("forbidden_repository_permissions") != [
        "Contents: write"
    ]:
        raise PolicyError("lifecycle_identity must forbid Contents write")
    expected_lifecycle_environments = {
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
    expected_lifecycle_workflows = {
        repo: [path for _, path in environments]
        for repo, environments in expected_lifecycle_environments.items()
    }
    if lifecycle_identity.get("workflow_paths") != expected_lifecycle_workflows:
        raise PolicyError("lifecycle_identity workflow paths are not exact")
    if lifecycle_identity.get("repository_variables") != {
        "app_id": "OPENADAPT_LIFECYCLE_APP_ID",
        "actor_id": "OPENADAPT_LIFECYCLE_ACTOR_ID",
        "installation_id": "OPENADAPT_LIFECYCLE_INSTALLATION_ID",
    }:
        raise PolicyError("lifecycle_identity repository variables are not exact")
    if (
        lifecycle_identity.get("private_key_secret")
        != "OPENADAPT_LIFECYCLE_APP_PRIVATE_KEY"
    ):
        raise PolicyError("lifecycle_identity private-key secret is not exact")
    if (
        lifecycle_identity.get("private_key_environment_bindings")
        != (EXPECTED_PRIVATE_KEY_BINDINGS["openadapt-lifecycle"])
    ):
        raise PolicyError("lifecycle_identity private-key bindings are not exact")
    if (
        lifecycle_identity.get("token_repository_bindings")
        != EXPECTED_TOKEN_REPOSITORY_BINDINGS["openadapt-lifecycle"]
    ):
        raise PolicyError("lifecycle_identity token repository bindings are not exact")
    actions_write_risk = lifecycle_identity.get("actions_write_risk")
    if not isinstance(actions_write_risk, Mapping):
        raise PolicyError("lifecycle_identity must record the Actions write risk")
    if set(actions_write_risk.get("capabilities", [])) != {
        "Dispatch repository workflows",
        "Cancel or rerun workflow runs",
        "Delete workflow artifacts",
    }:
        raise PolicyError(
            "lifecycle_identity Actions write capabilities are incomplete"
        )
    for field in ("app_id", "actor_id", "installation_id"):
        value = lifecycle_identity.get(field)
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise PolicyError(f"lifecycle_identity.{field} must be null or positive")
        environment_field = f"{field}_environment"
        if not isinstance(lifecycle_identity.get(environment_field), str):
            raise PolicyError(f"lifecycle_identity.{environment_field} is required")

    docs_identity = config.get("docs_identity")
    if not isinstance(docs_identity, Mapping):
        raise PolicyError("docs_identity must be an object")
    if docs_identity.get("app_slug") != "openadapt-docs":
        raise PolicyError("docs_identity must use the openadapt-docs App")
    if docs_identity.get("actor_login") != "openadapt-docs[bot]":
        raise PolicyError("docs_identity actor login is not exact")
    if docs_identity.get("repository_scope") != ["openadapt-ops"]:
        raise PolicyError("docs_identity repository scope is not exact")
    if docs_identity.get("required_repository_permissions") != [
        "Actions: write",
        "Metadata: read",
        "Pull requests: write",
    ]:
        raise PolicyError("docs_identity repository permissions are not exact")
    if docs_identity.get("forbidden_repository_permissions") != ["Contents: write"]:
        raise PolicyError("docs_identity must forbid Contents write")
    if docs_identity.get("ruleset_bypass") is not False:
        raise PolicyError("docs_identity must not have a ruleset bypass")
    if docs_identity.get("workflow_paths") != {
        "openadapt-ops": ".github/workflows/sync.yml"
    }:
        raise PolicyError("docs_identity workflow path is not exact")
    if docs_identity.get("repository_variables") != {
        "app_id": "OPENADAPT_DOCS_APP_ID",
        "actor_id": "OPENADAPT_DOCS_ACTOR_ID",
        "installation_id": "OPENADAPT_DOCS_INSTALLATION_ID",
    }:
        raise PolicyError("docs_identity repository variables are not exact")
    if docs_identity.get("private_key_secret") != "OPENADAPT_DOCS_APP_PRIVATE_KEY":
        raise PolicyError("docs_identity private-key secret is not exact")
    if (
        docs_identity.get("private_key_environment_bindings")
        != (EXPECTED_PRIVATE_KEY_BINDINGS["openadapt-docs"])
    ):
        raise PolicyError("docs_identity private-key bindings are not exact")
    if (
        docs_identity.get("token_repository_bindings")
        != EXPECTED_TOKEN_REPOSITORY_BINDINGS["openadapt-docs"]
    ):
        raise PolicyError("docs_identity token repository bindings are not exact")
    for field in ("app_id", "actor_id", "installation_id"):
        value = docs_identity.get(field)
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise PolicyError(f"docs_identity.{field} must be null or positive")
        environment_field = f"{field}_environment"
        if not isinstance(docs_identity.get(environment_field), str):
            raise PolicyError(f"docs_identity.{environment_field} is required")

    repositories = _require_list(config.get("repositories"), "repositories")
    names = [repo.get("name") for repo in repositories if isinstance(repo, Mapping)]
    if set(names) != EXPECTED_REPOSITORIES or len(names) != len(EXPECTED_REPOSITORIES):
        raise PolicyError(
            "repositories must contain exactly the nine reviewed OpenAdapt core repositories"
        )

    for repo in repositories:
        if not isinstance(repo, Mapping):
            raise PolicyError("each repository policy must be an object")
        name = repo.get("name")
        if repo.get("visibility") != "public":
            raise PolicyError(f"{name}: managed repository must be public")
        if repo.get("default_branch") != "main":
            raise PolicyError(f"{name}: default_branch must be main")
        sha = repo.get("audited_main_sha")
        if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            raise PolicyError(f"{name}: audited_main_sha must be a full commit SHA")
        required = _require_list(repo.get("required_checks"), f"{name}.required_checks")
        scoped = _require_list(
            repo.get("path_scoped_checks"), f"{name}.path_scoped_checks"
        )
        if any(not isinstance(item, str) or not item for item in required + scoped):
            raise PolicyError(f"{name}: check names must be non-empty strings")
        if len(required) != len(set(required)):
            raise PolicyError(f"{name}: required_checks contains duplicates")
        overlap = set(required).intersection(scoped)
        if overlap:
            raise PolicyError(
                f"{name}: path-scoped checks cannot be required: {sorted(overlap)}"
            )
        tags = _require_list(
            repo.get("release_tag_patterns"), f"{name}.release_tag_patterns"
        )
        if not tags or any(
            not isinstance(pattern, str) or not pattern.startswith("refs/tags/")
            for pattern in tags
        ):
            raise PolicyError(f"{name}: release tag patterns must use refs/tags/")
        release_environments = _require_list(
            repo.get("release_environments"), f"{name}.release_environments"
        )
        lifecycle_environments = _require_list(
            repo.get("lifecycle_environments", []),
            f"{name}.lifecycle_environments",
        )
        environments = release_environments + lifecycle_environments
        environment_names = [item.get("name") for item in environments]
        if len(environment_names) != len(set(environment_names)):
            raise PolicyError(f"{name}: duplicate protected environment")
        for environment in environments:
            if not isinstance(environment.get("name"), str) or not environment["name"]:
                raise PolicyError(f"{name}: protected environment needs a name")
            if environment.get("can_admins_bypass") is not False:
                raise PolicyError(
                    f"{name}: protected environment must set can_admins_bypass false"
                )
            policies = _require_list(
                environment.get("deployment_policies"),
                f"{name}.{environment.get('name')}.deployment_policies",
            )
            if not policies:
                raise PolicyError(
                    f"{name}: protected environment needs a deployment policy"
                )
            for policy in policies:
                if policy.get("type") not in {"branch", "tag"} or not policy.get(
                    "name"
                ):
                    raise PolicyError(f"{name}: invalid environment deployment policy")
        for environment in lifecycle_environments:
            if environment.get("wait_timer") != 0:
                raise PolicyError(
                    f"{name}: lifecycle environment wait_timer must be zero"
                )
            if environment.get("prevent_self_review") is not True:
                raise PolicyError(
                    f"{name}: lifecycle environment must prevent self-review"
                )
            if environment.get("deployment_policies") != [
                {"type": "branch", "name": "main"}
            ]:
                raise PolicyError(
                    f"{name}: lifecycle environment must admit exact main"
                )
            expected_workflows = expected_lifecycle_workflows.get(name, [])
            if environment.get("exclusive_workflow") not in expected_workflows:
                raise PolicyError(
                    f"{name}: lifecycle environment workflow is not exact"
                )
        actual_lifecycle_environments = [
            (item.get("name"), item.get("exclusive_workflow"))
            for item in lifecycle_environments
        ]
        if actual_lifecycle_environments != expected_lifecycle_environments.get(
            name, []
        ):
            raise PolicyError(f"{name}: lifecycle environments are not exact")
        workflows = _require_list(
            repo.get("release_workflows"), f"{name}.release_workflows"
        )
        for workflow in workflows:
            effects = _require_list(
                workflow.get("required_effects"),
                f"{name}.{workflow.get('path')}.required_effects",
            )
            if any(
                effect not in {"tag-push", "github-release"} for effect in effects
            ) or len(effects) != len(set(effects)):
                raise PolicyError(f"{name}: release workflow effects are invalid")
        requires_release_identity = any(
            "release-identity" in pattern
            for workflow in workflows
            for pattern in workflow.get("required_patterns", [])
        )
        if requires_release_identity and "release-identity" not in environment_names:
            raise PolicyError(f"{name}: publishing repository needs release-identity")
        admission_workflows = _require_list(
            repo.get("admission_workflows", []), f"{name}.admission_workflows"
        )
        lifecycle_workflows = _require_list(
            repo.get("lifecycle_workflows", []), f"{name}.lifecycle_workflows"
        )
        expected_lifecycle_paths = expected_lifecycle_workflows.get(name, [])
        actual_lifecycle_paths = [item.get("path") for item in lifecycle_workflows]
        if not expected_lifecycle_paths and actual_lifecycle_paths:
            raise PolicyError(f"{name}: lifecycle workflow is outside the App scope")
        if actual_lifecycle_paths != expected_lifecycle_paths:
            raise PolicyError(f"{name}: lifecycle workflow path is not exact")
        all_workflows = workflows + admission_workflows + lifecycle_workflows
        configured_workflow_paths = {item.get("path") for item in all_workflows}
        for environment in environments:
            exclusive_workflow = environment.get("exclusive_workflow")
            if (
                exclusive_workflow
                and exclusive_workflow not in configured_workflow_paths
            ):
                raise PolicyError(
                    f"{name}: protected environment workflow is not registered"
                )
        dispatch_inventory = _require_list(
            repo.get("dispatch_workflow_inventory", []),
            f"{name}.dispatch_workflow_inventory",
        )
        dispatch_paths = [item.get("path") for item in dispatch_inventory]
        if len(dispatch_paths) != len(set(dispatch_paths)):
            raise PolicyError(f"{name}: dispatch workflow inventory has duplicates")
        if any(
            not isinstance(item.get("path"), str)
            or not item["path"].startswith(".github/workflows/")
            or item.get("mode")
            not in {"docs-only", "lifecycle-only", "reject-lifecycle-app"}
            for item in dispatch_inventory
        ):
            raise PolicyError(f"{name}: dispatch workflow inventory is invalid")
        lifecycle_dispatch_paths = [
            item["path"]
            for item in dispatch_inventory
            if item["mode"] == "lifecycle-only"
        ]
        if not expected_lifecycle_paths and lifecycle_dispatch_paths:
            raise PolicyError(f"{name}: lifecycle dispatch is outside the App scope")
        if lifecycle_dispatch_paths != expected_lifecycle_paths:
            raise PolicyError(f"{name}: lifecycle dispatch path is not exact")
        docs_dispatch_paths = [
            item["path"] for item in dispatch_inventory if item["mode"] == "docs-only"
        ]
        expected_docs_path = docs_identity["workflow_paths"].get(name)
        if expected_docs_path is None and docs_dispatch_paths:
            raise PolicyError(f"{name}: docs dispatch is outside the App scope")
        if expected_docs_path is not None and docs_dispatch_paths != [
            expected_docs_path
        ]:
            raise PolicyError(f"{name}: docs dispatch path is not exact")
        for workflow in all_workflows:
            path = workflow.get("path")
            if not isinstance(path, str) or not path.startswith(".github/workflows/"):
                raise PolicyError(f"{name}: invalid workflow path")
            for field in ("required_patterns", "forbidden_patterns"):
                patterns = _require_list(workflow.get(field), f"{name}.{path}.{field}")
                for pattern in patterns:
                    try:
                        re.compile(pattern)
                    except (TypeError, re.error) as exc:
                        raise PolicyError(
                            f"{name}: invalid workflow pattern {pattern!r}"
                        ) from exc

    constraints = _require_list(config.get("plan_constraints"), "plan_constraints")
    cloud = [
        item for item in constraints if item.get("repository") == "openadapt-cloud"
    ]
    if len(cloud) != 1 or cloud[0].get("managed") is not False:
        raise PolicyError("openadapt-cloud must exist once as an unmanaged constraint")
    if cloud[0].get("mode") != "audit-only":
        raise PolicyError("openadapt-cloud must remain audit-only")


def _resolve_release_actor(
    client: GitHubClient, config: Mapping[str, Any], blockers: list[dict[str, str]]
) -> ReleaseActor | None:
    identity = config["release_identity"]
    actor_id = identity.get("actor_id")
    source = "config"
    if actor_id is None:
        source = identity["actor_id_environment"]
        raw = os.environ.get(source)
        if raw:
            try:
                actor_id = int(raw)
            except ValueError:
                actor_id = None
    if not isinstance(actor_id, int) or actor_id <= 0:
        blockers.append(
            {
                "code": "release_identity_unresolved",
                "message": (
                    "Set OPENADAPT_RELEASE_APP_ID to the reviewed openadapt-release "
                    "GitHub App ID before apply."
                ),
            }
        )
        return None

    slug = identity["app_slug"]
    app = client.get(f"/apps/{quote(slug, safe='')}", optional=True)
    if not isinstance(app, Mapping):
        blockers.append(
            {
                "code": "release_identity_not_found",
                "message": f"GitHub App {slug!r} from {source} was not found.",
            }
        )
        return None
    if app.get("id") != actor_id or app.get("slug") != slug:
        blockers.append(
            {
                "code": "release_identity_mismatch",
                "message": f"GitHub App {slug!r} does not have actor ID {actor_id}.",
            }
        )
        return None
    owner = config["organization"]
    response = client.get(f"/orgs/{owner}/installations?per_page=100")
    installations = (
        response.get("installations", []) if isinstance(response, Mapping) else response
    )
    installation = next(
        (
            item
            for item in installations or []
            if item.get("app_id") == actor_id and item.get("app_slug") == slug
        ),
        None,
    )
    if installation is None:
        blockers.append(
            {
                "code": "release_identity_not_installed",
                "message": f"GitHub App {slug!r} is not installed for {owner}.",
            }
        )
        return None
    expected_permissions = {
        item.split(":", 1)[0].strip().lower().replace(" ", "_"): item.split(":", 1)[1]
        .strip()
        .lower()
        for item in identity["required_repository_permissions"]
    }
    if installation.get("permissions") != expected_permissions:
        blockers.append(
            {
                "code": "release_identity_permissions_mismatch",
                "message": (
                    f"GitHub App {slug!r} does not have the exact reviewed permissions."
                ),
            }
        )
        return None
    if installation.get("repository_selection") != "selected":
        blockers.append(
            {
                "code": "release_identity_repository_scope",
                "message": (
                    f"GitHub App {slug!r} must select only the six public package "
                    "repositories."
                ),
            }
        )
        return None
    repository_response = client.get(
        f"/user/installations/{installation['id']}/repositories?per_page=100"
    )
    installed_names = {
        item.get("name") for item in repository_response.get("repositories", [])
    }
    expected_names = set(identity["repository_scope"])
    if installed_names != expected_names:
        blockers.append(
            {
                "code": "release_identity_repository_scope",
                "message": (
                    f"GitHub App {slug!r} repository scope must be exactly: "
                    f"{', '.join(sorted(expected_names))}."
                ),
            }
        )
        return None
    return ReleaseActor(actor_id=actor_id, app_slug=slug)


def _identity_number(
    identity: Mapping[str, Any],
    field: str,
    blockers: list[dict[str, str]],
    identity_key: str,
) -> int | None:
    value = identity.get(field)
    source = "config"
    if value is None:
        source = identity[f"{field}_environment"]
        raw = os.environ.get(source)
        if raw:
            try:
                value = int(raw)
            except ValueError:
                value = None
    if not isinstance(value, int) or value <= 0:
        blockers.append(
            {
                "code": f"{identity_key}_{field}_unresolved",
                "message": (
                    f"Set {identity[f'{field}_environment']} to the reviewed "
                    f"{identity['app_slug']} {field.replace('_', ' ')}."
                ),
            }
        )
        return None
    return value


def _resolve_scoped_dispatch_actor(
    client: GitHubClient,
    config: Mapping[str, Any],
    blockers: list[dict[str, str]],
    identity_key: str,
) -> LifecycleActor | None:
    identity = config[identity_key]
    app_id = _identity_number(identity, "app_id", blockers, identity_key)
    actor_id = _identity_number(identity, "actor_id", blockers, identity_key)
    installation_id = _identity_number(
        identity, "installation_id", blockers, identity_key
    )
    if app_id is None or actor_id is None or installation_id is None:
        return None

    slug = identity["app_slug"]
    app = client.get(f"/apps/{quote(slug, safe='')}", optional=True)
    if not isinstance(app, Mapping):
        blockers.append(
            {
                "code": f"{identity_key}_app_not_found",
                "message": f"GitHub App {slug!r} was not found.",
            }
        )
        return None
    if app.get("id") != app_id or app.get("slug") != slug:
        blockers.append(
            {
                "code": f"{identity_key}_app_mismatch",
                "message": f"GitHub App {slug!r} does not have App ID {app_id}.",
            }
        )
        return None

    actor_login = identity["actor_login"]
    actor = client.get(f"/users/{quote(actor_login, safe='')}", optional=True)
    if not isinstance(actor, Mapping):
        blockers.append(
            {
                "code": f"{identity_key}_actor_not_found",
                "message": f"GitHub App actor {actor_login!r} was not found.",
            }
        )
        return None
    if actor.get("id") != actor_id or actor.get("login") != actor_login:
        blockers.append(
            {
                "code": f"{identity_key}_actor_mismatch",
                "message": (
                    f"GitHub App actor {actor_login!r} does not have actor ID {actor_id}."
                ),
            }
        )
        return None

    owner = config["organization"]
    response = client.get(f"/orgs/{owner}/installations?per_page=100")
    installations = (
        response.get("installations", []) if isinstance(response, Mapping) else response
    )
    installation = next(
        (
            item
            for item in installations or []
            if item.get("id") == installation_id
            and item.get("app_id") == app_id
            and item.get("app_slug") == slug
        ),
        None,
    )
    if installation is None:
        blockers.append(
            {
                "code": f"{identity_key}_installation_not_found",
                "message": (
                    f"GitHub App {slug!r} installation {installation_id} was not found "
                    f"for {owner}."
                ),
            }
        )
        return None

    expected_permissions = {
        item.split(":", 1)[0].strip().lower().replace(" ", "_"): item.split(":", 1)[1]
        .strip()
        .lower()
        for item in identity["required_repository_permissions"]
    }
    if installation.get("permissions") != expected_permissions:
        blockers.append(
            {
                "code": f"{identity_key}_permissions_mismatch",
                "message": (
                    f"GitHub App {slug!r} does not have the exact reviewed permissions."
                ),
            }
        )
        return None
    if installation.get("repository_selection") != "selected":
        blockers.append(
            {
                "code": f"{identity_key}_repository_scope_mismatch",
                "message": f"GitHub App {slug!r} must use an exact selected-repository scope.",
            }
        )
        return None
    repository_response = client.get(
        f"/user/installations/{installation_id}/repositories?per_page=100"
    )
    installed_names = {
        item.get("name") for item in repository_response.get("repositories", [])
    }
    expected_names = set(identity["repository_scope"])
    if installed_names != expected_names:
        blockers.append(
            {
                "code": f"{identity_key}_repository_scope_mismatch",
                "message": (
                    f"GitHub App {slug!r} repository scope must be exactly: "
                    f"{', '.join(sorted(expected_names))}."
                ),
            }
        )
        return None
    return LifecycleActor(
        app_id=app_id,
        actor_id=actor_id,
        actor_login=actor_login,
        installation_id=installation_id,
    )


def _resolve_lifecycle_actor(
    client: GitHubClient,
    config: Mapping[str, Any],
    blockers: list[dict[str, str]],
) -> LifecycleActor | None:
    return _resolve_scoped_dispatch_actor(
        client, config, blockers, "lifecycle_identity"
    )


def _resolve_docs_actor(
    client: GitHubClient,
    config: Mapping[str, Any],
    blockers: list[dict[str, str]],
) -> LifecycleActor | None:
    return _resolve_scoped_dispatch_actor(client, config, blockers, "docs_identity")


def _verify_reviewer(
    client: GitHubClient, config: Mapping[str, Any], blockers: list[dict[str, str]]
) -> None:
    reviewer = config["environment_reviewer"]
    user = client.get(f"/users/{quote(reviewer['login'], safe='')}", optional=True)
    if not isinstance(user, Mapping) or user.get("id") != reviewer.get("id"):
        blockers.append(
            {
                "code": "environment_reviewer_mismatch",
                "message": (
                    f"Environment reviewer {reviewer['login']!r} does not have "
                    f"reviewed ID {reviewer['id']}."
                ),
            }
        )


def _pull_request_rule(
    config: Mapping[str, Any], repo: Mapping[str, Any]
) -> dict[str, Any]:
    defaults = config["main_rule_defaults"]
    return {
        "type": "pull_request",
        "parameters": {
            "allowed_merge_methods": defaults["allowed_merge_methods"],
            "dismiss_stale_reviews_on_push": defaults["dismiss_stale_reviews"],
            "require_code_owner_review": repo["require_code_owner_review"],
            "require_last_push_approval": defaults["require_last_push_approval"],
            "required_approving_review_count": defaults["required_approvals"],
            "required_review_thread_resolution": defaults[
                "require_review_thread_resolution"
            ],
        },
    }


def desired_rulesets(
    config: Mapping[str, Any], repo: Mapping[str, Any], actor: ReleaseActor | None
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        _pull_request_rule(config, repo),
    ]
    checks = repo["required_checks"]
    if checks:
        rules.append(
            {
                "type": "required_status_checks",
                "parameters": {
                    "do_not_enforce_on_create": False,
                    "strict_required_status_checks_policy": config[
                        "main_rule_defaults"
                    ]["strict_status_checks"],
                    "required_status_checks": [
                        {
                            "context": context,
                            "integration_id": config["github_actions_integration_id"],
                        }
                        for context in checks
                    ],
                },
            }
        )

    main = {
        "name": MANAGED_RULESET_NAMES[0],
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": rules,
    }
    immutable = {
        "name": MANAGED_RULESET_NAMES[2],
        "target": "tag",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {
            "ref_name": {"include": repo["release_tag_patterns"], "exclude": []}
        },
        "rules": [
            {"type": "update", "parameters": {"update_allows_fetch_and_merge": False}},
            {"type": "deletion"},
            {"type": "non_fast_forward"},
        ],
    }
    result = [main, immutable]
    if actor is not None:
        bypass_actors = []
        if repo["name"] in config["release_identity"]["repository_scope"]:
            bypass_actors = [
                {
                    "actor_id": actor.actor_id,
                    "actor_type": "Integration",
                    "bypass_mode": config["release_identity"]["bypass_mode"],
                }
            ]
        result.append(
            {
                "name": MANAGED_RULESET_NAMES[1],
                "target": "tag",
                "enforcement": "active",
                "bypass_actors": bypass_actors,
                "conditions": {
                    "ref_name": {
                        "include": repo["release_tag_patterns"],
                        "exclude": [],
                    }
                },
                "rules": [{"type": "creation"}],
            }
        )
    return result


def desired_environment(
    config: Mapping[str, Any], environment: Mapping[str, Any]
) -> dict[str, Any]:
    reviewer = config["environment_reviewer"]
    defaults = config["environment_defaults"]
    return {
        "wait_timer": environment.get("wait_timer", defaults["wait_timer"]),
        "prevent_self_review": environment.get(
            "prevent_self_review", defaults["prevent_self_review"]
        ),
        "reviewers": [{"type": reviewer["type"], "id": reviewer["id"]}],
        "deployment_branch_policy": {
            "protected_branches": False,
            "custom_branch_policies": True,
        },
    }


def _normalize_ruleset(value: Mapping[str, Any]) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    for rule in value.get("rules", []):
        normalized: dict[str, Any] = {"type": rule.get("type")}
        parameters = rule.get("parameters")
        if rule.get("type") == "pull_request" and isinstance(parameters, Mapping):
            normalized["parameters"] = {
                key: parameters.get(key)
                for key in (
                    "allowed_merge_methods",
                    "dismiss_stale_reviews_on_push",
                    "require_code_owner_review",
                    "require_last_push_approval",
                    "required_approving_review_count",
                    "required_review_thread_resolution",
                )
            }
        elif rule.get("type") == "required_status_checks" and isinstance(
            parameters, Mapping
        ):
            checks = [
                {
                    "context": check.get("context"),
                    "integration_id": check.get("integration_id"),
                }
                for check in parameters.get("required_status_checks", [])
            ]
            normalized["parameters"] = {
                "do_not_enforce_on_create": parameters.get(
                    "do_not_enforce_on_create", False
                ),
                "strict_required_status_checks_policy": parameters.get(
                    "strict_required_status_checks_policy"
                ),
                "required_status_checks": sorted(
                    checks, key=lambda item: item["context"]
                ),
            }
        elif rule.get("type") == "update" and isinstance(parameters, Mapping):
            normalized["parameters"] = {
                "update_allows_fetch_and_merge": parameters.get(
                    "update_allows_fetch_and_merge"
                )
            }
        rules.append(normalized)
    rules.sort(key=lambda item: (item["type"], json.dumps(item, sort_keys=True)))
    bypass = [
        {
            "actor_id": item.get("actor_id"),
            "actor_type": item.get("actor_type"),
            "bypass_mode": item.get("bypass_mode"),
        }
        for item in value.get("bypass_actors", [])
    ]
    bypass.sort(key=lambda item: json.dumps(item, sort_keys=True))
    ref_name = value.get("conditions", {}).get("ref_name", {})
    return {
        "name": value.get("name"),
        "target": value.get("target"),
        "enforcement": value.get("enforcement"),
        "bypass_actors": bypass,
        "conditions": {
            "ref_name": {
                "include": sorted(ref_name.get("include", [])),
                "exclude": sorted(ref_name.get("exclude", [])),
            }
        },
        "rules": rules,
    }


def _normalize_environment(value: Mapping[str, Any]) -> dict[str, Any]:
    reviewer_rule = next(
        (
            rule
            for rule in value.get("protection_rules", [])
            if rule.get("type") == "required_reviewers"
        ),
        {},
    )
    reviewers = []
    for item in reviewer_rule.get("reviewers", []):
        identity = item.get("reviewer", {})
        reviewers.append({"type": item.get("type"), "id": identity.get("id")})
    reviewers.sort(key=lambda item: (item["type"], item["id"]))
    wait_rule = next(
        (
            rule
            for rule in value.get("protection_rules", [])
            if rule.get("type") == "wait_timer"
        ),
        {},
    )
    deployment = value.get("deployment_branch_policy") or {}
    return {
        "wait_timer": wait_rule.get("wait_timer", 0),
        "prevent_self_review": reviewer_rule.get("prevent_self_review", False),
        "reviewers": reviewers,
        "deployment_branch_policy": {
            "protected_branches": deployment.get("protected_branches"),
            "custom_branch_policies": deployment.get("custom_branch_policies"),
        },
    }


def _workflow_text(
    client: GitHubClient, owner: str, repo: str, path: str, ref: str
) -> str | None:
    encoded_path = quote(path, safe="/")
    response = client.get(
        f"/repos/{owner}/{repo}/contents/{encoded_path}?ref={quote(ref, safe='')}",
        optional=True,
    )
    if not isinstance(response, Mapping) or response.get("type") != "file":
        return None
    try:
        return base64.b64decode(response["content"]).decode("utf-8")
    except (KeyError, ValueError, UnicodeDecodeError) as exc:
        raise GitHubError(f"cannot decode {owner}/{repo}/{path}") from exc


def _parse_workflow_document(
    content: str, owner: str, repo: str, path: str
) -> Mapping[str, Any]:
    try:
        document = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise PolicyError(
            f"{owner}/{repo}:{path}: malformed workflow YAML: {exc}"
        ) from exc
    if not isinstance(document, Mapping):
        raise PolicyError(f"{owner}/{repo}:{path}: workflow YAML must be an object")
    jobs = document.get("jobs")
    if jobs is not None and not isinstance(jobs, Mapping):
        raise PolicyError(f"{owner}/{repo}:{path}: workflow jobs must be an object")
    return document


def _workflow_triggers(document: Mapping[str, Any]) -> set[str]:
    trigger = document.get("on", document.get(True))
    if isinstance(trigger, str):
        return {trigger}
    if isinstance(trigger, list):
        if not all(isinstance(item, str) for item in trigger):
            raise PolicyError("workflow trigger list must contain only names")
        return set(trigger)
    if isinstance(trigger, Mapping):
        if not all(isinstance(item, str) for item in trigger):
            raise PolicyError("workflow trigger map must contain only names")
        return set(trigger)
    raise PolicyError("workflow must declare a valid trigger")


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        result: list[str] = []
        for key, item in value.items():
            if isinstance(key, str):
                result.append(key)
            result.extend(_all_strings(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_all_strings(item))
        return result
    return []


def _job_environment(job: Mapping[str, Any]) -> str | None:
    environment = job.get("environment")
    if isinstance(environment, str):
        return environment
    if isinstance(environment, Mapping) and isinstance(environment.get("name"), str):
        return environment["name"]
    return None


def _job_needs(job: Mapping[str, Any]) -> set[str]:
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    if isinstance(needs, list) and all(isinstance(item, str) for item in needs):
        return set(needs)
    return set()


def _job_steps(job: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    steps = job.get("steps", [])
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, Mapping)]


def _references_expression(value: Any, reference: str) -> bool:
    return isinstance(value, str) and reference in re.sub(r"\s+", "", value)


def _is_exact_expression(value: Any, reference: str) -> bool:
    return (
        isinstance(value, str) and re.sub(r"\s+", "", value) == f"${{{{{reference}}}}}"
    )


def _matching_app_token_step_ids(
    job: Mapping[str, Any],
    identity: Mapping[str, Any],
    owner: str,
    repository_name: str,
) -> set[str]:
    required_permissions = {
        permission.split(":", 1)[0].strip().lower().replace(" ", "-"): permission.split(
            ":", 1
        )[1]
        .strip()
        .lower()
        for permission in identity["required_repository_permissions"]
        if permission.split(":", 1)[0].strip().lower() != "metadata"
    }
    app_id_name = identity["repository_variables"]["app_id"]
    private_key_name = identity["private_key_secret"]
    expected_repositories = set(identity["token_repository_bindings"][repository_name])
    matching: set[str] = set()
    for step in _job_steps(job):
        uses = step.get("uses")
        inputs = step.get("with")
        step_id = step.get("id")
        if (
            not isinstance(uses, str)
            or not uses.startswith("actions/create-github-app-token@")
            or not isinstance(inputs, Mapping)
            or not isinstance(step_id, str)
            or not step_id
        ):
            continue
        if not _is_exact_expression(inputs.get("app-id"), f"vars.{app_id_name}"):
            continue
        if not _is_exact_expression(
            inputs.get("private-key"), f"secrets.{private_key_name}"
        ):
            continue
        token_owner = inputs.get("owner")
        if token_owner != owner and not _is_exact_expression(
            token_owner, "github.repository_owner"
        ):
            continue
        repositories_input = inputs.get("repositories")
        if expected_repositories == {repository_name} and _is_exact_expression(
            repositories_input, "github.event.repository.name"
        ):
            token_repositories = {repository_name}
        elif isinstance(repositories_input, str) and "${{" not in repositories_input:
            token_repositories = {
                item for item in re.split(r"[\s,]+", repositories_input.strip()) if item
            }
        else:
            continue
        if token_repositories != expected_repositories:
            continue
        if any(
            inputs.get(f"permission-{name}") != level
            for name, level in required_permissions.items()
        ):
            continue
        matching.add(step_id)
    return matching


def _token_references(step_ids: Iterable[str]) -> set[str]:
    return {f"steps.{step_id}.outputs.token" for step_id in step_ids}


def _step_uses_token(step: Mapping[str, Any], references: set[str]) -> bool:
    return any(
        _references_expression(value, reference)
        for value in _all_strings(step)
        for reference in references
    )


def _shell_command_match(run: str, command_pattern: str) -> re.Match[str] | None:
    match = re.search(rf"(?m)^[ \t]*{command_pattern}", run)
    if match is None:
        return None
    line_end = run.find("\n", match.start())
    line = run[match.start() :] if line_end == -1 else run[match.start() : line_end]
    # A line continuation can move a fail-open operator to a later physical line.
    # Required release effects stay on one physical line so the complete command
    # is available to this validator.
    if re.search(r"\\\s*(?:#.*)?$", line):
        return None
    if re.search(r"\|\||;|(?<!\\)\|(?!\|)|&\s*(?:#.*)?$", line):
        return None
    return match


def _checkout_persists_app_token(step: Mapping[str, Any], references: set[str]) -> bool:
    uses = step.get("uses")
    inputs = step.get("with")
    if (
        not isinstance(uses, str)
        or not uses.startswith("actions/checkout@")
        or not isinstance(inputs, Mapping)
    ):
        return False
    if not any(
        _is_exact_expression(inputs.get("token"), reference) for reference in references
    ):
        return False
    persist_credentials = inputs.get("persist-credentials", True)
    return (
        persist_credentials is not False and str(persist_credentials).lower() != "false"
    )


def _push_step_binds_app_token(step: Mapping[str, Any], references: set[str]) -> bool:
    run = step.get("run")
    environment = step.get("env")
    if not isinstance(run, str) or not isinstance(environment, Mapping):
        return False
    token_names = {
        name
        for name, value in environment.items()
        if isinstance(name, str)
        and any(_is_exact_expression(value, reference) for reference in references)
    }
    if not token_names:
        return False
    push = _shell_command_match(run, r"git\s+push\b")
    if push is None:
        return False
    binding = run[: push.start()]
    if re.search(r"(?m)^\s*set\s+-euo\s+pipefail\s*$", binding) is None:
        return False
    key_indexes = set(
        re.findall(
            r"GIT_CONFIG_KEY_([0-9]+)=['\"]?http\.https://github\.com/\.extraheader",
            binding,
        )
    )
    if not key_indexes:
        return False
    for token_name in token_names:
        if re.search(
            rf"(?m)^\s*(?:(?:export|readonly)\s+)?{re.escape(token_name)}\s*=",
            binding,
        ):
            continue
        token_reference = rf'["\']?\$\{{?{re.escape(token_name)}\}}?["\']?'
        assignment = re.search(
            rf"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)=\$\(\s*printf\s+"
            rf"['\"]x-access-token:%s['\"]\s+{token_reference}\s*\|"
            rf"[^;\n]*\bbase64\b[^;\n]*\)\s*$",
            binding,
        )
        if assignment is None:
            continue
        auth_variable = assignment.group(1)
        for index in key_indexes:
            if re.search(
                rf"GIT_CONFIG_VALUE_{index}=['\"]?AUTHORIZATION:\s*basic\s+"
                rf"\$\{{?{re.escape(auth_variable)}\}}?",
                binding,
                flags=re.IGNORECASE,
            ):
                return True
    return False


def _step_mutates_git_auth(step: Mapping[str, Any]) -> bool:
    run = step.get("run")
    return (
        isinstance(run, str)
        and re.search(
            r"\bgit\s+remote\s+(?:add|remove|rename|set-url)\b|"
            r"\bgit\s+config\b[^\n]*(?:extraheader|credential\.helper)|"
            r"\bGIT_CONFIG_(?:COUNT|KEY_[0-9]+|VALUE_[0-9]+)\b|"
            r"\bunset\b[^\n]*(?:TOKEN|AUTH|GIT_CONFIG)",
            run,
            flags=re.IGNORECASE,
        )
        is not None
    )


def _tag_pushes_use_app_token(job: Mapping[str, Any], token_step_ids: set[str]) -> bool:
    available_references: set[str] = set()
    persisted_app_credential = False
    saw_push = False
    for step in _job_steps(job):
        step_id = step.get("id")
        if isinstance(step_id, str) and step_id in token_step_ids:
            available_references.add(f"steps.{step_id}.outputs.token")

        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith("actions/checkout@"):
            persisted_app_credential = _checkout_persists_app_token(
                step, available_references
            )
        elif persisted_app_credential and isinstance(uses, str):
            persisted_app_credential = False

        run = step.get("run")
        mutates_persisted_auth = _step_mutates_git_auth(step)
        if (
            not isinstance(run, str)
            or _shell_command_match(run, r"git\s+push\b") is None
        ):
            if persisted_app_credential and mutates_persisted_auth:
                persisted_app_credential = False
            continue
        saw_push = True
        direct_binding = _push_step_binds_app_token(step, available_references)
        if (
            not persisted_app_credential or mutates_persisted_auth
        ) and not direct_binding:
            return False
    return saw_push


def _release_workflow_semantic_blockers(
    client: GitHubClient,
    owner: str,
    repo: Mapping[str, Any],
    identity: Mapping[str, Any],
    ref: str,
) -> list[dict[str, str]]:
    if repo["name"] not in identity["repository_scope"]:
        return []
    allowed_environments = set(
        identity["private_key_environment_bindings"][repo["name"]]
    )
    blockers: list[dict[str, str]] = []
    for workflow in repo.get("release_workflows", []):
        path = workflow["path"]
        required_effects = set(workflow["required_effects"])
        requires_tag_effect = "tag-push" in required_effects
        requires_release_effect = "github-release" in required_effects
        content = _workflow_text(client, owner, repo["name"], path, ref)
        if content is None:
            continue
        try:
            document = _parse_workflow_document(content, owner, repo["name"], path)
        except PolicyError:
            continue
        jobs = document.get("jobs", {})
        saw_tag_effect = False
        saw_release_effect = False
        for job_name, job in jobs.items():
            if not isinstance(job_name, str) or not isinstance(job, Mapping):
                continue
            run_steps = [
                step["run"]
                for step in _job_steps(job)
                if isinstance(step.get("run"), str)
            ]
            has_tag_effect = bool(
                any(_shell_command_match(run, r"git\s+tag\b") for run in run_steps)
                and any(_shell_command_match(run, r"git\s+push\b") for run in run_steps)
            )
            release_steps = [
                step
                for step in _job_steps(job)
                if isinstance(step.get("run"), str)
                if _shell_command_match(
                    step["run"], r"gh\s+release\s+(?:create|edit|upload)\b"
                )
            ]
            saw_tag_effect = saw_tag_effect or has_tag_effect
            saw_release_effect = saw_release_effect or bool(release_steps)
            if not has_tag_effect and not release_steps:
                continue
            environment = _job_environment(job)
            if environment not in allowed_environments:
                blockers.append(
                    {
                        "code": "release_effect_environment_mismatch",
                        "message": (
                            f"{repo['name']}:{path}:{job_name}: release effect must run "
                            "in an exact release private-key environment."
                        ),
                    }
                )
            token_step_ids = _matching_app_token_step_ids(
                job, identity, owner, repo["name"]
            )
            token_references = _token_references(token_step_ids)
            if not token_step_ids:
                blockers.append(
                    {
                        "code": "release_effect_app_token_missing",
                        "message": (
                            f"{repo['name']}:{path}:{job_name}: release effect needs a "
                            "same-job token from the exact Release App inputs."
                        ),
                    }
                )
                continue
            if has_tag_effect and not _tag_pushes_use_app_token(job, token_step_ids):
                blockers.append(
                    {
                        "code": "release_tag_app_token_not_bound",
                        "message": (
                            f"{repo['name']}:{path}:{job_name}: tag creation does not "
                            "bind its push to the same-job Release App token."
                        ),
                    }
                )
            for step in release_steps:
                environment_values = step.get("env", {})
                gh_token = (
                    environment_values.get("GH_TOKEN")
                    if isinstance(environment_values, Mapping)
                    else None
                )
                if not any(
                    _is_exact_expression(gh_token, reference)
                    for reference in token_references
                ):
                    blockers.append(
                        {
                            "code": "github_release_app_token_not_bound",
                            "message": (
                                f"{repo['name']}:{path}:{job_name}: each GitHub Release "
                                "create, edit, or upload step must bind GH_TOKEN to the "
                                "same-job Release App output."
                            ),
                        }
                    )
        if requires_tag_effect and not saw_tag_effect:
            blockers.append(
                {
                    "code": "release_tag_effect_missing",
                    "message": (
                        f"{repo['name']}:{path}: no run step creates and pushes the "
                        "release tag."
                    ),
                }
            )
        if requires_release_effect and not saw_release_effect:
            blockers.append(
                {
                    "code": "github_release_effect_missing",
                    "message": (
                        f"{repo['name']}:{path}: no run step creates, edits, or uploads "
                        "the GitHub Release."
                    ),
                }
            )
    return blockers


def _workflow_contract_blockers(
    client: GitHubClient,
    owner: str,
    repo: Mapping[str, Any],
    contract_field: str,
    code_prefix: str,
    ref: str,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for workflow in repo.get(contract_field, []):
        path = workflow["path"]
        content = _workflow_text(client, owner, repo["name"], path, ref)
        if content is None:
            blockers.append(
                {
                    "code": f"{code_prefix}_workflow_missing",
                    "message": f"{repo['name']}: {path} does not exist on main.",
                }
            )
            continue
        try:
            _parse_workflow_document(content, owner, repo["name"], path)
        except PolicyError as exc:
            blockers.append(
                {
                    "code": f"{code_prefix}_workflow_yaml_invalid",
                    "message": str(exc),
                }
            )
            continue
        for pattern in workflow["required_patterns"]:
            if re.search(pattern, content) is None:
                blockers.append(
                    {
                        "code": f"{code_prefix}_workflow_contract_missing",
                        "message": f"{repo['name']}: {path} does not match {pattern!r}.",
                    }
                )
        for pattern in workflow["forbidden_patterns"]:
            if re.search(pattern, content) is not None:
                blockers.append(
                    {
                        "code": f"{code_prefix}_workflow_forbidden_pattern",
                        "message": f"{repo['name']}: {path} still matches {pattern!r}.",
                    }
                )
    return blockers


def _dispatch_identity_variable_blockers(
    client: GitHubClient,
    owner: str,
    repo: Mapping[str, Any],
    identity: Mapping[str, Any],
    actor: LifecycleActor | None,
) -> list[dict[str, str]]:
    if repo["name"] not in identity["workflow_paths"] or actor is None:
        return []
    blockers: list[dict[str, str]] = []
    expected_values = {
        identity["repository_variables"]["app_id"]: actor.app_id,
        identity["repository_variables"]["actor_id"]: actor.actor_id,
        identity["repository_variables"]["installation_id"]: actor.installation_id,
    }
    for variable_name, expected in expected_values.items():
        variable = client.get(
            (
                f"/repos/{owner}/{repo['name']}/actions/variables/"
                f"{quote(variable_name, safe='')}"
            ),
            optional=True,
        )
        if not isinstance(variable, Mapping):
            blockers.append(
                {
                    "code": f"{identity['app_slug']}_variable_missing",
                    "message": f"{repo['name']}: Actions variable {variable_name} is missing.",
                }
            )
        elif variable.get("name") != variable_name or variable.get("value") != str(
            expected
        ):
            blockers.append(
                {
                    "code": f"{identity['app_slug']}_variable_mismatch",
                    "message": (
                        f"{repo['name']}: Actions variable {variable_name} does not "
                        "match the reviewed lifecycle App identity."
                    ),
                }
            )
    return blockers


def _release_identity_variable_blockers(
    client: GitHubClient,
    owner: str,
    repo: Mapping[str, Any],
    identity: Mapping[str, Any],
    actor: ReleaseActor | None,
) -> list[dict[str, str]]:
    if repo["name"] not in identity["repository_scope"] or actor is None:
        return []
    variable_name = identity["repository_variables"]["app_id"]
    variable = client.get(
        (
            f"/repos/{owner}/{repo['name']}/actions/variables/"
            f"{quote(variable_name, safe='')}"
        ),
        optional=True,
    )
    if not isinstance(variable, Mapping):
        return [
            {
                "code": "openadapt-release_variable_missing",
                "message": (
                    f"{repo['name']}: Actions variable {variable_name} is missing."
                ),
            }
        ]
    if variable.get("name") != variable_name or variable.get("value") != str(
        actor.actor_id
    ):
        return [
            {
                "code": "openadapt-release_variable_mismatch",
                "message": (
                    f"{repo['name']}: Actions variable {variable_name} does not "
                    "match the reviewed release App identity."
                ),
            }
        ]
    return []


def _inventory_names(response: Any, field: str, description: str) -> set[str]:
    if not isinstance(response, Mapping):
        raise GitHubError(f"{description} inventory is unavailable")
    values = response.get(field)
    if not isinstance(values, list):
        raise GitHubError(f"{description} inventory is malformed")
    names = {
        item.get("name")
        for item in values
        if isinstance(item, Mapping) and isinstance(item.get("name"), str)
    }
    total_count = response.get("total_count", len(values))
    if not isinstance(total_count, int) or total_count != len(values):
        raise GitHubError(f"{description} inventory is incomplete")
    if len(names) != len(values):
        raise GitHubError(f"{description} inventory contains an invalid name")
    return names


def _identity_private_key_secret_blockers(
    client: GitHubClient,
    owner: str,
    repo: Mapping[str, Any],
    identity: Mapping[str, Any],
    repository_id: int | None,
) -> list[dict[str, str]]:
    repo_name = repo["name"]
    if repo_name not in identity["repository_scope"]:
        return []
    secret_name = identity["private_key_secret"]
    expected_environments = set(identity["private_key_environment_bindings"][repo_name])
    blockers: list[dict[str, str]] = []

    response = client.get(f"/repos/{owner}/{repo_name}/actions/secrets?per_page=100")
    repository_secret_names = _inventory_names(
        response, "secrets", f"{repo_name}: repository Actions secret"
    )
    if secret_name in repository_secret_names:
        blockers.append(
            {
                "code": f"{identity['app_slug']}_repository_private_key_present",
                "message": (
                    f"{repo_name}: remove repository Actions secret {secret_name}; "
                    "the private key must exist only in its exact protected environments."
                ),
            }
        )

    repository_variable = client.get(
        f"/repos/{owner}/{repo_name}/actions/variables/{quote(secret_name, safe='')}",
        optional=True,
    )
    if isinstance(repository_variable, Mapping):
        blockers.append(
            {
                "code": f"{identity['app_slug']}_repository_private_key_variable_present",
                "message": (
                    f"{repo_name}: remove repository Actions variable {secret_name}; "
                    "a private-key name must not be shadowed by a variable."
                ),
            }
        )

    environment_response = client.get(
        f"/repos/{owner}/{repo_name}/environments?per_page=100"
    )
    environment_names = _inventory_names(
        environment_response, "environments", f"{repo_name}: environment"
    )
    if repository_id is None or repository_id <= 0:
        raise GitHubError(f"{repo_name}: numeric repository id is unavailable")
    environments_with_key: set[str] = set()
    for environment_name in sorted(environment_names):
        encoded_environment = quote(environment_name, safe="")
        environment_secrets = client.get(
            f"/repos/{owner}/{repo_name}/environments/{encoded_environment}/secrets?per_page=100"
        )
        secret_names = _inventory_names(
            environment_secrets,
            "secrets",
            f"{repo_name}:{environment_name}: environment Actions secret",
        )
        if secret_name in secret_names:
            environments_with_key.add(environment_name)
        environment_variables = client.get(
            f"/repositories/{repository_id}/environments/{encoded_environment}/variables?per_page=100"
        )
        variable_names = _inventory_names(
            environment_variables,
            "variables",
            f"{repo_name}:{environment_name}: environment Actions variable",
        )
        if secret_name in variable_names:
            blockers.append(
                {
                    "code": f"{identity['app_slug']}_environment_private_key_variable_present",
                    "message": (
                        f"{repo_name}:{environment_name}: remove environment variable "
                        f"{secret_name}; it shadows the private-key secret name."
                    ),
                }
            )

    missing = sorted(expected_environments - environments_with_key)
    unexpected = sorted(environments_with_key - expected_environments)
    if missing:
        blockers.append(
            {
                "code": f"{identity['app_slug']}_environment_private_key_missing",
                "message": (
                    f"{repo_name}: environment secret {secret_name} is missing from "
                    f"the exact binding(s): {', '.join(missing)}."
                ),
            }
        )
    if unexpected:
        blockers.append(
            {
                "code": f"{identity['app_slug']}_environment_private_key_out_of_scope",
                "message": (
                    f"{repo_name}: environment secret {secret_name} exists outside "
                    f"its exact binding(s): {', '.join(unexpected)}."
                ),
            }
        )
    return blockers


def _exclusive_environment_blockers(
    client: GitHubClient,
    owner: str,
    repo: Mapping[str, Any],
    ref: str,
) -> list[dict[str, str]]:
    environments = repo.get("lifecycle_environments", []) + [
        item
        for item in repo.get("release_environments", [])
        if item.get("exclusive_workflow")
    ]
    if not environments:
        return []
    tree = client.get(
        f"/repos/{owner}/{repo['name']}/git/trees/{quote(ref, safe='')}?recursive=1"
    )
    if not isinstance(tree, Mapping) or tree.get("truncated"):
        raise GitHubError(
            f"{owner}/{repo['name']}: complete workflow tree is not available"
        )
    workflow_paths = sorted(
        item.get("path")
        for item in tree.get("tree", [])
        if item.get("type") == "blob"
        and isinstance(item.get("path"), str)
        and item["path"].startswith(".github/workflows/")
        and item["path"].endswith((".yml", ".yaml"))
    )
    content_by_path = {
        path: _workflow_text(client, owner, repo["name"], path, ref)
        for path in workflow_paths
    }
    blockers: list[dict[str, str]] = []
    for environment in environments:
        environment_name = environment["name"]
        allowed = environment["exclusive_workflow"]
        unexpected = [
            path
            for path, content in content_by_path.items()
            if path != allowed and content is not None and environment_name in content
        ]
        if unexpected:
            blockers.append(
                {
                    "code": "lifecycle_environment_workflow_scope",
                    "message": (
                        f"{repo['name']}:{environment_name} is referenced outside "
                        f"{allowed}: {', '.join(unexpected)}."
                    ),
                }
            )
    return blockers


def _conjunctive_clauses(expression: str) -> list[str]:
    normalized = expression.strip()
    if normalized.startswith("${{") and normalized.endswith("}}"):
        normalized = normalized[3:-2].strip()
    if re.search(r"\|\||\bor\b", normalized, flags=re.IGNORECASE):
        return []
    return [part.strip() for part in normalized.split("&&")]


def _has_exact_clause(clauses: Iterable[str], pattern: str) -> bool:
    return any(re.fullmatch(pattern, clause) is not None for clause in clauses)


def _actor_rejection_failures(expression: str) -> list[str]:
    failures: list[str] = []
    clauses = _conjunctive_clauses(expression)
    if not clauses:
        failures.append("non-conjunctive-condition")
    for actor_login in ("openadapt-lifecycle[bot]", "openadapt-docs[bot]"):
        escaped = re.escape(actor_login)
        for field in ("actor", "triggering_actor"):
            if not _has_exact_clause(
                clauses, rf"github\.{field}\s*!=\s*['\"]{escaped}['\"]"
            ):
                failures.append(f"{field}:{actor_login}")
    return failures


def _guard_actor_rejection_failures(guard: Mapping[str, Any]) -> list[str]:
    direct = _actor_rejection_failures(str(guard.get("if", "")))
    unresolved = set(direct)
    for step in _job_steps(guard):
        environment = step.get("env", {})
        run = step.get("run")
        if not isinstance(environment, Mapping) or not isinstance(run, str):
            continue
        if re.search(r"\|\||\bor\b|;\s*true\b", run, flags=re.IGNORECASE):
            unresolved.add("non-conjunctive-condition")
        run_lines = [line.strip() for line in run.splitlines() if line.strip()]
        test_commands: list[tuple[str, str]] = []
        invalid_command = False
        for line in run_lines:
            if line == "set -euo pipefail":
                continue
            match = re.fullmatch(
                r"test\s+['\"]?\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?['\"]?\s*"
                r"!=\s*['\"]([^'\"]+)['\"]",
                line,
            )
            if match is None:
                invalid_command = True
                break
            test_commands.append((match.group(1), match.group(2)))
        if invalid_command or not test_commands:
            continue
        for variable_name, value in environment.items():
            if not isinstance(variable_name, str) or not isinstance(value, str):
                continue
            field = next(
                (
                    candidate
                    for candidate in ("actor", "triggering_actor")
                    if f"github.{candidate}" in value
                ),
                None,
            )
            if field is None:
                continue
            for actor_login in ("openadapt-lifecycle[bot]", "openadapt-docs[bot]"):
                if (variable_name, actor_login) in test_commands:
                    unresolved.discard(f"{field}:{actor_login}")
    return sorted(unresolved)


def _job_actor_rejection_failures(document: Mapping[str, Any]) -> list[str]:
    jobs = document.get("jobs", {})
    if not isinstance(jobs, Mapping):
        return ["<invalid jobs object>"]
    guard_name = "reject-lifecycle-app"
    guard = jobs.get(guard_name)
    if not isinstance(guard, Mapping):
        return ["<missing reject-lifecycle-app predecessor>"]
    failures: list[str] = []
    if guard.get("permissions") != {}:
        failures.append(f"{guard_name}:permissions")
    guard_failures = _guard_actor_rejection_failures(guard)
    failures.extend(f"{guard_name}:{item}" for item in guard_failures)
    for job_name, job in jobs.items():
        if job_name == guard_name:
            continue
        if not isinstance(job_name, str) or not isinstance(job, Mapping):
            failures.append("<invalid job>")
            continue
        expression = str(job.get("if", ""))
        clauses = _conjunctive_clauses(expression)
        tag_only = _has_exact_clause(
            clauses, r"github\.event_name\s*==\s*['\"]push['\"]"
        ) and _has_exact_clause(
            clauses,
            r"startsWith\(\s*github\.ref\s*,\s*['\"]refs/tags/[^'\"]*['\"]\s*\)",
        )
        if tag_only:
            continue
        if guard_name not in _job_needs(job):
            failures.append(f"{job_name}:needs")
        failures.extend(
            f"{job_name}:{item}" for item in _actor_rejection_failures(expression)
        )
    return failures


def _authorized_dispatch_semantic_failures(
    document: Mapping[str, Any],
    owner: str,
    repo: Mapping[str, Any],
    path: str,
    identity: Mapping[str, Any],
) -> list[str]:
    jobs = document.get("jobs", {})
    if not isinstance(jobs, Mapping):
        return ["<invalid jobs object>"]
    expected_environments = [
        environment["name"]
        for environment in (
            repo.get("release_environments", [])
            + repo.get("lifecycle_environments", [])
        )
        if environment.get("exclusive_workflow") == path
        and environment["name"]
        in identity["private_key_environment_bindings"][repo["name"]]
    ]
    if len(expected_environments) != 1:
        return ["<workflow does not have one exact private-key environment>"]
    expected_environment = expected_environments[0]
    actor_login = identity["actor_login"]
    actor_id_variable = identity["repository_variables"]["actor_id"]
    installation_variable = identity["repository_variables"]["installation_id"]
    candidates: list[tuple[str, Mapping[str, Any]]] = []
    for job_name, job in jobs.items():
        if not isinstance(job_name, str) or not isinstance(job, Mapping):
            continue
        text = "\n".join(_all_strings(job))
        if (
            actor_login in text
            or identity["private_key_secret"] in text
            or re.search(r"\bgh\s+pr\s+create\b", text)
            or re.search(r"/dispatches\b", text)
        ):
            candidates.append((job_name, job))
    if not candidates:
        return ["<missing authorized effect job>"]

    failures: list[str] = []
    for job_name, job in candidates:
        expression = str(job.get("if", ""))
        clauses = _conjunctive_clauses(expression)
        if not clauses:
            failures.append(f"{job_name}:non-conjunctive-condition")
        required_conditions = {
            "repository": rf"github\.repository\s*==\s*['\"]{re.escape(owner)}/{re.escape(repo['name'])}['\"]",
            "ref": r"github\.ref\s*==\s*['\"]refs/heads/main['\"]",
            "event": r"github\.event_name\s*==\s*['\"](?:workflow_dispatch|repository_dispatch)['\"]",
            "actor": rf"github\.actor\s*==\s*['\"]{re.escape(actor_login)}['\"]",
            "triggering_actor": rf"github\.triggering_actor\s*==\s*['\"]{re.escape(actor_login)}['\"]",
            "actor_id": rf"github\.actor_id\s*==\s*vars\.{re.escape(actor_id_variable)}",
        }
        for label, pattern in required_conditions.items():
            if not _has_exact_clause(clauses, pattern):
                failures.append(f"{job_name}:{label}")
        if _job_environment(job) != expected_environment:
            failures.append(f"{job_name}:environment")
        token_step_ids = _matching_app_token_step_ids(
            job, identity, owner, repo["name"]
        )
        if not token_step_ids:
            failures.append(f"{job_name}:app-token")
            continue
        if installation_variable not in "\n".join(_all_strings(job)):
            failures.append(f"{job_name}:installation-id")
        token_references = _token_references(token_step_ids)
        for step in _job_steps(job):
            step_text = "\n".join(_all_strings(step))
            if re.search(r"\bgh\s+pr\s+create\b|/dispatches\b", step_text):
                step_environment = step.get("env", {})
                gh_token = (
                    step_environment.get("GH_TOKEN")
                    if isinstance(step_environment, Mapping)
                    else None
                )
                if not any(
                    _is_exact_expression(gh_token, reference)
                    for reference in token_references
                ):
                    failures.append(f"{job_name}:effect-token")
            if re.search(r"\bgit\s+push\b", step_text) and _step_uses_token(
                step, token_references
            ):
                failures.append(f"{job_name}:branch-push-app-token")
    return failures


def _dispatch_workflow_blockers(
    client: GitHubClient,
    owner: str,
    repo: Mapping[str, Any],
    lifecycle_identity: Mapping[str, Any],
    docs_identity: Mapping[str, Any],
    ref: str,
) -> list[dict[str, str]]:
    inventory = {
        item["path"]: item["mode"]
        for item in repo.get("dispatch_workflow_inventory", [])
    }
    if not inventory:
        return []
    tree = client.get(
        f"/repos/{owner}/{repo['name']}/git/trees/{quote(ref, safe='')}?recursive=1"
    )
    if not isinstance(tree, Mapping) or tree.get("truncated"):
        raise GitHubError(
            f"{owner}/{repo['name']}: complete dispatch workflow tree is not available"
        )
    workflow_paths = sorted(
        item.get("path")
        for item in tree.get("tree", [])
        if item.get("type") == "blob"
        and isinstance(item.get("path"), str)
        and item["path"].startswith(".github/workflows/")
        and item["path"].endswith((".yml", ".yaml"))
    )
    blockers: list[dict[str, str]] = []
    for path in workflow_paths:
        content = _workflow_text(client, owner, repo["name"], path, ref)
        if content is None:
            continue
        try:
            document = _parse_workflow_document(content, owner, repo["name"], path)
            triggers = _workflow_triggers(document)
        except PolicyError as exc:
            blockers.append(
                {"code": "dispatch_workflow_yaml_invalid", "message": str(exc)}
            )
            continue
        if not triggers.intersection({"workflow_dispatch", "repository_dispatch"}):
            continue
        concurrency = document.get("concurrency")
        group = concurrency.get("group") if isinstance(concurrency, Mapping) else None
        non_cancelling = (
            concurrency.get("cancel-in-progress")
            if isinstance(concurrency, Mapping)
            else None
        )
        if (
            not isinstance(group, str)
            or "github.workflow" not in group
            or "github.event_name" not in group
            or non_cancelling is not False
        ):
            blockers.append(
                {
                    "code": "dispatch_workflow_concurrency_not_isolated",
                    "message": (
                        f"{repo['name']}:{path} needs a workflow-and-event-specific "
                        "non-cancelling concurrency group."
                    ),
                }
            )
        mode = inventory.get(path)
        if mode is None:
            blockers.append(
                {
                    "code": "dispatch_workflow_not_inventoried",
                    "message": f"{repo['name']}: dispatchable workflow {path} is not inventoried.",
                }
            )
            continue
        if mode == "reject-lifecycle-app":
            failures = _job_actor_rejection_failures(document)
            if failures:
                blockers.append(
                    {
                        "code": "dispatch_workflow_accepts_privileged_app",
                        "message": (
                            f"{repo['name']}:{path} does not reject both privileged App actors "
                            f"in every job: {', '.join(failures)}."
                        ),
                    }
                )
        elif mode in {"lifecycle-only", "docs-only"}:
            identity = lifecycle_identity if mode == "lifecycle-only" else docs_identity
            failures = _authorized_dispatch_semantic_failures(
                document, owner, repo, path, identity
            )
            if failures:
                blockers.append(
                    {
                        "code": f"{mode}_workflow_semantic_contract",
                        "message": (
                            f"{repo['name']}:{path} does not bind its actor, environment, "
                            f"App token, and effects in the authorized job: {', '.join(failures)}."
                        ),
                    }
                )
    return blockers


def _list_rulesets(
    client: GitHubClient, owner: str, repo: str
) -> dict[str, Mapping[str, Any]]:
    response = client.get(
        f"/repos/{owner}/{repo}/rulesets?includes_parents=false&per_page=100"
    )
    if not isinstance(response, list):
        raise GitHubError(f"{owner}/{repo}: ruleset list is not an array")
    result: dict[str, Mapping[str, Any]] = {}
    for summary in response:
        if summary.get("name") not in MANAGED_RULESET_NAMES:
            continue
        detail = client.get(f"/repos/{owner}/{repo}/rulesets/{summary['id']}")
        result[summary["name"]] = detail
    return result


def _open_pull_requests(
    client: GitHubClient, owner: str, repo: str, branch: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    response = client.get(
        f"/repos/{owner}/{repo}/pulls?state=open&base={quote(branch, safe='')}&per_page=100"
    )
    if not isinstance(response, list):
        raise GitHubError(f"{owner}/{repo}: pull request list is not an array")
    pulls: list[dict[str, Any]] = []
    active: list[dict[str, Any]] = []
    for pull in response:
        head = pull.get("head", {}).get("sha")
        pulls.append(
            {
                "number": pull.get("number"),
                "draft": pull.get("draft", False),
                "head_sha": head,
            }
        )
        if not head:
            continue
        checks = client.get(
            f"/repos/{owner}/{repo}/commits/{head}/check-runs?per_page=100"
        )
        for check in checks.get("check_runs", []):
            if check.get("status") in ACTIVE_CHECK_STATES:
                active.append(
                    {
                        "pull_request": pull.get("number"),
                        "name": check.get("name"),
                        "status": check.get("status"),
                    }
                )
    return pulls, active


def _environment_actions(
    client: GitHubClient,
    config: Mapping[str, Any],
    owner: str,
    repo: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], bool]:
    actions: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []
    prune_needed = False
    environments = repo["release_environments"] + repo.get("lifecycle_environments", [])
    for environment in environments:
        name = environment["name"]
        encoded = quote(name, safe="")
        current = client.get(
            f"/repos/{owner}/{repo['name']}/environments/{encoded}", optional=True
        )
        desired = desired_environment(config, environment)
        if (
            not isinstance(current, Mapping)
            or current.get("can_admins_bypass") is not False
        ):
            blockers.append(
                {
                    "code": "environment_admin_bypass_not_disabled",
                    "message": (
                        f"{repo['name']}:{name}: open Settings > Environments > {name} "
                        "in GitHub, create the environment if needed, and clear "
                        "'Allow administrators to bypass configured protection rules'. "
                        "The REST API cannot set this control."
                    ),
                }
            )
            continue
        if _normalize_environment(current) != desired:
            actions.append(
                {
                    "kind": "put_environment",
                    "environment": name,
                    "payload": desired,
                }
            )
        current_policies: list[Mapping[str, Any]] = []
        current_deployment_policy = (
            current.get("deployment_branch_policy")
            if isinstance(current, Mapping)
            else None
        )
        if isinstance(
            current_deployment_policy, Mapping
        ) and current_deployment_policy.get("custom_branch_policies"):
            response = client.get(
                f"/repos/{owner}/{repo['name']}/environments/{encoded}/deployment-branch-policies?per_page=100"
            )
            current_policies = response.get("branch_policies", [])
        if any(item.get("type") not in {"branch", "tag"} for item in current_policies):
            raise GitHubError(
                f"{owner}/{repo['name']}:{name}: GitHub omitted a deployment policy type"
            )
        current_by_key = {
            (item["type"], item.get("name")): item for item in current_policies
        }
        desired_keys = {
            (item["type"], item["name"]) for item in environment["deployment_policies"]
        }
        for policy in environment["deployment_policies"]:
            if (policy["type"], policy["name"]) not in current_by_key:
                actions.append(
                    {
                        "kind": "create_environment_policy",
                        "environment": name,
                        "payload": policy,
                    }
                )
        for key, policy in current_by_key.items():
            if key not in desired_keys:
                prune_needed = True
                actions.append(
                    {
                        "kind": "delete_environment_policy",
                        "environment": name,
                        "policy_id": policy.get("id"),
                        "current": {"type": key[0], "name": key[1]},
                    }
                )
    return actions, blockers, prune_needed


def build_plan(client: GitHubClient, config: Mapping[str, Any]) -> dict[str, Any]:
    owner = config["organization"]
    global_blockers: list[dict[str, str]] = []
    actor = _resolve_release_actor(client, config, global_blockers)
    lifecycle_actor = _resolve_lifecycle_actor(client, config, global_blockers)
    docs_actor = _resolve_docs_actor(client, config, global_blockers)
    _verify_reviewer(client, config, global_blockers)
    repositories: list[dict[str, Any]] = []

    for repo in config["repositories"]:
        name = repo["name"]
        blockers: list[dict[str, str]] = []
        warnings = [
            {"code": "admission_gap", "message": message}
            for message in repo.get("admission_gaps", [])
        ]
        metadata = client.get(f"/repos/{owner}/{name}")
        expected_full_name = f"{owner}/{name}"
        if metadata.get("full_name") != expected_full_name:
            blockers.append(
                {
                    "code": "repository_identity_mismatch",
                    "message": f"Expected {expected_full_name}, got {metadata.get('full_name')!r}.",
                }
            )
        actual_visibility = "private" if metadata.get("private") else "public"
        if actual_visibility != repo["visibility"]:
            blockers.append(
                {
                    "code": "repository_visibility_mismatch",
                    "message": f"{name}: expected {repo['visibility']}, got {actual_visibility}.",
                }
            )
        if metadata.get("default_branch") != repo["default_branch"]:
            blockers.append(
                {
                    "code": "default_branch_mismatch",
                    "message": f"{name}: default branch is not {repo['default_branch']}.",
                }
            )
        commit = client.get(f"/repos/{owner}/{name}/commits/{repo['default_branch']}")
        main_sha = commit.get("sha")
        if (
            not isinstance(main_sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", main_sha) is None
        ):
            raise GitHubError(f"{name}: default branch did not resolve to a commit SHA")
        if main_sha != repo["audited_main_sha"]:
            blockers.append(
                {
                    "code": "audited_main_drift",
                    "message": (
                        f"{name}: main advanced from {repo['audited_main_sha']} to {main_sha}. "
                        "Re-audit the exact current main workflow state and update the policy SHA."
                    ),
                }
            )

        pulls, active_checks = _open_pull_requests(
            client, owner, name, repo["default_branch"]
        )
        if pulls:
            warnings.append(
                {
                    "code": "open_pull_requests",
                    "message": f"{name}: {len(pulls)} open pull request(s) target main.",
                }
            )
        if active_checks:
            blockers.append(
                {
                    "code": "active_pull_request_checks",
                    "message": f"{name}: pull-request checks are still active.",
                }
            )

        blockers.extend(
            _workflow_contract_blockers(
                client, owner, repo, "release_workflows", "release", main_sha
            )
        )
        blockers.extend(
            _workflow_contract_blockers(
                client, owner, repo, "admission_workflows", "admission", main_sha
            )
        )
        blockers.extend(
            _workflow_contract_blockers(
                client, owner, repo, "lifecycle_workflows", "lifecycle", main_sha
            )
        )
        blockers.extend(
            _release_workflow_semantic_blockers(
                client, owner, repo, config["release_identity"], main_sha
            )
        )
        blockers.extend(
            _release_identity_variable_blockers(
                client,
                owner,
                repo,
                config["release_identity"],
                actor,
            )
        )
        blockers.extend(
            _dispatch_identity_variable_blockers(
                client,
                owner,
                repo,
                config["lifecycle_identity"],
                lifecycle_actor,
            )
        )
        blockers.extend(
            _dispatch_identity_variable_blockers(
                client,
                owner,
                repo,
                config["docs_identity"],
                docs_actor,
            )
        )
        for identity in (
            config["release_identity"],
            config["lifecycle_identity"],
            config["docs_identity"],
        ):
            blockers.extend(
                _identity_private_key_secret_blockers(
                    client,
                    owner,
                    repo,
                    identity,
                    metadata.get("id"),
                )
            )
        blockers.extend(_exclusive_environment_blockers(client, owner, repo, main_sha))
        blockers.extend(
            _dispatch_workflow_blockers(
                client,
                owner,
                repo,
                config["lifecycle_identity"],
                config["docs_identity"],
                main_sha,
            )
        )
        current_rulesets = _list_rulesets(client, owner, name)
        actions: list[dict[str, Any]] = []
        for desired in desired_rulesets(config, repo, actor):
            current = current_rulesets.get(desired["name"])
            if current is None:
                actions.append(
                    {
                        "kind": "create_ruleset",
                        "name": desired["name"],
                        "payload": desired,
                    }
                )
            elif _normalize_ruleset(current) != _normalize_ruleset(desired):
                actions.append(
                    {
                        "kind": "update_ruleset",
                        "name": desired["name"],
                        "ruleset_id": current.get("id"),
                        "payload": desired,
                    }
                )

        environment_actions, environment_blockers, prune_needed = _environment_actions(
            client, config, owner, repo
        )
        blockers.extend(environment_blockers)
        actions.extend(environment_actions)
        final_commit = client.get(
            f"/repos/{owner}/{name}/commits/{repo['default_branch']}"
        )
        final_main_sha = final_commit.get("sha")
        if final_main_sha != main_sha:
            blockers.append(
                {
                    "code": "audited_main_changed_during_plan",
                    "message": (
                        f"{name}: {repo['default_branch']} changed from {main_sha} "
                        f"to {final_main_sha} during the audit. Create a new plan."
                    ),
                }
            )
        repositories.append(
            {
                "name": name,
                "default_branch": repo["default_branch"],
                "main_sha": main_sha,
                "audited_main_sha": repo["audited_main_sha"],
                "open_pull_requests": pulls,
                "active_checks": active_checks,
                "path_scoped_checks": repo["path_scoped_checks"],
                "warnings": warnings,
                "blockers": blockers,
                "requires_environment_policy_prune": prune_needed,
                "actions": actions,
            }
        )

    blocker_count = len(global_blockers) + sum(
        len(repo["blockers"]) for repo in repositories
    )
    return {
        "schema_version": 1,
        "generated_at": _utc_now().isoformat(),
        "max_age_seconds": PLAN_MAX_AGE_SECONDS,
        "organization": owner,
        "config_sha256": _json_digest(config),
        "release_actor_id": actor.actor_id if actor else None,
        "lifecycle_app_id": lifecycle_actor.app_id if lifecycle_actor else None,
        "lifecycle_actor_id": lifecycle_actor.actor_id if lifecycle_actor else None,
        "lifecycle_installation_id": (
            lifecycle_actor.installation_id if lifecycle_actor else None
        ),
        "docs_app_id": docs_actor.app_id if docs_actor else None,
        "docs_actor_id": docs_actor.actor_id if docs_actor else None,
        "docs_installation_id": docs_actor.installation_id if docs_actor else None,
        "global_blockers": global_blockers,
        "repositories": repositories,
        "plan_constraints": config["plan_constraints"],
        "blocker_count": blocker_count,
        "safe_to_apply": blocker_count == 0,
    }


def _plan_snapshot(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "config_sha256": plan.get("config_sha256"),
        "release_actor_id": plan.get("release_actor_id"),
        "lifecycle_app_id": plan.get("lifecycle_app_id"),
        "lifecycle_actor_id": plan.get("lifecycle_actor_id"),
        "lifecycle_installation_id": plan.get("lifecycle_installation_id"),
        "docs_app_id": plan.get("docs_app_id"),
        "docs_actor_id": plan.get("docs_actor_id"),
        "docs_installation_id": plan.get("docs_installation_id"),
        "repositories": [
            {
                "name": repo.get("name"),
                "main_sha": repo.get("main_sha"),
                "actions": repo.get("actions"),
            }
            for repo in plan.get("repositories", [])
        ],
    }


def _parse_plan_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise PolicyError("plan has no generated_at time")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PolicyError("plan generated_at time is invalid") from exc
    if result.tzinfo is None:
        raise PolicyError("plan generated_at time has no timezone")
    return result.astimezone(timezone.utc)


def validate_plan_for_apply(
    saved: Mapping[str, Any], current: Mapping[str, Any], config: Mapping[str, Any]
) -> None:
    if saved.get("organization") != config["organization"]:
        raise PolicyError("plan organization does not match the config")
    age = (_utc_now() - _parse_plan_time(saved.get("generated_at"))).total_seconds()
    if age < 0 or age > PLAN_MAX_AGE_SECONDS:
        raise PolicyError("plan is stale; create a new plan")
    if saved.get("blocker_count") != 0 or not saved.get("safe_to_apply"):
        raise PolicyError("saved plan has blockers")
    if current.get("blocker_count") != 0 or not current.get("safe_to_apply"):
        raise PolicyError("live preflight has blockers")
    if _plan_snapshot(saved) != _plan_snapshot(current):
        raise PolicyError("live state changed after the saved plan")


def _apply_actions(
    client: GitHubClient,
    plan: Mapping[str, Any],
    *,
    prune_environment_policies: bool,
) -> None:
    owner = plan["organization"]
    if not prune_environment_policies and any(
        repo.get("requires_environment_policy_prune") for repo in plan["repositories"]
    ):
        raise PolicyError(
            "the plan removes environment policies; inspect it and add "
            "--prune-environment-policies"
        )
    for repo in plan["repositories"]:
        name = repo["name"]
        branch = repo.get("default_branch", "main")
        current = client.get(f"/repos/{owner}/{name}/commits/{branch}")
        if current.get("sha") != repo.get("main_sha"):
            raise PolicyError(
                f"{name}: {branch} changed after preflight; no protection mutation was sent"
            )
    for repo in plan["repositories"]:
        name = repo["name"]
        for action in repo["actions"]:
            kind = action["kind"]
            if kind == "create_ruleset":
                client.write(
                    "POST", f"/repos/{owner}/{name}/rulesets", action["payload"]
                )
            elif kind == "update_ruleset":
                client.write(
                    "PUT",
                    f"/repos/{owner}/{name}/rulesets/{action['ruleset_id']}",
                    action["payload"],
                )
            elif kind == "put_environment":
                environment = quote(action["environment"], safe="")
                client.write(
                    "PUT",
                    f"/repos/{owner}/{name}/environments/{environment}",
                    action["payload"],
                )
            elif kind == "create_environment_policy":
                environment = quote(action["environment"], safe="")
                client.write(
                    "POST",
                    f"/repos/{owner}/{name}/environments/{environment}/deployment-branch-policies",
                    action["payload"],
                )
            elif kind == "delete_environment_policy":
                if not prune_environment_policies:
                    raise PolicyError("environment policy prune was not confirmed")
                environment = quote(action["environment"], safe="")
                client.write(
                    "DELETE",
                    (
                        f"/repos/{owner}/{name}/environments/{environment}/"
                        f"deployment-branch-policies/{action['policy_id']}"
                    ),
                )
            else:
                raise PolicyError(f"unknown plan action: {kind}")


def _write_json(value: Any, output: Path | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")
        print(f"Wrote {output}")


def _default_config() -> Path:
    return (
        Path(__file__).resolve().parents[1] / "ops/github/core-protection-policy.json"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=_default_config())
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate-config", help="Validate the local JSON policy only")

    plan = commands.add_parser("plan", help="Read GitHub and write a non-mutating plan")
    plan.add_argument("--output", type=Path)

    verify = commands.add_parser(
        "verify", help="Verify live GitHub state against the policy"
    )
    verify.add_argument("--output", type=Path)

    apply = commands.add_parser("apply", help="Apply one fresh, reviewed plan")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--confirm", required=True)
    apply.add_argument("--prune-environment-policies", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "validate-config":
            print(
                f"Valid policy for {len(config['repositories'])} managed repositories; "
                "openadapt-cloud is audit-only."
            )
            return 0

        GhApiClient.require_auth()
        read_client = GhApiClient(allow_writes=False)
        plan = build_plan(read_client, config)
        if args.command == "plan":
            _write_json(plan, args.output)
            return 0 if plan["safe_to_apply"] else 2
        if args.command == "verify":
            _write_json(plan, args.output)
            has_actions = any(repo["actions"] for repo in plan["repositories"])
            return 0 if plan["safe_to_apply"] and not has_actions else 2

        if args.confirm != "APPLY OpenAdaptAI CORE PROTECTION":
            raise PolicyError("apply confirmation value is invalid")
        try:
            saved = json.loads(args.plan.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyError(f"cannot read apply plan: {exc}") from exc
        validate_plan_for_apply(saved, plan, config)
        write_client = GhApiClient(allow_writes=True)
        _apply_actions(
            write_client,
            plan,
            prune_environment_policies=args.prune_environment_policies,
        )
        verified = build_plan(read_client, config)
        if verified["blocker_count"] or any(
            repo["actions"] for repo in verified["repositories"]
        ):
            raise PolicyError("post-apply verification did not converge")
        print("Applied and verified the OpenAdapt core GitHub protection policy.")
        return 0
    except (GitHubError, PolicyError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
