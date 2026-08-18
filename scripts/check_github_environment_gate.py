#!/usr/bin/env python3
"""Require one protected main branch and one exact environment branch policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class EnvironmentGateError(ValueError):
    """The GitHub environment does not have the required external gate."""


def validate(
    *,
    environment: dict[str, object],
    policies: dict[str, object],
    expected_environment: str,
    expected_branch: str,
    actual_ref: str,
    ref_protected: str,
) -> dict[str, object]:
    expected_ref = f"refs/heads/{expected_branch}"
    if actual_ref != expected_ref:
        raise EnvironmentGateError(
            f"the workflow ref is {actual_ref!r}, not {expected_ref!r}"
        )
    if ref_protected.lower() != "true":
        raise EnvironmentGateError("the exact main ref is not protected")
    if environment.get("name") != expected_environment:
        raise EnvironmentGateError("the GitHub environment identity is invalid")

    deployment = environment.get("deployment_branch_policy")
    if not isinstance(deployment, dict):
        raise EnvironmentGateError("the GitHub environment has no branch policy")
    if deployment.get("protected_branches") is not False:
        raise EnvironmentGateError(
            "the GitHub environment must not admit every protected branch"
        )
    if deployment.get("custom_branch_policies") is not True:
        raise EnvironmentGateError(
            "the GitHub environment needs an exact custom branch policy"
        )

    branch_policies = policies.get("branch_policies")
    total = policies.get("total_count")
    if (
        not isinstance(branch_policies, list)
        or isinstance(total, bool)
        or not isinstance(total, int)
        or total != len(branch_policies)
        or total != 1
    ):
        raise EnvironmentGateError(
            "the GitHub environment must have exactly one deployment branch policy"
        )
    policy = branch_policies[0]
    if not isinstance(policy, dict):
        raise EnvironmentGateError("the deployment branch policy is invalid")
    # GitHub's list-deployment-branch-policies response does not consistently
    # include the policy type. The environment has already admitted this run on
    # the exact protected branch, so require the one returned policy to have the
    # exact branch name without depending on an absent response field.
    if policy.get("name") != expected_branch:
        raise EnvironmentGateError(
            "the only environment deployment policy must be the exact main branch"
        )

    return {
        "valid": True,
        "environment": expected_environment,
        "ref": expected_ref,
        "ref_protected": True,
        "branch_policy": expected_branch,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-json", required=True)
    parser.add_argument("--policies-json", required=True)
    parser.add_argument("--expected-environment", required=True)
    parser.add_argument("--expected-branch", default="main")
    parser.add_argument("--actual-ref", required=True)
    parser.add_argument("--ref-protected", required=True)
    args = parser.parse_args()
    try:
        result = validate(
            environment=json.loads(
                Path(args.environment_json).read_text(encoding="utf-8")
            ),
            policies=json.loads(Path(args.policies_json).read_text(encoding="utf-8")),
            expected_environment=args.expected_environment,
            expected_branch=args.expected_branch,
            actual_ref=args.actual_ref,
            ref_protected=args.ref_protected,
        )
    except (EnvironmentGateError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
