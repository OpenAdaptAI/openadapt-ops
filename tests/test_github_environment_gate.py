from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_github_environment_gate import EnvironmentGateError, validate


def environment(name: str = "production-backup") -> dict[str, object]:
    return {
        "name": name,
        "deployment_branch_policy": {
            "protected_branches": False,
            "custom_branch_policies": True,
        },
    }


def policies(name: str = "main") -> dict[str, object]:
    return {
        "total_count": 1,
        "branch_policies": [{"id": 1, "name": name}],
    }


def check(
    env: dict[str, object] | None = None,
    rules: dict[str, object] | None = None,
    *,
    actual_ref: str = "refs/heads/main",
    ref_protected: str = "true",
) -> dict[str, object]:
    return validate(
        environment=env or environment(),
        policies=rules or policies(),
        expected_environment="production-backup",
        expected_branch="main",
        actual_ref=actual_ref,
        ref_protected=ref_protected,
    )


def test_exact_protected_main_environment_passes() -> None:
    assert check()["valid"] is True


@pytest.mark.parametrize(
    ("env", "rules", "actual_ref", "ref_protected", "message"),
    [
        (environment("other"), policies(), "refs/heads/main", "true", "identity"),
        (environment(), policies(), "refs/heads/feature", "true", "workflow ref"),
        (environment(), policies(), "refs/heads/main", "false", "not protected"),
        (
            {"name": "production-backup", "deployment_branch_policy": None},
            policies(),
            "refs/heads/main",
            "true",
            "no branch policy",
        ),
        (
            {
                "name": "production-backup",
                "deployment_branch_policy": {
                    "protected_branches": True,
                    "custom_branch_policies": False,
                },
            },
            policies(),
            "refs/heads/main",
            "true",
            "every protected branch",
        ),
        (environment(), policies("release/*"), "refs/heads/main", "true", "exact main"),
        (
            environment(),
            {
                "total_count": 2,
                "branch_policies": [
                    {"id": 1, "name": "main"},
                    {"id": 2, "name": "release/*"},
                ],
            },
            "refs/heads/main",
            "true",
            "exactly one",
        ),
    ],
)
def test_incomplete_or_broad_gate_is_rejected(
    env: dict[str, object],
    rules: dict[str, object],
    actual_ref: str,
    ref_protected: str,
    message: str,
) -> None:
    with pytest.raises(EnvironmentGateError, match=message):
        check(env, rules, actual_ref=actual_ref, ref_protected=ref_protected)
