#!/usr/bin/env python3
"""Verify the exact live S3 database-backup target contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class TargetError(ValueError):
    """The live S3 target does not match the reviewed backup contract."""


def read_object(path: str, name: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TargetError(f"the {name} response is not an object")
    return value


def require_exact_public_block(value: dict[str, object]) -> None:
    expected = {
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True,
    }
    if value.get("PublicAccessBlockConfiguration") != expected:
        raise TargetError("the backup bucket public-access block is incomplete")


def require_exact_encryption(value: dict[str, object]) -> None:
    configuration = value.get("ServerSideEncryptionConfiguration")
    rules = configuration.get("Rules") if isinstance(configuration, dict) else None
    if not isinstance(rules, list) or len(rules) != 1:
        raise TargetError("the backup bucket encryption rule is not exact")
    rule = rules[0]
    if not isinstance(rule, dict):
        raise TargetError("the backup bucket encryption rule is invalid")
    default = rule.get("ApplyServerSideEncryptionByDefault")
    if not isinstance(default, dict) or default.get("SSEAlgorithm") != "AES256":
        raise TargetError("the backup bucket does not default to SSE-S3")
    if default.get("KMSMasterKeyID") is not None:
        raise TargetError("the backup bucket has an unexpected KMS key")


def require_exact_versioning(value: dict[str, object]) -> None:
    if value.get("Status") != "Enabled":
        raise TargetError("the backup bucket versioning is not enabled")
    if value.get("MFADelete") not in {None, "Disabled"}:
        raise TargetError("the backup bucket has an unexpected MFA-delete state")


def require_exact_ownership(value: dict[str, object]) -> None:
    if value.get("OwnershipControls") != {
        "Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]
    }:
        raise TargetError("the backup bucket ownership control is not exact")


def require_us_east_1(value: dict[str, object]) -> None:
    # S3 reports a null location constraint for us-east-1.
    if value.get("LocationConstraint") is not None:
        raise TargetError("the backup bucket is not in us-east-1")


def rule_prefix(rule: dict[str, object]) -> object:
    if "Prefix" in rule:
        return rule.get("Prefix")
    filter_value = rule.get("Filter")
    if isinstance(filter_value, dict):
        return filter_value.get("Prefix")
    return None


def require_exact_lifecycle(value: dict[str, object]) -> None:
    rules = value.get("Rules")
    if not isinstance(rules, list) or len(rules) != 3:
        raise TargetError("the backup bucket lifecycle rule set is not exact")
    by_id = {
        rule.get("ID"): rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("ID"), str)
    }
    expected = {
        "DeleteExpiredBackups": ("daily/", 90),
        "DeleteExpiredDrillEvidence": ("drills/", 365),
        "DeleteExpiredActivationState": ("activation/", 365),
    }
    if set(by_id) != set(expected):
        raise TargetError("the backup bucket lifecycle rule identities are not exact")
    for rule_id, (prefix, days) in expected.items():
        rule = by_id[rule_id]
        if (
            rule.get("Status") != "Enabled"
            or rule_prefix(rule) != prefix
            or rule.get("Expiration") != {"Days": days}
            or rule.get("NoncurrentVersionExpiration") != {"NoncurrentDays": 7}
        ):
            raise TargetError(f"the backup bucket lifecycle rule is invalid: {rule_id}")
        abort = rule.get("AbortIncompleteMultipartUpload")
        if rule_id == "DeleteExpiredBackups":
            if abort != {"DaysAfterInitiation": 1}:
                raise TargetError("the daily backup multipart cleanup is invalid")
        elif abort is not None:
            raise TargetError(f"the lifecycle has an unexpected cleanup: {rule_id}")


def actions(statement: dict[str, object]) -> set[str]:
    value = statement.get("Action")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    return set()


def resources(statement: dict[str, object]) -> set[str]:
    value = statement.get("Resource")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    return set()


def policy_document(value: dict[str, object]) -> dict[str, object]:
    document = value.get("Policy")
    if isinstance(document, str):
        document = json.loads(document)
    if not isinstance(document, dict):
        raise TargetError("the backup bucket policy is invalid")
    return document


def require_exact_policy(value: dict[str, object], bucket: str) -> None:
    statements = policy_document(value).get("Statement")
    if not isinstance(statements, list) or len(statements) != 7:
        raise TargetError("the backup bucket policy statement set is not exact")
    by_sid = {
        statement.get("Sid"): statement
        for statement in statements
        if isinstance(statement, dict) and isinstance(statement.get("Sid"), str)
    }
    expected_ids = {
        "DenyInsecureTransport",
        "RequireSseS3",
        "RequireSseS3ForDrillEvidence",
        "RequireSseS3ForActivationState",
        "RequireGlacierInstantRetrievalCiphertext",
        "RequireStandardManifest",
        "RequireStandardActivationState",
    }
    if set(by_sid) != expected_ids:
        raise TargetError("the backup bucket policy identities are not exact")

    bucket_arn = f"arn:aws:s3:::{bucket}"
    tls = by_sid["DenyInsecureTransport"]
    if (
        tls.get("Effect") != "Deny"
        or tls.get("Principal") != "*"
        or actions(tls) != {"s3:*"}
        or resources(tls) != {bucket_arn, f"{bucket_arn}/*"}
        or tls.get("Condition") != {"Bool": {"aws:SecureTransport": "false"}}
    ):
        raise TargetError("the backup bucket TLS-only policy is invalid")

    for sid, prefix in (
        ("RequireSseS3", "daily"),
        ("RequireSseS3ForDrillEvidence", "drills"),
        ("RequireSseS3ForActivationState", "activation"),
    ):
        statement = by_sid[sid]
        if (
            statement.get("Effect") != "Deny"
            or statement.get("Principal") != "*"
            or actions(statement) != {"s3:PutObject"}
            or resources(statement) != {f"{bucket_arn}/{prefix}/*"}
            or statement.get("Condition")
            != {"StringNotEquals": {"s3:x-amz-server-side-encryption": "AES256"}}
        ):
            raise TargetError(f"the backup bucket encryption policy is invalid: {sid}")

    storage_classes = (
        (
            "RequireGlacierInstantRetrievalCiphertext",
            "daily/*/*.age",
            "GLACIER_IR",
        ),
        ("RequireStandardManifest", "daily/*/artifact-manifest.json", "STANDARD"),
        ("RequireStandardActivationState", "activation/*", "STANDARD"),
    )
    for sid, key_pattern, storage_class in storage_classes:
        statement = by_sid[sid]
        if (
            statement.get("Effect") != "Deny"
            or statement.get("Principal") != "*"
            or actions(statement) != {"s3:PutObject"}
            or resources(statement) != {f"{bucket_arn}/{key_pattern}"}
            or statement.get("Condition")
            != {"StringNotEquals": {"s3:x-amz-storage-class": storage_class}}
        ):
            raise TargetError(f"the backup bucket storage policy is invalid: {sid}")


def validate(args: argparse.Namespace) -> dict[str, object]:
    require_exact_public_block(read_object(args.public_access_block, "public-access"))
    require_exact_encryption(read_object(args.encryption, "encryption"))
    require_exact_versioning(read_object(args.versioning, "versioning"))
    require_exact_ownership(read_object(args.ownership, "ownership"))
    require_us_east_1(read_object(args.location, "location"))
    require_exact_lifecycle(read_object(args.lifecycle, "lifecycle"))
    require_exact_policy(read_object(args.policy, "policy"), args.bucket)
    return {"valid": True, "bucket": args.bucket, "region": "us-east-1"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--bucket", required=True)
    result.add_argument("--public-access-block", required=True)
    result.add_argument("--encryption", required=True)
    result.add_argument("--versioning", required=True)
    result.add_argument("--ownership", required=True)
    result.add_argument("--location", required=True)
    result.add_argument("--lifecycle", required=True)
    result.add_argument("--policy", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        print(json.dumps(validate(args), sort_keys=True))
    except (TargetError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
