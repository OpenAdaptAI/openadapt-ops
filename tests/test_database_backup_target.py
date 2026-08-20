from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "check_database_backup_target.py"
SPEC = importlib.util.spec_from_file_location("check_database_backup_target", MODULE_PATH)
assert SPEC and SPEC.loader
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)

BUCKET = "openadapt-production-db-backups-992382684924"


def documents(tmp_path: Path) -> Namespace:
    bucket_arn = f"arn:aws:s3:::{BUCKET}"
    values = {
        "public_access_block": {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        },
        "encryption": {
            "ServerSideEncryptionConfiguration": {
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        },
        "versioning": {"Status": "Enabled"},
        "ownership": {
            "OwnershipControls": {
                "Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]
            }
        },
        "location": {"LocationConstraint": None},
        "lifecycle": {
            "Rules": [
                {
                    "ID": "DeleteExpiredBackups",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "daily/"},
                    "Expiration": {"Days": 90},
                    "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                },
                {
                    "ID": "DeleteExpiredDrillEvidence",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "drills/"},
                    "Expiration": {"Days": 365},
                    "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
                },
            ]
        },
        "policy": {
            "Policy": json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "DenyInsecureTransport",
                            "Effect": "Deny",
                            "Principal": "*",
                            "Action": "s3:*",
                            "Resource": [bucket_arn, f"{bucket_arn}/*"],
                            "Condition": {
                                "Bool": {"aws:SecureTransport": "false"}
                            },
                        },
                        {
                            "Sid": "RequireSseS3",
                            "Effect": "Deny",
                            "Principal": "*",
                            "Action": "s3:PutObject",
                            "Resource": f"{bucket_arn}/daily/*",
                            "Condition": {
                                "StringNotEquals": {
                                    "s3:x-amz-server-side-encryption": "AES256"
                                }
                            },
                        },
                        {
                            "Sid": "RequireSseS3ForDrillEvidence",
                            "Effect": "Deny",
                            "Principal": "*",
                            "Action": "s3:PutObject",
                            "Resource": f"{bucket_arn}/drills/*",
                            "Condition": {
                                "StringNotEquals": {
                                    "s3:x-amz-server-side-encryption": "AES256"
                                }
                            },
                        },
                    ],
                }
            )
        },
    }
    paths: dict[str, str] = {}
    for name, value in values.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        paths[name] = str(path)
    return Namespace(bucket=BUCKET, **paths)


def change(args: Namespace, name: str, update) -> None:
    path = Path(getattr(args, name))
    value = json.loads(path.read_text())
    update(value)
    path.write_text(json.dumps(value))


def weaken_tls_policy(value: dict[str, object]) -> None:
    policy = json.loads(value["Policy"])
    policy["Statement"][0]["Condition"]["Bool"]["aws:SecureTransport"] = "true"
    value["Policy"] = json.dumps(policy)


def test_exact_live_bucket_contract_passes(tmp_path: Path) -> None:
    assert target.validate(documents(tmp_path)) == {
        "valid": True,
        "bucket": BUCKET,
        "region": "us-east-1",
    }


@pytest.mark.parametrize(
    ("name", "update", "message"),
    [
        (
            "public_access_block",
            lambda value: value["PublicAccessBlockConfiguration"].update(
                BlockPublicPolicy=False
            ),
            "public-access",
        ),
        (
            "encryption",
            lambda value: value["ServerSideEncryptionConfiguration"]["Rules"][0][
                "ApplyServerSideEncryptionByDefault"
            ].update(SSEAlgorithm="aws:kms"),
            "SSE-S3",
        ),
        ("versioning", lambda value: value.update(Status="Suspended"), "versioning"),
        (
            "ownership",
            lambda value: value["OwnershipControls"]["Rules"][0].update(
                ObjectOwnership="ObjectWriter"
            ),
            "ownership",
        ),
        (
            "location",
            lambda value: value.update(LocationConstraint="us-west-2"),
            "us-east-1",
        ),
        (
            "lifecycle",
            lambda value: value["Rules"][0]["Expiration"].update(Days=30),
            "DeleteExpiredBackups",
        ),
        (
            "policy",
            weaken_tls_policy,
            "TLS-only",
        ),
    ],
)
def test_live_bucket_drift_is_rejected(
    tmp_path: Path, name: str, update, message: str
) -> None:
    args = documents(tmp_path)
    change(args, name, update)
    with pytest.raises(target.TargetError, match=message):
        target.validate(args)
