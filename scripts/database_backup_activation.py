#!/usr/bin/env python3
"""Validate and advance the paid-customer database-backup activation gate.

This module has no Stripe, GitHub, AWS, or database client. The activation
workflow owns those transports. This module keeps their payloads opaque,
digest-bound, signed, and retry-safe.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REQUEST_SCHEMA = "openadapt.database-backup-activation-request/v1"
STATE_SCHEMA = "openadapt.database-backup-activation-state/v1"
SIGNED_STATE_SCHEMA = "openadapt.database-backup-activation-signed-state/v1"
RECEIPT_SCHEMA = "openadapt.database-backup-readiness-receipt/v1"
CLOUD_ACK_SCHEMA = "openadapt.database-backup-cloud-readiness-ack/v2"
RESTORE_SCHEMA = "openadapt.database-restore-evidence/v2"
SIGNATURE_ALGORITHM = "HMAC-SHA256"
PAYMENT_SIGNAL_ISSUER = "openadapt-cloud"
PAYMENT_SIGNAL_AUDIENCE = "OpenAdaptAI/openadapt-ops:database-backup-activation"
PAYMENT_SIGNAL_KEY_ID = "cloud-payment-signal-hmac-2026-01"
READINESS_ISSUER = "openadapt-ops"
READINESS_AUDIENCE = "openadapt-cloud:database-backup-readiness"
READINESS_KEY_ID = "ops-database-readiness-hmac-2026-01"
CLOUD_ACK_ISSUER = "openadapt-cloud"
CLOUD_ACK_AUDIENCE = "OpenAdaptAI/openadapt-ops:database-backup-schedule"
CLOUD_ACK_KEY_ID = "cloud-backup-activation-ack-hmac-2026-01"
STATE_KEY_ID = "ops-backup-activation-state-hmac-2026-01"
OFFER_CONTRACT = "openadapt-cloud-managed-browser-v1"
CIPHERTEXT_STORAGE_CLASS = "GLACIER_IR"
MANIFEST_STORAGE_CLASS = "STANDARD"
MAXIMUM_REQUEST_VALIDITY = timedelta(minutes=15)
RECEIPT_VALIDITY = timedelta(days=90)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHECKSUM_SHA256 = re.compile(r"^[A-Za-z0-9+/]{43}=$")
ACTIVATION_ID = re.compile(r"^act_[0-9a-f]{32,64}$")
STAMP = re.compile(r"^\d{8}T\d{6}Z$")
VERSION_ID = re.compile(r"^[^\s/]{1,1024}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
WORKFLOW_RUN_ID = re.compile(r"^[1-9][0-9]*$")
BUCKET = "openadapt-production-db-backups-992382684924"
AWS_ACCOUNT_ID = "992382684924"
AWS_REGION = "us-east-1"


class ActivationError(ValueError):
    """The activation input cannot authorize a backup or customer activation."""


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_value(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode()).hexdigest()


def read_object(path: str | Path, name: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ActivationError(f"the {name} is not an object")
    return value


def read_canonical_object(path: str | Path, name: str) -> dict[str, object]:
    raw = Path(path).read_bytes()
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ActivationError(f"the {name} is not canonical UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ActivationError(f"the {name} is not an object")
    if raw != (stable_json(value) + "\n").encode():
        raise ActivationError(f"the {name} bytes are not canonical JSON plus one LF")
    return value


def write_object(path: str | Path, value: object) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise ActivationError(f"{name} is missing")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ActivationError(f"{name} is not an ISO-8601 time") from error
    if result.tzinfo is None:
        raise ActivationError(f"{name} has no timezone")
    return result.astimezone(timezone.utc)


def iso_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def secret(name: str) -> bytes:
    value = os.environ.get(name, "").encode()
    if len(value) < 32:
        raise ActivationError(f"the {name} signing key is missing or too short")
    return value


def signature(value: object, key: bytes) -> str:
    return hmac.new(key, stable_json(value).encode(), hashlib.sha256).hexdigest()


def require_exact_keys(value: dict[str, object], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise ActivationError(f"the {name} fields are not exact")


def require_sha256(value: object, name: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise ActivationError(f"{name} is not a SHA-256 digest")
    return value


def require_checksum_sha256(value: object, name: str) -> str:
    if not isinstance(value, str) or CHECKSUM_SHA256.fullmatch(value) is None:
        raise ActivationError(f"{name} is not a base64 SHA-256 checksum")
    try:
        decoded = base64.b64decode(value, validate=True)
    except ValueError as error:
        raise ActivationError(f"{name} is not a base64 SHA-256 checksum") from error
    if len(decoded) != hashlib.sha256().digest_size:
        raise ActivationError(f"{name} is not a base64 SHA-256 checksum")
    return value


def require_version_id(value: object, name: str) -> str:
    if not isinstance(value, str) or VERSION_ID.fullmatch(value) is None:
        raise ActivationError(f"{name} is invalid")
    return value


def validate_request(
    envelope: dict[str, object],
    *,
    key: bytes,
    now: datetime,
    permit_expired_retry: bool = False,
) -> tuple[dict[str, object], str]:
    require_exact_keys(envelope, {"schema", "request", "signature"}, "request envelope")
    if envelope.get("schema") != REQUEST_SCHEMA:
        raise ActivationError("the activation request schema is not supported")
    request = envelope.get("request")
    signed = envelope.get("signature")
    if not isinstance(request, dict) or not isinstance(signed, dict):
        raise ActivationError("the activation request envelope is incomplete")
    require_exact_keys(signed, {"algorithm", "key_id", "value"}, "request signature")
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the activation request signature algorithm is invalid")
    if signed.get("key_id") != PAYMENT_SIGNAL_KEY_ID:
        raise ActivationError("the activation request signature key is invalid")
    actual_signature = signed.get("value")
    if not isinstance(actual_signature, str) or not hmac.compare_digest(
        actual_signature, signature(request, key)
    ):
        raise ActivationError("the activation request signature is invalid")

    require_exact_keys(
        request,
        {
            "activation_id",
            "amount_total_minor",
            "audience",
            "currency",
            "expires_at",
            "first_verified_payment",
            "issued_at",
            "issuer",
            "offer_contract",
            "organization_id_sha256",
            "payment_event_id_sha256",
            "payment_status",
            "recovery_point_stamp",
            "verified_payment_at",
        },
        "activation request",
    )
    activation_id = request.get("activation_id")
    if (
        not isinstance(activation_id, str)
        or ACTIVATION_ID.fullmatch(activation_id) is None
    ):
        raise ActivationError("the activation ID is invalid")
    require_sha256(request.get("organization_id_sha256"), "organization ID")
    require_sha256(request.get("payment_event_id_sha256"), "payment event ID")
    recovery_point_stamp = request.get("recovery_point_stamp")
    if (
        not isinstance(recovery_point_stamp, str)
        or STAMP.fullmatch(recovery_point_stamp) is None
    ):
        raise ActivationError("the activation recovery point stamp is invalid")
    if request.get("offer_contract") != OFFER_CONTRACT:
        raise ActivationError("the payment does not bind the managed-browser offer")
    if request.get("issuer") != PAYMENT_SIGNAL_ISSUER:
        raise ActivationError("the activation request issuer is invalid")
    if request.get("audience") != PAYMENT_SIGNAL_AUDIENCE:
        raise ActivationError("the activation request audience is invalid")
    if request.get("first_verified_payment") is not True:
        raise ActivationError("the payment is not the first verified payment")
    if request.get("payment_status") != "paid":
        raise ActivationError("the payment status is not paid")
    amount = request.get("amount_total_minor")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount != 50_000:
        raise ActivationError("the payment amount does not match the offer")
    if request.get("currency") != "usd":
        raise ActivationError("the payment currency does not match the offer")

    paid = parse_time(request.get("verified_payment_at"), "verified payment time")
    issued = parse_time(request.get("issued_at"), "request issue time")
    expires = parse_time(request.get("expires_at"), "request expiry time")
    if paid > issued or issued > expires:
        raise ActivationError("the activation request times are out of order")
    if expires - issued > MAXIMUM_REQUEST_VALIDITY:
        raise ActivationError("the activation request validity is too long")
    current = now.astimezone(timezone.utc)
    if issued > current + timedelta(minutes=5):
        raise ActivationError("the activation request was issued in the future")
    if not permit_expired_retry and current > expires:
        raise ActivationError("the activation request has expired")
    return request, sha256_value(request)


def read_state(value: dict[str, object]) -> dict[str, object]:
    require_exact_keys(value, {"schema", "state", "state_sha256"}, "activation state")
    if value.get("schema") != STATE_SCHEMA:
        raise ActivationError("the activation state schema is not supported")
    state = value.get("state")
    if not isinstance(state, dict) or value.get("state_sha256") != sha256_value(state):
        raise ActivationError("the activation state digest is invalid")
    require_exact_keys(
        state,
        {
            "activation_id",
            "attempt_count",
            "backup",
            "created_at",
            "last_attempt_at",
            "offer_contract",
            "organization_id_sha256",
            "payment_event_id_sha256",
            "readiness_receipt_sha256",
            "recovery_point_stamp",
            "request_sha256",
            "restore",
            "stage",
        },
        "activation state payload",
    )
    if state.get("stage") not in {
        "PENDING_BACKUP",
        "BACKUP_VERIFIED",
        "RESTORE_VERIFIED",
        "READY",
    }:
        raise ActivationError("the activation state stage is invalid")
    return state


def state_envelope(state: dict[str, object]) -> dict[str, object]:
    return {
        "schema": STATE_SCHEMA,
        "state": state,
        "state_sha256": sha256_value(state),
    }


def sign_state(envelope: dict[str, object], *, key: bytes) -> dict[str, object]:
    read_state(envelope)
    return {
        "schema": SIGNED_STATE_SCHEMA,
        "state_envelope": envelope,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": STATE_KEY_ID,
            "value": signature(envelope, key),
        },
    }


def validate_signed_state(
    envelope: dict[str, object], *, key: bytes
) -> dict[str, object]:
    require_exact_keys(
        envelope,
        {"schema", "state_envelope", "signature"},
        "signed activation state",
    )
    if envelope.get("schema") != SIGNED_STATE_SCHEMA:
        raise ActivationError("the signed activation state schema is invalid")
    state = envelope.get("state_envelope")
    signed = envelope.get("signature")
    if not isinstance(state, dict) or not isinstance(signed, dict):
        raise ActivationError("the signed activation state is incomplete")
    require_exact_keys(
        signed, {"algorithm", "key_id", "value"}, "activation state signature"
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the activation state signature algorithm is invalid")
    if signed.get("key_id") != STATE_KEY_ID:
        raise ActivationError("the activation state signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(state, key)
    ):
        raise ActivationError("the activation state signature is invalid")
    read_state(state)
    return state


STAGE_ORDER = {
    "PENDING_BACKUP": 0,
    "BACKUP_VERIFIED": 1,
    "RESTORE_VERIFIED": 2,
    "READY": 3,
}


def resume(
    request_envelope: dict[str, object],
    *,
    request_key: bytes,
    state_key: bytes,
    now: datetime,
    signed_states: list[dict[str, object]],
) -> dict[str, object]:
    """Return the highest exact signed stage for one idempotent activation."""
    if not signed_states:
        return begin(request_envelope, key=request_key, now=now)
    by_stage: dict[str, dict[str, object]] = {}
    for signed_state in signed_states:
        state_envelope_value = validate_signed_state(signed_state, key=state_key)
        begin(
            request_envelope,
            key=request_key,
            now=now,
            existing=state_envelope_value,
        )
        state = read_state(state_envelope_value)
        stage = state["stage"]
        assert isinstance(stage, str)
        retained = by_stage.get(stage)
        if retained is not None and retained != state_envelope_value:
            raise ActivationError(
                f"the durable activation has conflicting {stage} states"
            )
        by_stage[stage] = state_envelope_value
    return max(
        by_stage.values(),
        key=lambda value: STAGE_ORDER[str(read_state(value)["stage"])],
    )


def required_actions(state_envelope_value: dict[str, object]) -> dict[str, bool]:
    """Describe only the incomplete side effects for a retained stage."""
    stage = read_state(state_envelope_value)["stage"]
    rank = STAGE_ORDER[str(stage)]
    return {
        "backup": rank < STAGE_ORDER["BACKUP_VERIFIED"],
        "restore": rank < STAGE_ORDER["RESTORE_VERIFIED"],
        "receipt": rank < STAGE_ORDER["READY"],
    }


def begin(
    envelope: dict[str, object],
    *,
    key: bytes,
    now: datetime,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    request, request_sha = validate_request(
        envelope,
        key=key,
        now=now,
        permit_expired_retry=existing is not None,
    )
    current = iso_time(parse_time(request.get("issued_at"), "request issue time"))
    if existing is None:
        state = {
            "activation_id": request["activation_id"],
            "attempt_count": 1,
            "backup": None,
            "created_at": current,
            "last_attempt_at": current,
            "offer_contract": request["offer_contract"],
            "organization_id_sha256": request["organization_id_sha256"],
            "payment_event_id_sha256": request["payment_event_id_sha256"],
            "readiness_receipt_sha256": None,
            "recovery_point_stamp": request["recovery_point_stamp"],
            "request_sha256": request_sha,
            "restore": None,
            "stage": "PENDING_BACKUP",
        }
        return state_envelope(state)

    state = read_state(existing).copy()
    exact = {
        "activation_id": request["activation_id"],
        "offer_contract": request["offer_contract"],
        "organization_id_sha256": request["organization_id_sha256"],
        "payment_event_id_sha256": request["payment_event_id_sha256"],
        "request_sha256": request_sha,
        "recovery_point_stamp": request["recovery_point_stamp"],
    }
    if any(state.get(name) != value for name, value in exact.items()):
        raise ActivationError("the activation retry conflicts with retained state")
    created = parse_time(state.get("created_at"), "activation state creation time")
    issued = parse_time(request.get("issued_at"), "request issue time")
    expires = parse_time(request.get("expires_at"), "request expiry time")
    if created < issued or created > expires:
        raise ActivationError("the retained activation state was not created in time")
    return existing


def verify_claimed_request(
    envelope: dict[str, object],
    *,
    key: bytes,
    now: datetime,
    authority_claim_sha256: str,
) -> dict[str, str]:
    """Verify a claimed request before loading its retained activation state."""
    require_sha256(authority_claim_sha256, "dispatch authority claim")
    request, request_sha = validate_request(
        envelope,
        key=key,
        now=now,
        permit_expired_retry=True,
    )
    activation_id = request["activation_id"]
    recovery_point_stamp = request["recovery_point_stamp"]
    assert isinstance(activation_id, str)
    assert isinstance(recovery_point_stamp, str)
    return {
        "activation_id": activation_id,
        "recovery_point_stamp": recovery_point_stamp,
        "request_sha256": request_sha,
    }


def validate_backup_evidence(
    backup: dict[str, object], *, expected_recovery_stamp: object | None = None
) -> dict[str, object]:
    require_exact_keys(
        backup,
        {
            "artifact_sha256",
            "aws_account_id",
            "aws_region",
            "backup_contract_sha256",
            "bucket_name",
            "ciphertext_bytes",
            "ciphertext_checksum_sha256",
            "ciphertext_gib",
            "ciphertext_key",
            "ciphertext_sha256",
            "ciphertext_storage_class",
            "ciphertext_version_id",
            "manifest_checksum_sha256",
            "manifest_key",
            "manifest_sha256",
            "manifest_storage_class",
            "manifest_version_id",
            "recovery_point_stamp",
            "repository_commit",
            "workflow_run_id",
        },
        "backup evidence",
    )
    for name in (
        "artifact_sha256",
        "backup_contract_sha256",
        "ciphertext_sha256",
        "manifest_sha256",
    ):
        require_sha256(backup.get(name), name.replace("_", " "))
    require_checksum_sha256(
        backup.get("ciphertext_checksum_sha256"), "ciphertext checksum"
    )
    require_checksum_sha256(backup.get("manifest_checksum_sha256"), "manifest checksum")
    if backup.get("aws_account_id") != AWS_ACCOUNT_ID:
        raise ActivationError("the backup AWS account is invalid")
    if backup.get("aws_region") != AWS_REGION:
        raise ActivationError("the backup AWS region is invalid")
    if backup.get("bucket_name") != BUCKET:
        raise ActivationError("the backup bucket is invalid")
    if backup.get("ciphertext_storage_class") != CIPHERTEXT_STORAGE_CLASS:
        raise ActivationError("the backup ciphertext is not in GLACIER_IR")
    if backup.get("manifest_storage_class") != MANIFEST_STORAGE_CLASS:
        raise ActivationError("the backup manifest is not in STANDARD")
    stamp = backup.get("recovery_point_stamp")
    if not isinstance(stamp, str) or STAMP.fullmatch(stamp) is None:
        raise ActivationError("the backup recovery point stamp is invalid")
    if expected_recovery_stamp is not None and stamp != expected_recovery_stamp:
        raise ActivationError("the backup recovery point stamp changed")
    expected_prefix = f"daily/{stamp}"
    if backup.get("ciphertext_key") != (
        f"{expected_prefix}/db-backup-{stamp}.tar.gz.age"
    ):
        raise ActivationError("the backup ciphertext key is invalid")
    if backup.get("manifest_key") != f"{expected_prefix}/artifact-manifest.json":
        raise ActivationError("the backup manifest key is invalid")
    require_version_id(backup.get("ciphertext_version_id"), "ciphertext version ID")
    require_version_id(backup.get("manifest_version_id"), "manifest version ID")
    commit = backup.get("repository_commit")
    if not isinstance(commit, str) or COMMIT.fullmatch(commit) is None:
        raise ActivationError("the backup repository commit is invalid")
    run_id = backup.get("workflow_run_id")
    if not isinstance(run_id, str) or WORKFLOW_RUN_ID.fullmatch(run_id) is None:
        raise ActivationError("the backup workflow run ID is invalid")
    size = backup.get("ciphertext_bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ActivationError("the backup ciphertext size is invalid")
    gib = backup.get("ciphertext_gib")
    if not isinstance(gib, str) or gib != f"{size / (1024**3):.9f}":
        raise ActivationError("the backup GiB measurement is invalid")
    return backup


def record_backup(
    existing: dict[str, object], backup: dict[str, object]
) -> dict[str, object]:
    state = read_state(existing).copy()
    validate_backup_evidence(
        backup, expected_recovery_stamp=state.get("recovery_point_stamp")
    )

    retained = state.get("backup")
    if state["stage"] != "PENDING_BACKUP":
        if retained == backup:
            return existing
        raise ActivationError("the activation state already binds a different backup")
    state["backup"] = backup
    state["stage"] = "BACKUP_VERIFIED"
    return state_envelope(state)


def record_restore(
    existing: dict[str, object], evidence: dict[str, object]
) -> dict[str, object]:
    state = read_state(existing).copy()
    if state.get("stage") not in {"BACKUP_VERIFIED", "RESTORE_VERIFIED"}:
        raise ActivationError("a verified first backup must precede the restore gate")
    backup = state.get("backup")
    if not isinstance(backup, dict):
        raise ActivationError("the activation state has no first backup evidence")
    restore = validate_restore_evidence(backup, evidence)
    if state.get("stage") == "RESTORE_VERIFIED":
        if state.get("restore") == restore:
            return existing
        raise ActivationError("the activation state already binds a different restore")
    state["restore"] = restore
    state["stage"] = "RESTORE_VERIFIED"
    return state_envelope(state)


def validate_restore_evidence(
    backup: dict[str, object], evidence: dict[str, object]
) -> dict[str, object]:
    require_exact_keys(
        evidence,
        {
            "artifact_sha256",
            "aws_account_id",
            "aws_region",
            "backup_contract_sha256",
            "bucket_name",
            "ciphertext_key",
            "ciphertext_version_id",
            "completed_at",
            "database_restored",
            "manifest_key",
            "manifest_version_id",
            "rpo_seconds_at_start",
            "rto_seconds",
            "schema",
            "started_at",
            "storage_restored",
        },
        "restore evidence",
    )
    if evidence.get("schema") != RESTORE_SCHEMA:
        raise ActivationError("the restore evidence schema is not supported")
    if evidence.get("database_restored") is not True:
        raise ActivationError("the database restore gate did not pass")
    if evidence.get("storage_restored") is not False:
        raise ActivationError("the database-only restore scope is invalid")
    if evidence.get("artifact_sha256") != backup.get("artifact_sha256"):
        raise ActivationError("the restore evidence does not bind the first backup")
    if evidence.get("backup_contract_sha256") != backup.get("backup_contract_sha256"):
        raise ActivationError("the restore evidence does not bind the backup contract")
    for name in (
        "aws_account_id",
        "aws_region",
        "bucket_name",
        "ciphertext_key",
        "ciphertext_version_id",
        "manifest_key",
        "manifest_version_id",
    ):
        if evidence.get(name) != backup.get(name):
            raise ActivationError(
                f"the restore evidence does not bind the first backup {name.replace('_', ' ')}"
            )
    started = parse_time(evidence.get("started_at"), "restore start time")
    completed = parse_time(evidence.get("completed_at"), "restore completion time")
    if completed < started:
        raise ActivationError("the restore evidence times are out of order")
    restore = {
        "completed_at": iso_time(completed),
        "database_restored": True,
        "evidence_sha256": sha256_value(evidence),
        "rpo_seconds_at_start": evidence.get("rpo_seconds_at_start"),
        "rto_seconds": evidence.get("rto_seconds"),
        "storage_restored": False,
    }
    for name in ("rpo_seconds_at_start", "rto_seconds"):
        value = restore[name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ActivationError(f"the restore {name.replace('_', ' ')} is invalid")
    return restore


def issue_receipt(
    existing: dict[str, object], *, key: bytes
) -> tuple[dict[str, object], dict[str, object]]:
    state = read_state(existing).copy()
    if state.get("stage") not in {"RESTORE_VERIFIED", "READY"}:
        raise ActivationError("the restore gate must pass before readiness")
    backup = state.get("backup")
    restore = state.get("restore")
    if not isinstance(backup, dict) or not isinstance(restore, dict):
        raise ActivationError("the readiness evidence is incomplete")
    issued = parse_time(restore.get("completed_at"), "receipt issue time")
    receipt = {
        "activation_id": state["activation_id"],
        "audience": READINESS_AUDIENCE,
        "backup": backup,
        "expires_at": iso_time(issued + RECEIPT_VALIDITY),
        "issued_at": iso_time(issued),
        "issuer": READINESS_ISSUER,
        "offer_contract": state["offer_contract"],
        "organization_id_sha256": state["organization_id_sha256"],
        "payment_event_id_sha256": state["payment_event_id_sha256"],
        "readiness_state": "DATABASE_RECOVERY_READY",
        "recovery_scope": "database_only",
        "request_sha256": state["request_sha256"],
        "restore": restore,
    }
    receipt_sha = sha256_value(receipt)
    envelope = {
        "schema": RECEIPT_SCHEMA,
        "receipt": receipt,
        "receipt_sha256": receipt_sha,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": READINESS_KEY_ID,
            "value": signature(receipt, key),
        },
    }
    retained = state.get("readiness_receipt_sha256")
    if retained not in {None, receipt_sha}:
        raise ActivationError(
            "the activation state binds a different readiness receipt"
        )
    state["readiness_receipt_sha256"] = receipt_sha
    state["stage"] = "READY"
    return state_envelope(state), envelope


def validate_receipt(
    envelope: dict[str, object], *, key: bytes, now: datetime
) -> dict[str, object]:
    require_exact_keys(
        envelope,
        {"schema", "receipt", "receipt_sha256", "signature"},
        "readiness receipt envelope",
    )
    if envelope.get("schema") != RECEIPT_SCHEMA:
        raise ActivationError("the readiness receipt schema is not supported")
    receipt = envelope.get("receipt")
    signed = envelope.get("signature")
    if not isinstance(receipt, dict) or not isinstance(signed, dict):
        raise ActivationError("the readiness receipt is incomplete")
    if envelope.get("receipt_sha256") != sha256_value(receipt):
        raise ActivationError("the readiness receipt digest is invalid")
    require_exact_keys(signed, {"algorithm", "key_id", "value"}, "receipt signature")
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the readiness receipt signature algorithm is invalid")
    if signed.get("key_id") != READINESS_KEY_ID:
        raise ActivationError("the readiness receipt signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(receipt, key)
    ):
        raise ActivationError("the readiness receipt signature is invalid")
    if receipt.get("recovery_scope") != "database_only":
        raise ActivationError("the readiness receipt scope is invalid")
    if receipt.get("readiness_state") != "DATABASE_RECOVERY_READY":
        raise ActivationError("the readiness receipt state is invalid")
    if receipt.get("offer_contract") != OFFER_CONTRACT:
        raise ActivationError("the readiness receipt offer is invalid")
    if receipt.get("issuer") != READINESS_ISSUER:
        raise ActivationError("the readiness receipt issuer is invalid")
    if receipt.get("audience") != READINESS_AUDIENCE:
        raise ActivationError("the readiness receipt audience is invalid")
    backup = receipt.get("backup")
    restore = receipt.get("restore")
    if not isinstance(backup, dict) or not isinstance(restore, dict):
        raise ActivationError("the readiness receipt evidence is incomplete")
    if backup.get("ciphertext_storage_class") != CIPHERTEXT_STORAGE_CLASS:
        raise ActivationError("the readiness receipt ciphertext class is invalid")
    if backup.get("manifest_storage_class") != MANIFEST_STORAGE_CLASS:
        raise ActivationError("the readiness receipt manifest class is invalid")
    if restore.get("database_restored") is not True:
        raise ActivationError("the readiness receipt has no passed restore")
    if restore.get("storage_restored") is not False:
        raise ActivationError("the readiness receipt restore scope is invalid")
    issued = parse_time(receipt.get("issued_at"), "receipt issue time")
    expires = parse_time(receipt.get("expires_at"), "receipt expiry time")
    if expires - issued != RECEIPT_VALIDITY:
        raise ActivationError("the readiness receipt validity is invalid")
    current = now.astimezone(timezone.utc)
    if current < issued - timedelta(minutes=5) or current > expires:
        raise ActivationError("the readiness receipt is not active")
    return receipt


def validate_cloud_readiness_ack(
    envelope: dict[str, object],
    receipt_envelope: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    now: datetime,
) -> dict[str, object]:
    """Validate the exact non-authorizing PENDING_SCHEDULE acknowledgment."""
    receipt = validate_receipt(receipt_envelope, key=receipt_key, now=now)
    require_exact_keys(
        envelope,
        {"schema", "ack", "ack_sha256", "signature"},
        "Cloud readiness acknowledgment envelope",
    )
    if envelope.get("schema") != CLOUD_ACK_SCHEMA:
        raise ActivationError("the Cloud readiness acknowledgment schema is invalid")
    ack = envelope.get("ack")
    signed = envelope.get("signature")
    if not isinstance(ack, dict) or not isinstance(signed, dict):
        raise ActivationError("the Cloud readiness acknowledgment is incomplete")
    if envelope.get("ack_sha256") != sha256_value(ack):
        raise ActivationError("the Cloud readiness acknowledgment digest is invalid")
    require_exact_keys(
        signed,
        {"algorithm", "key_id", "value"},
        "Cloud readiness acknowledgment signature",
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the Cloud acknowledgment signature algorithm is invalid")
    if signed.get("key_id") != CLOUD_ACK_KEY_ID:
        raise ActivationError("the Cloud acknowledgment signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(ack, cloud_ack_key)
    ):
        raise ActivationError("the Cloud readiness acknowledgment signature is invalid")
    require_exact_keys(
        ack,
        {
            "activation_id",
            "applied_at",
            "audience",
            "cloud_revision_sha256",
            "idempotency_key",
            "issuer",
            "new_state",
            "organization_id_sha256",
            "prior_state",
            "readiness_receipt_sha256",
        },
        "Cloud readiness acknowledgment",
    )
    exact = {
        "activation_id": receipt.get("activation_id"),
        "audience": CLOUD_ACK_AUDIENCE,
        "idempotency_key": receipt.get("activation_id"),
        "issuer": CLOUD_ACK_ISSUER,
        "new_state": "PENDING_SCHEDULE",
        "organization_id_sha256": receipt.get("organization_id_sha256"),
        "prior_state": "PENDING_RECOVERY",
        "readiness_receipt_sha256": receipt_envelope.get("receipt_sha256"),
    }
    if any(ack.get(name) != value for name, value in exact.items()):
        raise ActivationError("the Cloud readiness acknowledgment state is invalid")
    require_sha256(ack.get("cloud_revision_sha256"), "Cloud revision")
    applied = parse_time(ack.get("applied_at"), "Cloud readiness time")
    if applied < parse_time(receipt.get("issued_at"), "receipt issue time"):
        raise ActivationError("the Cloud readiness transition precedes recovery proof")
    if applied > now.astimezone(timezone.utc) + timedelta(minutes=5):
        raise ActivationError("the Cloud readiness time is in the future")
    return ack


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    begin_command = commands.add_parser("begin")
    begin_command.add_argument("--request", required=True)
    begin_command.add_argument("--existing-state")
    begin_command.add_argument("--hmac-key-env", required=True)
    begin_command.add_argument("--now")
    begin_command.add_argument("--output", required=True)

    verify_request_command = commands.add_parser("verify-claimed-request")
    verify_request_command.add_argument("--request", required=True)
    verify_request_command.add_argument("--authority-claim-sha256", required=True)
    verify_request_command.add_argument("--hmac-key-env", required=True)
    verify_request_command.add_argument("--now")
    verify_request_command.add_argument("--output", required=True)

    backup_command = commands.add_parser("record-backup")
    backup_command.add_argument("--state", required=True)
    backup_command.add_argument("--evidence", required=True)
    backup_command.add_argument("--output", required=True)

    restore_command = commands.add_parser("record-restore")
    restore_command.add_argument("--state", required=True)
    restore_command.add_argument("--evidence", required=True)
    restore_command.add_argument("--output", required=True)

    receipt_command = commands.add_parser("issue-receipt")
    receipt_command.add_argument("--state", required=True)
    receipt_command.add_argument("--hmac-key-env", required=True)
    receipt_command.add_argument("--state-output", required=True)
    receipt_command.add_argument("--receipt-output", required=True)

    verify_command = commands.add_parser("verify-receipt")
    verify_command.add_argument("--receipt", required=True)
    verify_command.add_argument("--hmac-key-env", required=True)
    verify_command.add_argument("--now")

    verify_ack_command = commands.add_parser("verify-readiness-ack")
    verify_ack_command.add_argument("--receipt", required=True)
    verify_ack_command.add_argument("--ack", required=True)
    verify_ack_command.add_argument("--receipt-hmac-key-env", required=True)
    verify_ack_command.add_argument("--cloud-ack-hmac-key-env", required=True)
    verify_ack_command.add_argument("--now")

    sign_state_command = commands.add_parser("sign-state")
    sign_state_command.add_argument("--state", required=True)
    sign_state_command.add_argument("--hmac-key-env", required=True)
    sign_state_command.add_argument("--output", required=True)

    verify_state_command = commands.add_parser("verify-state")
    verify_state_command.add_argument("--signed-state", required=True)
    verify_state_command.add_argument("--hmac-key-env", required=True)
    verify_state_command.add_argument("--output", required=True)

    resume_command = commands.add_parser("resume")
    resume_command.add_argument("--request", required=True)
    resume_command.add_argument("--signed-state", action="append", default=[])
    resume_command.add_argument("--request-hmac-key-env", required=True)
    resume_command.add_argument("--state-hmac-key-env", required=True)
    resume_command.add_argument("--now")
    resume_command.add_argument("--output", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "begin":
            existing = (
                read_object(args.existing_state, "existing activation state")
                if args.existing_state
                else None
            )
            now = (
                parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
            )
            result = begin(
                read_object(args.request, "activation request"),
                key=secret(args.hmac_key_env),
                now=now,
                existing=existing,
            )
            write_object(args.output, result)
        elif args.command == "verify-claimed-request":
            now = (
                parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
            )
            result = verify_claimed_request(
                read_object(args.request, "activation request"),
                key=secret(args.hmac_key_env),
                now=now,
                authority_claim_sha256=args.authority_claim_sha256,
            )
            write_object(args.output, result)
        elif args.command == "record-backup":
            result = record_backup(
                read_object(args.state, "activation state"),
                read_object(args.evidence, "first backup evidence"),
            )
            write_object(args.output, result)
        elif args.command == "record-restore":
            result = record_restore(
                read_object(args.state, "activation state"),
                read_object(args.evidence, "restore evidence"),
            )
            write_object(args.output, result)
        elif args.command == "issue-receipt":
            state, receipt = issue_receipt(
                read_object(args.state, "activation state"),
                key=secret(args.hmac_key_env),
            )
            write_object(args.state_output, state)
            write_object(args.receipt_output, receipt)
            result = {
                "activation_id": state["state"]["activation_id"],
                "receipt_sha256": receipt["receipt_sha256"],
                "stage": "READY",
            }
        elif args.command == "verify-receipt":
            result = validate_receipt(
                read_object(args.receipt, "readiness receipt"),
                key=secret(args.hmac_key_env),
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
            )
        elif args.command == "verify-readiness-ack":
            result = validate_cloud_readiness_ack(
                read_canonical_object(args.ack, "Cloud readiness acknowledgment"),
                read_canonical_object(args.receipt, "readiness receipt"),
                receipt_key=secret(args.receipt_hmac_key_env),
                cloud_ack_key=secret(args.cloud_ack_hmac_key_env),
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
            )
        elif args.command == "sign-state":
            result = sign_state(
                read_object(args.state, "activation state"),
                key=secret(args.hmac_key_env),
            )
            write_object(args.output, result)
        elif args.command == "verify-state":
            result = validate_signed_state(
                read_object(args.signed_state, "signed activation state"),
                key=secret(args.hmac_key_env),
            )
            write_object(args.output, result)
        else:
            now = (
                parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
            )
            result = resume(
                read_object(args.request, "activation request"),
                request_key=secret(args.request_hmac_key_env),
                state_key=secret(args.state_hmac_key_env),
                now=now,
                signed_states=[
                    read_object(path, "signed activation state")
                    for path in args.signed_state
                ],
            )
            write_object(args.output, result)
        print(json.dumps(result, sort_keys=True))
    except (ActivationError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
