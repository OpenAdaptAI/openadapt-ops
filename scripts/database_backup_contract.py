#!/usr/bin/env python3
"""Fail-closed contracts for encrypted production database backups.

This module never connects to a database. The workflows keep database access in
the Supabase CLI and psql. This module validates target identity, verifies dump
components, creates a redacted integrity manifest, and records restore evidence.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

CONTRACT_SCHEMA = "openadapt.database-backup-contract/v2"
ARTIFACT_SCHEMA = "openadapt.database-backup-artifact/v2"
RESTORE_EVIDENCE_SCHEMA = "openadapt.database-restore-evidence/v2"
S3_UPLOAD_SCHEMA = "openadapt.database-backup-s3-upload/v2"
S3_SINGLE_PUT_MAX_BYTES = 5 * 1024 * 1024 * 1024
CIPHERTEXT_STORAGE_CLASS = "GLACIER_IR"
MANIFEST_STORAGE_CLASS = "STANDARD"
PROJECT_REF = re.compile(r"^[a-z0-9]{8,64}$")
AGE_RECIPIENT = re.compile(r"^age1[0-9a-z]+$")
REQUIRED_DUMPS = ("roles.sql", "schema.sql", "data.sql")
ARCHIVE_MEMBERS = (*REQUIRED_DUMPS, "backup-contract.json")
MAX_ARCHIVE_MEMBER_BYTES = 2 * 1024 * 1024 * 1024
UNSAFE_PSQL_COMMAND = re.compile(
    r"^\\(?:!|cd|copy|e(?:dit)?|i|ir|o|out|qecho|setenv|w(?:rite)?)(?:\s|$)",
    re.MULTILINE | re.IGNORECASE,
)
COPY_PROGRAM = re.compile(r"\bCOPY\b[^;]*\bPROGRAM\b", re.IGNORECASE | re.DOTALL)
RESTRICT_MARKER = re.compile(
    r"^-- \\(?P<operation>un)?restrict (?P<key>[A-Za-z0-9]+)\r?\n?$"
)
COPY_FROM_STDIN = re.compile(r"^COPY\s.+\sFROM\sstdin;\r?\n?$", re.IGNORECASE)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
VERSION_ID = re.compile(r"^[^\s/]{1,1024}$")
RECOVERY_POINT_STAMP = re.compile(r"^\d{8}T\d{6}Z$")
BACKUP_BUCKET = "openadapt-production-db-backups-992382684924"
AWS_ACCOUNT_ID = "992382684924"
AWS_REGION = "us-east-1"


class ContractError(ValueError):
    """A backup or restore contract is unsafe or incomplete."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def gibibytes(value: int) -> str:
    """Return a stable, human-readable GiB measurement while bytes stay authoritative."""
    return f"{value / (1024**3):.9f}"


def project_ref(value: str, name: str) -> str:
    value = value.strip()
    if not PROJECT_REF.fullmatch(value):
        raise ContractError(f"{name} is not a valid Supabase project reference")
    return value


def database_identity(url: str, expected_ref: str, name: str) -> dict[str, str]:
    expected_ref = project_ref(expected_ref, f"{name} project reference")
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ContractError(f"{name} must use a postgres connection URL")
    if not parsed.hostname or not parsed.username or not parsed.path.strip("/"):
        raise ContractError(f"{name} is incomplete")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise ContractError(f"{name} must name the declared Supabase project")

    username = unquote(parsed.username)
    direct_host = parsed.hostname == f"db.{expected_ref}.supabase.co"
    pooler_user = username == f"postgres.{expected_ref}"
    pooler_host = parsed.hostname.endswith(".pooler.supabase.com")
    if not direct_host and not (pooler_user and pooler_host):
        raise ContractError(f"{name} does not match the declared Supabase project")

    # This digest lets an operator compare identities without publishing the
    # project reference, hostname, username, or connection string.
    canonical = f"{expected_ref}|{parsed.hostname}|{username}|{parsed.path.strip('/')}"
    return {
        "identity_sha256": sha256_text(canonical),
        "project_ref_sha256": sha256_text(expected_ref),
    }


def recipients(path: Path) -> list[str]:
    values = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not values or any(not AGE_RECIPIENT.fullmatch(value) for value in values):
        raise ContractError(
            "the recipient file must contain only age public recipients"
        )
    if len(values) != len(set(values)):
        raise ContractError("the recipient file contains a duplicate recipient")
    return sorted(values)


def dump_inventory(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for name in REQUIRED_DUMPS:
        path = root / name
        if not path.is_file() or path.stat().st_size <= 0:
            raise ContractError(f"database dump component is missing or empty: {name}")
        result.append(
            {"name": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )

    schema = (root / "schema.sql").read_text(encoding="utf-8", errors="replace")
    data = (root / "data.sql").read_text(encoding="utf-8", errors="replace")
    for name in REQUIRED_DUMPS:
        sql = (root / name).read_text(encoding="utf-8", errors="replace")
        if UNSAFE_PSQL_COMMAND.search(sql) or COPY_PROGRAM.search(sql):
            raise ContractError(
                f"database dump contains an unsafe local command: {name}"
            )
    if not re.search(r"^CREATE\s", schema, re.MULTILINE | re.IGNORECASE):
        raise ContractError("schema.sql contains no CREATE statement")
    if not re.search(r"^COPY\s", data, re.MULTILINE | re.IGNORECASE):
        raise ContractError("data.sql contains no COPY statement")
    return result


def comparison_sha256(path: Path) -> str:
    """Hash a dump while normalizing only pg_dump's random guard key.

    Patched PostgreSQL clients generate a fresh ``\\restrict`` key for every
    plain-text dump. Supabase CLI comments those two guard commands instead of
    removing them. A source dump and a correct scratch redump therefore differ
    in those random keys. The restore check must ignore that non-data value,
    but it must never rewrite a matching line inside COPY data.
    """

    digest = hashlib.sha256()
    markers: list[tuple[str, str]] = []
    in_copy = False
    with path.open("r", encoding="utf-8", errors="strict", newline="") as stream:
        for line in stream:
            marker = RESTRICT_MARKER.fullmatch(line) if not in_copy else None
            if marker is not None:
                operation = "unrestrict" if marker.group("operation") else "restrict"
                markers.append((operation, marker.group("key")))
                digest.update(f"-- \\{operation} OPENADAPT_RANDOM_KEY\n".encode())
                continue

            digest.update(line.encode())
            if not in_copy and COPY_FROM_STDIN.fullmatch(line):
                in_copy = True
            elif in_copy and line.rstrip("\r\n") == r"\.":
                in_copy = False

    if in_copy:
        raise ContractError(
            f"the restored dump has an unterminated COPY block: {path.name}"
        )
    if markers and (
        len(markers) != 2
        or markers[0][0] != "restrict"
        or markers[1][0] != "unrestrict"
        or markers[0][1] != markers[1][1]
    ):
        raise ContractError(
            f"the restored dump has an invalid pg_dump restriction guard: {path.name}"
        )
    return digest.hexdigest()


def parse_time(value: str, name: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"{name} is not an ISO-8601 timestamp") from error
    if result.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return result.astimezone(timezone.utc)


def read_contract(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != CONTRACT_SCHEMA:
        raise ContractError("the backup contract schema is not supported")
    contract = value.get("contract")
    if not isinstance(contract, dict):
        raise ContractError("the backup contract is missing")
    expected = sha256_text(stable_json(contract))
    if value.get("contract_sha256") != expected:
        raise ContractError("the backup contract digest is invalid")
    return value


def read_manifest(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != ARTIFACT_SCHEMA:
        raise ContractError("the artifact manifest schema is not supported")
    manifest = value.get("artifact")
    if not isinstance(manifest, dict):
        raise ContractError("the artifact manifest is missing")
    expected = sha256_text(stable_json(manifest))
    if value.get("artifact_sha256") != expected:
        raise ContractError("the artifact manifest digest is invalid")
    return value


def validate_source(args: argparse.Namespace) -> None:
    identity = database_identity(args.db_url, args.project_ref, "production database")
    keys = recipients(Path(args.recipients))
    print(
        json.dumps(
            {
                "valid": True,
                **identity,
                "recipient_count": len(keys),
                "recipients_sha256": sha256_text("\n".join(keys) + "\n"),
            },
            sort_keys=True,
        )
    )


def create_contract(args: argparse.Namespace) -> None:
    source_ref = project_ref(args.project_ref, "production project reference")
    keys = recipients(Path(args.recipients))
    created = parse_time(args.created_at, "created-at")
    dump_files = dump_inventory(Path(args.dump_dir))
    contract: dict[str, object] = {
        "source_project_ref_sha256": sha256_text(source_ref),
        "created_at": created.isoformat().replace("+00:00", "Z"),
        "maximum_rpo_seconds": args.maximum_rpo_seconds,
        "retention_days": args.retention_days,
        "dump_files": dump_files,
        "recipients_sha256": sha256_text("\n".join(keys) + "\n"),
        "supabase_cli_version": args.supabase_cli_version,
    }
    envelope = {
        "schema": CONTRACT_SCHEMA,
        "contract": contract,
        "contract_sha256": sha256_text(stable_json(contract)),
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"contract": str(output), "contract_sha256": envelope["contract_sha256"]}
        )
    )


def create_manifest(args: argparse.Namespace) -> None:
    contract = read_contract(Path(args.contract))
    plaintext = Path(args.plaintext_archive)
    ciphertext = Path(args.ciphertext_archive)
    if not plaintext.is_file() or plaintext.stat().st_size <= 0:
        raise ContractError("the plaintext archive is missing or empty")
    if not ciphertext.is_file() or ciphertext.stat().st_size <= 0:
        raise ContractError("the encrypted archive is missing or empty")
    artifact: dict[str, object] = {
        "backup_contract_sha256": contract["contract_sha256"],
        "plaintext_archive": {
            "bytes": plaintext.stat().st_size,
            "sha256": sha256_file(plaintext),
        },
        "ciphertext_archive": {
            "bytes": ciphertext.stat().st_size,
            "sha256": sha256_file(ciphertext),
        },
        "repository_commit": args.repository_commit,
        "workflow_run_id": args.workflow_run_id,
    }
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "artifact": artifact,
        "artifact_sha256": sha256_text(stable_json(artifact)),
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"manifest": str(output), "artifact_sha256": manifest["artifact_sha256"]}
        )
    )


def verify_artifact(args: argparse.Namespace) -> None:
    manifest = read_manifest(Path(args.manifest))
    artifact = manifest["artifact"]
    assert isinstance(artifact, dict)
    ciphertext = Path(args.ciphertext_archive)
    expected = artifact.get("ciphertext_archive")
    if not isinstance(expected, dict):
        raise ContractError("the encrypted archive contract is missing")
    if expected.get("bytes") != ciphertext.stat().st_size or expected.get(
        "sha256"
    ) != sha256_file(ciphertext):
        raise ContractError("the encrypted archive does not match the manifest")
    print(json.dumps({"valid": True, "artifact_sha256": manifest["artifact_sha256"]}))


def single_put_contract(
    ciphertext: Path,
    manifest_path: Path,
    *,
    maximum_bytes: int = S3_SINGLE_PUT_MAX_BYTES,
) -> dict[str, object]:
    """Bind one ciphertext to an S3-validated full-object SHA-256 checksum."""
    if maximum_bytes <= 0:
        raise ContractError("the S3 single-PutObject limit must be positive")
    if not ciphertext.is_file():
        raise ContractError("the encrypted archive is missing")
    size = ciphertext.stat().st_size
    if size <= 0:
        raise ContractError("the encrypted archive is empty")
    if size > maximum_bytes:
        raise ContractError(
            "the encrypted archive exceeds the 5 GiB single-PutObject launch limit"
        )

    contract = single_put_contract_from_manifest(
        manifest_path, maximum_bytes=maximum_bytes
    )
    digest = sha256_file(ciphertext)
    if contract["bytes"] != size or contract["sha256"] != digest:
        raise ContractError("the encrypted archive does not match the manifest")
    return contract


def single_put_contract_from_manifest(
    manifest_path: Path,
    *,
    maximum_bytes: int = S3_SINGLE_PUT_MAX_BYTES,
) -> dict[str, object]:
    """Rebuild the exact upload contract from a retained redacted manifest."""
    if maximum_bytes <= 0:
        raise ContractError("the S3 single-PutObject limit must be positive")
    manifest = read_manifest(manifest_path)
    artifact = manifest["artifact"]
    assert isinstance(artifact, dict)
    expected = artifact.get("ciphertext_archive")
    if not isinstance(expected, dict):
        raise ContractError("the encrypted archive contract is missing")
    size = expected.get("bytes")
    digest = expected.get("sha256")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size <= 0
        or size > maximum_bytes
    ):
        raise ContractError("the encrypted archive size in the manifest is invalid")
    if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
        raise ContractError("the encrypted archive digest in the manifest is invalid")

    return {
        "schema": S3_UPLOAD_SCHEMA,
        "bytes": size,
        "encrypted_archive_gib": gibibytes(size),
        "storage_class": CIPHERTEXT_STORAGE_CLASS,
        "sha256": digest,
        "checksum_algorithm": "SHA256",
        "checksum_type": "FULL_OBJECT",
        "checksum_sha256": base64.b64encode(bytes.fromhex(digest)).decode(),
        "maximum_bytes": maximum_bytes,
    }


def recover_single_put(args: argparse.Namespace) -> None:
    """Verify a completed ciphertext PutObject and rebuild its local contract."""
    manifest_path = Path(args.manifest)
    contract = single_put_contract_from_manifest(manifest_path)
    head = json.loads(Path(args.ciphertext_head).read_text(encoding="utf-8"))
    if not isinstance(head, dict):
        raise ContractError("the retained ciphertext head response is invalid")
    require_version_id(head.get("VersionId"), "ciphertext")
    if head.get("ContentLength") != contract["bytes"]:
        raise ContractError("the retained ciphertext size does not match")
    if head.get("StorageClass") != CIPHERTEXT_STORAGE_CLASS:
        raise ContractError("the retained ciphertext is not in GLACIER_IR")
    if head.get("ServerSideEncryption") != "AES256":
        raise ContractError("the retained ciphertext is not encrypted with SSE-S3")
    if head.get("ChecksumSHA256") != contract["checksum_sha256"]:
        raise ContractError("the retained ciphertext checksum does not match")
    metadata = head.get("Metadata")
    if not isinstance(metadata, dict) or metadata.get("sha256") != contract["sha256"]:
        raise ContractError("the retained ciphertext digest metadata does not match")
    manifest_b64 = base64.b64encode(manifest_path.read_bytes()).decode()
    if metadata.get("artifact-manifest-base64") != manifest_b64:
        raise ContractError("the retained ciphertext manifest metadata does not match")
    output = Path(args.output)
    output.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "recovered": True,
                "ciphertext_version_id": head["VersionId"],
                "upload_contract": str(output),
            },
            sort_keys=True,
        )
    )


def read_single_put_contract(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != S3_UPLOAD_SCHEMA:
        raise ContractError("the S3 upload contract schema is invalid")
    if value.get("checksum_algorithm") != "SHA256":
        raise ContractError("the S3 upload checksum algorithm is invalid")
    if value.get("checksum_type") != "FULL_OBJECT":
        raise ContractError("the S3 upload checksum type is invalid")
    size = value.get("bytes")
    maximum = value.get("maximum_bytes")
    digest = value.get("sha256")
    encoded = value.get("checksum_sha256")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size <= 0
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum != S3_SINGLE_PUT_MAX_BYTES
        or size > maximum
    ):
        raise ContractError("the S3 upload size contract is invalid")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ContractError("the S3 upload SHA-256 is invalid")
    if encoded != base64.b64encode(bytes.fromhex(digest)).decode():
        raise ContractError("the S3 upload checksum encoding is invalid")
    if value.get("storage_class") != CIPHERTEXT_STORAGE_CLASS:
        raise ContractError("the S3 upload storage class is invalid")
    if value.get("encrypted_archive_gib") != gibibytes(size):
        raise ContractError("the encrypted archive GiB measurement is invalid")
    return value


def prepare_single_put(args: argparse.Namespace) -> None:
    value = single_put_contract(Path(args.ciphertext_archive), Path(args.manifest))
    output = Path(args.output)
    output.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "upload_contract": str(output),
                "bytes": value["bytes"],
                "encrypted_archive_gib": value["encrypted_archive_gib"],
                "storage_class": value["storage_class"],
                "checksum_type": value["checksum_type"],
            },
            sort_keys=True,
        )
    )


def verify_single_put(args: argparse.Namespace) -> None:
    contract = read_single_put_contract(Path(args.upload_contract))
    attributes = json.loads(Path(args.attributes).read_text(encoding="utf-8"))
    if not isinstance(attributes, dict):
        raise ContractError("the S3 object attributes are invalid")
    if attributes.get("ObjectSize") != contract["bytes"]:
        raise ContractError("the S3 object size does not match the upload contract")
    if attributes.get("StorageClass") != CIPHERTEXT_STORAGE_CLASS:
        raise ContractError("the encrypted archive is not in GLACIER_IR")
    checksum = attributes.get("Checksum")
    if not isinstance(checksum, dict):
        raise ContractError("the S3 object checksum is missing")
    if checksum.get("ChecksumSHA256") != contract["checksum_sha256"]:
        raise ContractError("the S3 full-object checksum does not match")
    print(
        json.dumps(
            {
                "valid": True,
                "bytes": contract["bytes"],
                "encrypted_archive_gib": contract["encrypted_archive_gib"],
                "storage_class": contract["storage_class"],
                "checksum_type": "FULL_OBJECT",
                "sha256": contract["sha256"],
            },
            sort_keys=True,
        )
    )


def require_version_id(value: object, name: str) -> str:
    if not isinstance(value, str) or VERSION_ID.fullmatch(value) is None:
        raise ContractError(f"the {name} S3 version ID is invalid")
    return value


def uploaded_pair_evidence(args: argparse.Namespace) -> dict[str, object]:
    """Verify and bind the exact immutable S3 versions of one backup pair."""
    if args.bucket != BACKUP_BUCKET:
        raise ContractError("the S3 backup bucket is invalid")
    if RECOVERY_POINT_STAMP.fullmatch(args.recovery_point_stamp) is None:
        raise ContractError("the recovery point stamp is invalid")
    if re.fullmatch(r"[0-9a-f]{40}", args.repository_commit) is None:
        raise ContractError("the backup repository commit is invalid")
    if re.fullmatch(r"[1-9][0-9]*", args.workflow_run_id) is None:
        raise ContractError("the backup workflow run ID is invalid")

    contract = read_single_put_contract(Path(args.upload_contract))
    manifest_path = Path(args.manifest)
    manifest = read_manifest(manifest_path)
    artifact = manifest["artifact"]
    assert isinstance(artifact, dict)
    if artifact.get("repository_commit") != args.repository_commit:
        raise ContractError("the artifact commit does not match the current backup")
    if artifact.get("workflow_run_id") != args.workflow_run_id:
        raise ContractError("the artifact run ID does not match the current backup")

    responses: dict[str, dict[str, object]] = {}
    attributes: dict[str, dict[str, object]] = {}
    for name, response_path, attributes_path in (
        ("ciphertext", args.ciphertext_response, args.ciphertext_attributes),
        ("manifest", args.manifest_response, args.manifest_attributes),
    ):
        response = json.loads(Path(response_path).read_text(encoding="utf-8"))
        remote = json.loads(Path(attributes_path).read_text(encoding="utf-8"))
        if not isinstance(response, dict) or not isinstance(remote, dict):
            raise ContractError(f"the {name} S3 verification response is invalid")
        version_id = require_version_id(response.get("VersionId"), name)
        if remote.get("VersionId") != version_id:
            raise ContractError(f"the {name} S3 version changed during verification")
        responses[name] = response
        attributes[name] = remote

    cipher = attributes["ciphertext"]
    if cipher.get("ObjectSize") != contract["bytes"]:
        raise ContractError("the S3 object size does not match the upload contract")
    if cipher.get("StorageClass") != CIPHERTEXT_STORAGE_CLASS:
        raise ContractError("the encrypted archive is not in GLACIER_IR")
    cipher_checksums = cipher.get("Checksum")
    if not isinstance(cipher_checksums, dict) or cipher_checksums.get(
        "ChecksumSHA256"
    ) != contract.get("checksum_sha256"):
        raise ContractError("the S3 full-object checksum does not match")

    manifest_bytes = manifest_path.stat().st_size
    manifest_sha = sha256_file(manifest_path)
    manifest_checksum = base64.b64encode(bytes.fromhex(manifest_sha)).decode()
    manifest_remote = attributes["manifest"]
    manifest_checksums = manifest_remote.get("Checksum")
    if manifest_remote.get("ObjectSize") != manifest_bytes:
        raise ContractError("the S3 manifest size does not match the local manifest")
    if manifest_remote.get("StorageClass") != MANIFEST_STORAGE_CLASS:
        raise ContractError("the artifact manifest is not in STANDARD")
    if (
        not isinstance(manifest_checksums, dict)
        or manifest_checksums.get("ChecksumSHA256") != manifest_checksum
    ):
        raise ContractError("the S3 manifest checksum does not match")

    stamp = args.recovery_point_stamp
    cipher_key = f"daily/{stamp}/db-backup-{stamp}.tar.gz.age"
    manifest_key = f"daily/{stamp}/artifact-manifest.json"
    return {
        "artifact_sha256": manifest["artifact_sha256"],
        "aws_account_id": AWS_ACCOUNT_ID,
        "aws_region": AWS_REGION,
        "backup_contract_sha256": artifact["backup_contract_sha256"],
        "bucket_name": args.bucket,
        "ciphertext_bytes": contract["bytes"],
        "ciphertext_checksum_sha256": contract["checksum_sha256"],
        "ciphertext_gib": contract["encrypted_archive_gib"],
        "ciphertext_key": cipher_key,
        "ciphertext_sha256": contract["sha256"],
        "ciphertext_storage_class": CIPHERTEXT_STORAGE_CLASS,
        "ciphertext_version_id": responses["ciphertext"]["VersionId"],
        "manifest_checksum_sha256": manifest_checksum,
        "manifest_key": manifest_key,
        "manifest_sha256": manifest_sha,
        "manifest_storage_class": MANIFEST_STORAGE_CLASS,
        "manifest_version_id": responses["manifest"]["VersionId"],
        "recovery_point_stamp": stamp,
        "repository_commit": args.repository_commit,
        "workflow_run_id": args.workflow_run_id,
    }


def verify_uploaded_pair(args: argparse.Namespace) -> None:
    evidence = uploaded_pair_evidence(args)
    output = Path(args.output)
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "valid": True,
                "evidence": str(output),
                "ciphertext_version_id": evidence["ciphertext_version_id"],
                "manifest_version_id": evidence["manifest_version_id"],
            },
            sort_keys=True,
        )
    )


def verify_storage_classes(args: argparse.Namespace) -> None:
    values = (
        (
            json.loads(Path(args.manifest_attributes).read_text(encoding="utf-8")),
            "artifact manifest",
            MANIFEST_STORAGE_CLASS,
        ),
        (
            json.loads(Path(args.ciphertext_attributes).read_text(encoding="utf-8")),
            "encrypted archive",
            CIPHERTEXT_STORAGE_CLASS,
        ),
    )
    for attributes, name, expected_class in values:
        if not isinstance(attributes, dict):
            raise ContractError(f"the {name} S3 attributes are invalid")
        size = attributes.get("ObjectSize")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ContractError(f"the {name} S3 object size is invalid")
        if attributes.get("StorageClass") != expected_class:
            raise ContractError(
                f"the {name} is not in the required {expected_class} storage class"
            )
    print(
        json.dumps(
            {
                "valid": True,
                "manifest_storage_class": MANIFEST_STORAGE_CLASS,
                "ciphertext_storage_class": CIPHERTEXT_STORAGE_CLASS,
            },
            sort_keys=True,
        )
    )


def validate_restore_target(args: argparse.Namespace) -> None:
    source_ref = project_ref(args.source_project_ref, "production project reference")
    scratch_ref = project_ref(args.scratch_project_ref, "scratch project reference")
    if source_ref == scratch_ref:
        raise ContractError("the restore target is the production project")
    identity = database_identity(args.scratch_db_url, scratch_ref, "scratch database")
    print(json.dumps({"valid": True, **identity}, sort_keys=True))


def extract_artifact(args: argparse.Namespace) -> None:
    archive = Path(args.plaintext_archive)
    manifest = read_manifest(Path(args.manifest))
    artifact = manifest["artifact"]
    assert isinstance(artifact, dict)
    expected_archive = artifact.get("plaintext_archive")
    if not isinstance(expected_archive, dict):
        raise ContractError("the plaintext archive contract is missing")
    if expected_archive.get("bytes") != archive.stat().st_size or expected_archive.get(
        "sha256"
    ) != sha256_file(archive):
        raise ContractError("the decrypted archive does not match the manifest")
    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()):
        raise ContractError("the extraction directory is not empty")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)

    with tarfile.open(archive, mode="r:gz") as bundle:
        members = bundle.getmembers()
        names = [member.name for member in members]
        if sorted(names) != sorted(ARCHIVE_MEMBERS):
            raise ContractError("the archive member allowlist does not match")
        for member in members:
            if not member.isfile():
                raise ContractError("the archive contains a non-regular member")
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise ContractError("the archive contains an unsafe member path")
            if member.size <= 0 or member.size > MAX_ARCHIVE_MEMBER_BYTES:
                raise ContractError("the archive contains an invalid member size")
            source = bundle.extractfile(member)
            if source is None:
                raise ContractError("the archive member is not readable")
            destination = output / member.name
            with destination.open("xb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
            destination.chmod(0o600)

    contract = read_contract(output / "backup-contract.json")
    if artifact.get("backup_contract_sha256") != contract.get("contract_sha256"):
        raise ContractError("the decrypted backup contract does not match the manifest")
    inventory = dump_inventory(output)
    expected = contract["contract"].get("dump_files")
    if stable_json(inventory) != stable_json(expected):
        raise ContractError("the extracted dump files do not match the backup contract")
    print(json.dumps({"valid": True, "contract_sha256": contract["contract_sha256"]}))


def verify_restored_dumps(args: argparse.Namespace) -> None:
    source = {entry["name"]: entry for entry in dump_inventory(Path(args.source_dir))}
    restored: dict[str, dict[str, object]] = {}
    comparison: dict[str, dict[str, str]] = {}
    for name in ("schema.sql", "data.sql"):
        source_path = Path(args.source_dir) / name
        restored_path = Path(args.restored_dir) / name
        if not restored_path.is_file() or restored_path.stat().st_size <= 0:
            raise ContractError(f"the restored dump is missing or empty: {name}")
        restored[name] = {
            "name": name,
            "bytes": restored_path.stat().st_size,
            "sha256": sha256_file(restored_path),
        }
        comparison[name] = {
            "source": comparison_sha256(source_path),
            "restored": comparison_sha256(restored_path),
        }
    # Roles are target-specific. Schema and data must reproduce exactly.
    for name in ("schema.sql", "data.sql"):
        if comparison[name]["source"] != comparison[name]["restored"]:
            raise ContractError(f"the restored {name} does not match the backup")
    print(
        json.dumps(
            {
                "valid": True,
                "schema_sha256": source["schema.sql"]["sha256"],
                "data_sha256": source["data.sql"]["sha256"],
                "schema_comparison_sha256": comparison["schema.sql"]["source"],
                "data_comparison_sha256": comparison["data.sql"]["source"],
            },
            sort_keys=True,
        )
    )


def record_restore(args: argparse.Namespace) -> None:
    manifest = read_manifest(Path(args.manifest))
    contract = read_contract(Path(args.contract))
    source_ref = project_ref(args.source_project_ref, "production project reference")
    scratch_ref = project_ref(args.scratch_project_ref, "scratch project reference")
    if source_ref == scratch_ref:
        raise ContractError("the restore target is the production project")
    artifact = manifest["artifact"]
    assert isinstance(artifact, dict)
    payload = contract["contract"]
    assert isinstance(payload, dict)
    if artifact.get("backup_contract_sha256") != contract.get("contract_sha256"):
        raise ContractError("the artifact and backup contract do not match")
    if payload.get("source_project_ref_sha256") != sha256_text(source_ref):
        raise ContractError(
            "the backup does not belong to the declared production project"
        )

    verification = json.loads(Path(args.verification).read_text(encoding="utf-8"))
    if verification.get("valid") is not True:
        raise ContractError("the scratch restore verification did not pass")
    dump_files = payload.get("dump_files")
    if not isinstance(dump_files, list):
        raise ContractError("the backup contract has no dump inventory")
    expected_digests = {
        entry.get("name"): entry.get("sha256")
        for entry in dump_files
        if isinstance(entry, dict)
    }
    for name in ("schema", "data"):
        if verification.get(f"{name}_sha256") != expected_digests.get(f"{name}.sql"):
            raise ContractError(
                "the restore verification does not match the backup contract"
            )
        comparison_digest = verification.get(f"{name}_comparison_sha256")
        if (
            not isinstance(comparison_digest, str)
            or SHA256.fullmatch(comparison_digest) is None
        ):
            raise ContractError("the restore comparison digest is invalid")
    started = parse_time(args.started_at, "started-at")
    completed = parse_time(args.completed_at, "completed-at")
    if completed < started:
        raise ContractError("the restore completion time precedes the start time")
    recovery_point = parse_time(str(payload.get("created_at")), "backup recovery point")
    stamp = recovery_point.strftime("%Y%m%dT%H%M%SZ")
    expected_ciphertext_key = f"daily/{stamp}/db-backup-{stamp}.tar.gz.age"
    expected_manifest_key = f"daily/{stamp}/artifact-manifest.json"
    if args.aws_account_id != AWS_ACCOUNT_ID:
        raise ContractError("the restore evidence AWS account is invalid")
    if args.aws_region != AWS_REGION:
        raise ContractError("the restore evidence AWS region is invalid")
    if args.bucket_name != BACKUP_BUCKET:
        raise ContractError("the restore evidence bucket is invalid")
    if args.ciphertext_key != expected_ciphertext_key:
        raise ContractError("the restore evidence ciphertext key is invalid")
    if args.manifest_key != expected_manifest_key:
        raise ContractError("the restore evidence manifest key is invalid")
    ciphertext_version_id = require_version_id(args.ciphertext_version_id, "ciphertext")
    manifest_version_id = require_version_id(args.manifest_version_id, "manifest")
    receipt = {
        "schema": RESTORE_EVIDENCE_SCHEMA,
        "backup_contract_sha256": contract["contract_sha256"],
        "artifact_sha256": manifest["artifact_sha256"],
        "aws_account_id": args.aws_account_id,
        "aws_region": args.aws_region,
        "bucket_name": args.bucket_name,
        "ciphertext_key": args.ciphertext_key,
        "ciphertext_version_id": ciphertext_version_id,
        "manifest_key": args.manifest_key,
        "manifest_version_id": manifest_version_id,
        "source_project_ref_sha256": sha256_text(source_ref),
        "scratch_project_ref_sha256": sha256_text(scratch_ref),
        "recovery_point_at": recovery_point.isoformat().replace("+00:00", "Z"),
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "completed_at": completed.isoformat().replace("+00:00", "Z"),
        "rpo_seconds_at_start": max(0, int((started - recovery_point).total_seconds())),
        "rto_seconds": int((completed - started).total_seconds()),
        "schema_sha256": verification["schema_sha256"],
        "data_sha256": verification["data_sha256"],
        "schema_comparison_sha256": verification["schema_comparison_sha256"],
        "data_comparison_sha256": verification["data_comparison_sha256"],
        "database_restored": True,
        "storage_restored": False,
    }
    output = Path(args.output)
    try:
        with output.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as error:
        raise ContractError("the restore evidence output already exists") from error
    print(json.dumps({"receipt": str(output), "rto_seconds": receipt["rto_seconds"]}))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    source = commands.add_parser("validate-source")
    source.add_argument("--db-url", required=True)
    source.add_argument("--project-ref", required=True)
    source.add_argument("--recipients", required=True)
    source.set_defaults(run=validate_source)

    contract = commands.add_parser("create-contract")
    contract.add_argument("--project-ref", required=True)
    contract.add_argument("--recipients", required=True)
    contract.add_argument("--dump-dir", required=True)
    contract.add_argument("--created-at", required=True)
    contract.add_argument("--supabase-cli-version", required=True)
    contract.add_argument("--maximum-rpo-seconds", type=int, default=86400)
    contract.add_argument("--retention-days", type=int, default=90)
    contract.add_argument("--output", required=True)
    contract.set_defaults(run=create_contract)

    manifest = commands.add_parser("create-manifest")
    manifest.add_argument("--contract", required=True)
    manifest.add_argument("--plaintext-archive", required=True)
    manifest.add_argument("--ciphertext-archive", required=True)
    manifest.add_argument("--repository-commit", required=True)
    manifest.add_argument("--workflow-run-id", required=True)
    manifest.add_argument("--output", required=True)
    manifest.set_defaults(run=create_manifest)

    artifact = commands.add_parser("verify-artifact")
    artifact.add_argument("--manifest", required=True)
    artifact.add_argument("--ciphertext-archive", required=True)
    artifact.set_defaults(run=verify_artifact)

    upload = commands.add_parser("prepare-single-put")
    upload.add_argument("--manifest", required=True)
    upload.add_argument("--ciphertext-archive", required=True)
    upload.add_argument("--output", required=True)
    upload.set_defaults(run=prepare_single_put)

    recover_upload = commands.add_parser("recover-single-put")
    recover_upload.add_argument("--manifest", required=True)
    recover_upload.add_argument("--ciphertext-head", required=True)
    recover_upload.add_argument("--output", required=True)
    recover_upload.set_defaults(run=recover_single_put)

    uploaded = commands.add_parser("verify-single-put")
    uploaded.add_argument("--upload-contract", required=True)
    uploaded.add_argument("--attributes", required=True)
    uploaded.set_defaults(run=verify_single_put)

    pair = commands.add_parser("verify-uploaded-pair")
    pair.add_argument("--bucket", required=True)
    pair.add_argument("--recovery-point-stamp", required=True)
    pair.add_argument("--repository-commit", required=True)
    pair.add_argument("--workflow-run-id", required=True)
    pair.add_argument("--manifest", required=True)
    pair.add_argument("--upload-contract", required=True)
    pair.add_argument("--ciphertext-response", required=True)
    pair.add_argument("--ciphertext-attributes", required=True)
    pair.add_argument("--manifest-response", required=True)
    pair.add_argument("--manifest-attributes", required=True)
    pair.add_argument("--output", required=True)
    pair.set_defaults(run=verify_uploaded_pair)

    stored = commands.add_parser("verify-storage-classes")
    stored.add_argument("--manifest-attributes", required=True)
    stored.add_argument("--ciphertext-attributes", required=True)
    stored.set_defaults(run=verify_storage_classes)

    target = commands.add_parser("validate-restore-target")
    target.add_argument("--source-project-ref", required=True)
    target.add_argument("--scratch-project-ref", required=True)
    target.add_argument("--scratch-db-url", required=True)
    target.set_defaults(run=validate_restore_target)

    extract = commands.add_parser("extract-artifact")
    extract.add_argument("--plaintext-archive", required=True)
    extract.add_argument("--manifest", required=True)
    extract.add_argument("--output-dir", required=True)
    extract.set_defaults(run=extract_artifact)

    restored = commands.add_parser("verify-restored-dumps")
    restored.add_argument("--source-dir", required=True)
    restored.add_argument("--restored-dir", required=True)
    restored.set_defaults(run=verify_restored_dumps)

    receipt = commands.add_parser("record-restore")
    receipt.add_argument("--manifest", required=True)
    receipt.add_argument("--contract", required=True)
    receipt.add_argument("--verification", required=True)
    receipt.add_argument("--source-project-ref", required=True)
    receipt.add_argument("--scratch-project-ref", required=True)
    receipt.add_argument("--started-at", required=True)
    receipt.add_argument("--completed-at", required=True)
    receipt.add_argument("--aws-account-id", required=True)
    receipt.add_argument("--aws-region", required=True)
    receipt.add_argument("--bucket-name", required=True)
    receipt.add_argument("--ciphertext-key", required=True)
    receipt.add_argument("--ciphertext-version-id", required=True)
    receipt.add_argument("--manifest-key", required=True)
    receipt.add_argument("--manifest-version-id", required=True)
    receipt.add_argument("--output", required=True)
    receipt.set_defaults(run=record_restore)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.run(args)
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
