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
ADMISSION_SCHEMA = "openadapt.database-backup-schedule-lease/v1"
CONTINUATION_SCHEMA = "openadapt.database-backup-continuation-assertion/v1"
CONTINUATION_ACCEPTANCE_SCHEMA = (
    "openadapt.database-backup-continuation-acceptance/v1"
)
RENEWAL_RECEIPT_SCHEMA = (
    "openadapt.database-backup-renewal-readiness-receipt/v1"
)
CLOUD_LEASE_ACK_SCHEMA = "openadapt.cloud-backup-schedule-lease-ack/v1"
DEACTIVATION_REQUEST_SCHEMA = "openadapt.database-backup-deactivation-request/v1"
DEACTIVATION_AUTHORIZATION_SCHEMA = (
    "openadapt.database-backup-deactivation-authorization/v1"
)
ZERO_CUSTOMER_PROOF_SCHEMA = "openadapt.zero-customer-backup-shutdown-proof/v1"
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
OPS_LEASE_ISSUER = "openadapt-ops"
OPS_LEASE_AUDIENCE = "openadapt-cloud:database-backup-schedule-lease"
OPS_LEASE_KEY_ID = "ops-backup-schedule-lease-hmac-2026-01"
CLOUD_CONTINUATION_ISSUER = "openadapt-cloud"
CLOUD_CONTINUATION_AUDIENCE = "OpenAdaptAI/openadapt-ops:database-backup-renewal"
CLOUD_CONTINUATION_KEY_ID = "cloud-backup-continuation-hmac-2026-01"
RENEWAL_READINESS_ISSUER = "openadapt-ops"
RENEWAL_READINESS_AUDIENCE = "openadapt-cloud:database-backup-renewal-readiness"
RENEWAL_READINESS_KEY_ID = "ops-backup-renewal-readiness-hmac-2026-01"
CLOUD_LEASE_ACK_ISSUER = "openadapt-cloud"
CLOUD_LEASE_ACK_AUDIENCE = "OpenAdaptAI/openadapt-ops:database-backup-lease-ack"
CLOUD_LEASE_ACK_KEY_ID = "cloud-backup-schedule-lease-ack-hmac-2026-01"
STATE_KEY_ID = "ops-backup-activation-state-hmac-2026-01"
CLOUD_DEACTIVATION_ISSUER = "openadapt-cloud"
CLOUD_DEACTIVATION_AUDIENCE = "OpenAdaptAI/openadapt-ops:database-backup-deactivation"
CLOUD_DEACTIVATION_KEY_ID = "cloud-backup-deactivation-hmac-2026-01"
OPS_DEACTIVATION_KEY_ID = "ops-backup-deactivation-authorization-hmac-2026-01"
OFFER_CONTRACT = "openadapt-cloud-managed-browser-v1"
CIPHERTEXT_STORAGE_CLASS = "GLACIER_IR"
MANIFEST_STORAGE_CLASS = "STANDARD"
MAXIMUM_REQUEST_VALIDITY = timedelta(minutes=15)
RECEIPT_VALIDITY = timedelta(days=90)
LEASE_VALIDITY = timedelta(days=90)
LEASE_RENEWAL_INTERVAL = timedelta(days=60)
CONTINUATION_VALIDITY = timedelta(minutes=15)
CONTINUATION_POLICY = "continue_until_signed_zero_customer_deactivation"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHECKSUM_SHA256 = re.compile(r"^[A-Za-z0-9+/]{43}=$")
ACTIVATION_ID = re.compile(r"^act_[0-9a-f]{32,64}$")
DEACTIVATION_ID = re.compile(r"^deact_[0-9a-f]{32,64}$")
LEASE_EVENT_ID = re.compile(r"^lease_[0-9a-f]{64}$")
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
            "cloud_lease_ack_sha256",
            "request_sha256",
            "restore",
            "schedule_lease_sha256",
            "stage",
        },
        "activation state payload",
    )
    if state.get("stage") not in {
        "PENDING_BACKUP",
        "BACKUP_VERIFIED",
        "RESTORE_VERIFIED",
        "READY",
        "ACTIVE",
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
    "ACTIVE": 4,
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
        "callback": rank < STAGE_ORDER["ACTIVE"],
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
            "cloud_lease_ack_sha256": None,
            "request_sha256": request_sha,
            "restore": None,
            "schedule_lease_sha256": None,
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


def create_admission(
    receipt_envelope: dict[str, object],
    ack_envelope: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    lease_key: bytes,
    now: datetime,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    ack_payload = ack_envelope.get("ack")
    if not isinstance(ack_payload, dict):
        raise ActivationError("the schedule admission acknowledgment is incomplete")
    applied = parse_time(ack_payload.get("applied_at"), "Cloud activation time")
    receipt = validate_receipt(receipt_envelope, key=receipt_key, now=applied)
    validate_cloud_ack_signature(
        ack_envelope,
        key=cloud_ack_key,
        receipt_envelope=receipt_envelope,
        receipt=receipt,
        now=now,
    )
    if applied > parse_time(receipt.get("expires_at"), "receipt expiry time"):
        raise ActivationError("Cloud accepted an expired readiness receipt")
    issued = applied
    activation_id = str(receipt["activation_id"])
    payload: dict[str, object] = {
        "activation_id": receipt["activation_id"],
        "audience": OPS_LEASE_AUDIENCE,
        "cloud_readiness_ack": ack_envelope,
        "continuation_assertion": None,
        "continuation_policy": CONTINUATION_POLICY,
        "expires_at": iso_time(issued + LEASE_VALIDITY),
        "issued_at": iso_time(issued),
        "issuer": OPS_LEASE_ISSUER,
        "lease_event_id": initial_lease_event_id(activation_id),
        "lease_sequence": 0,
        "offer_contract": receipt["offer_contract"],
        "organization_id_sha256": receipt["organization_id_sha256"],
        "prior_lease_sha256": None,
        "readiness_receipt": receipt_envelope,
        "renewal_due_at": iso_time(issued + LEASE_RENEWAL_INTERVAL),
        "requested_cadence_seconds": 43_200,
    }
    result = signed_lease(payload, key=lease_key)
    if existing is not None and existing != result:
        raise ActivationError("the initial lease conflicts with retained state")
    return existing if existing is not None else result


def initial_lease_event_id(activation_id: str) -> str:
    digest = hashlib.sha256(f"initial:{activation_id}".encode()).hexdigest()
    return f"lease_{digest}"


def renewal_lease_event_id(
    activation_id: str, prior_lease_sha256: str, sequence: int
) -> str:
    identity = {
        "activation_id": activation_id,
        "active_lease_sha256": prior_lease_sha256,
        "lease_sequence": sequence,
    }
    digest = hashlib.sha256(stable_json(identity).encode()).hexdigest()
    return f"lease_{digest}"


def signed_lease(payload: dict[str, object], *, key: bytes) -> dict[str, object]:
    return {
        "schema": ADMISSION_SCHEMA,
        "lease": payload,
        "lease_sha256": sha256_value(payload),
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": OPS_LEASE_KEY_ID,
            "value": signature(payload, key),
        },
    }


def validate_cloud_ack_signature(
    envelope: dict[str, object],
    *,
    key: bytes,
    receipt_envelope: dict[str, object] | None,
    receipt: dict[str, object],
    now: datetime,
) -> dict[str, object]:
    """Validate the Cloud signature after a receipt key validated the receipt."""
    require_exact_keys(
        envelope,
        {"schema", "ack", "ack_sha256", "signature"},
        "Cloud activation acknowledgment envelope",
    )
    if envelope.get("schema") != CLOUD_ACK_SCHEMA:
        raise ActivationError("the Cloud activation acknowledgment schema is invalid")
    ack = envelope.get("ack")
    signed = envelope.get("signature")
    if not isinstance(ack, dict) or not isinstance(signed, dict):
        raise ActivationError("the Cloud activation acknowledgment is incomplete")
    if envelope.get("ack_sha256") != sha256_value(ack):
        raise ActivationError("the Cloud activation acknowledgment digest is invalid")
    require_exact_keys(
        signed,
        {"algorithm", "key_id", "value"},
        "Cloud acknowledgment signature",
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the Cloud acknowledgment signature algorithm is invalid")
    if signed.get("key_id") != CLOUD_ACK_KEY_ID:
        raise ActivationError("the Cloud acknowledgment signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(ack, key)
    ):
        raise ActivationError(
            "the Cloud activation acknowledgment signature is invalid"
        )
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
        "Cloud activation acknowledgment",
    )
    if ack.get("activation_id") != receipt.get("activation_id"):
        raise ActivationError("the Cloud acknowledgment activation ID is invalid")
    if ack.get("issuer") != CLOUD_ACK_ISSUER:
        raise ActivationError("the Cloud acknowledgment issuer is invalid")
    if ack.get("audience") != CLOUD_ACK_AUDIENCE:
        raise ActivationError("the Cloud acknowledgment audience is invalid")
    if ack.get("idempotency_key") != receipt.get("activation_id"):
        raise ActivationError("the Cloud acknowledgment idempotency key is invalid")
    if ack.get("organization_id_sha256") != receipt.get("organization_id_sha256"):
        raise ActivationError("the Cloud acknowledgment organization is invalid")
    if receipt_envelope is not None:
        if ack.get("readiness_receipt_sha256") != receipt_envelope.get(
            "receipt_sha256"
        ):
            raise ActivationError("the Cloud acknowledgment receipt digest is invalid")
    else:
        require_sha256(
            ack.get("readiness_receipt_sha256"),
            "Cloud acknowledgment readiness receipt",
        )
    if (
        ack.get("prior_state") != "PENDING_RECOVERY"
        or ack.get("new_state") != "PENDING_SCHEDULE"
    ):
        raise ActivationError("the Cloud acknowledgment state transition is invalid")
    require_sha256(ack.get("cloud_revision_sha256"), "Cloud revision")
    applied = parse_time(ack.get("applied_at"), "Cloud activation time")
    if receipt_envelope is not None and applied < parse_time(
        receipt.get("issued_at"), "receipt issue time"
    ):
        raise ActivationError("the Cloud activation precedes recovery readiness")
    if applied > now.astimezone(timezone.utc) + timedelta(minutes=5):
        raise ActivationError("the Cloud activation time is in the future")
    return ack


def validate_continuation_assertion(
    envelope: dict[str, object],
    *,
    key: bytes,
    now: datetime,
    expected: dict[str, object],
) -> dict[str, object]:
    require_exact_keys(
        envelope,
        {"schema", "assertion", "assertion_sha256", "signature"},
        "continuation assertion envelope",
    )
    if envelope.get("schema") != CONTINUATION_SCHEMA:
        raise ActivationError("the continuation assertion schema is invalid")
    assertion = envelope.get("assertion")
    signed = envelope.get("signature")
    if not isinstance(assertion, dict) or not isinstance(signed, dict):
        raise ActivationError("the continuation assertion is incomplete")
    if envelope.get("assertion_sha256") != sha256_value(assertion):
        raise ActivationError("the continuation assertion digest is invalid")
    require_exact_keys(
        signed, {"algorithm", "key_id", "value"}, "continuation signature"
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the continuation signature algorithm is invalid")
    if signed.get("key_id") != CLOUD_CONTINUATION_KEY_ID:
        raise ActivationError("the continuation signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(assertion, key)
    ):
        raise ActivationError("the continuation assertion signature is invalid")
    require_exact_keys(
        assertion,
        {
            "activation_id",
            "active_lease_sha256",
            "audience",
            "backup_required",
            "cloud_revision_sha256",
            "customer_data_remaining",
            "expires_at",
            "issued_at",
            "issuer",
            "lease_event_id",
            "offer_contract",
            "organization_id_sha256",
            "paid_customer_count",
            "pending_customer_count",
            "requested_lease_sequence",
            "service_state",
        },
        "continuation assertion",
    )
    for name, value in expected.items():
        if assertion.get(name) != value:
            raise ActivationError(f"the continuation {name.replace('_', ' ')} is invalid")
    if assertion.get("issuer") != CLOUD_CONTINUATION_ISSUER:
        raise ActivationError("the continuation issuer is invalid")
    if assertion.get("audience") != CLOUD_CONTINUATION_AUDIENCE:
        raise ActivationError("the continuation audience is invalid")
    if assertion.get("backup_required") is not True:
        raise ActivationError("the continuation does not require backup protection")
    if assertion.get("service_state") != "ACTIVE":
        raise ActivationError("the continuation service state is invalid")
    remaining = assertion.get("customer_data_remaining")
    if not isinstance(remaining, bool):
        raise ActivationError("the continuation customer-data state is invalid")
    counts: list[int] = []
    for name in ("paid_customer_count", "pending_customer_count"):
        count = assertion.get(name)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ActivationError(f"the continuation {name.replace('_', ' ')} is invalid")
        counts.append(count)
    if not remaining and all(count == 0 for count in counts):
        raise ActivationError("the continuation has no protected customer state")
    require_sha256(assertion.get("cloud_revision_sha256"), "Cloud revision")
    issued = parse_time(assertion.get("issued_at"), "continuation issue time")
    expires = parse_time(assertion.get("expires_at"), "continuation expiry time")
    if expires <= issued or expires - issued > CONTINUATION_VALIDITY:
        raise ActivationError("the continuation validity is invalid")
    current = now.astimezone(timezone.utc)
    if current < issued - timedelta(minutes=5) or current > expires:
        raise ActivationError("the continuation assertion is not active")
    return assertion


def _continuation_expectation(
    prior_lease_envelope: dict[str, object], prior: dict[str, object]
) -> dict[str, object]:
    prior_sha = require_sha256(
        prior_lease_envelope.get("lease_sha256"), "prior schedule lease"
    )
    sequence = int(prior["lease_sequence"]) + 1
    activation_id = str(prior["activation_id"])
    return {
        "activation_id": activation_id,
        "active_lease_sha256": prior_sha,
        "lease_event_id": renewal_lease_event_id(
            activation_id, prior_sha, sequence
        ),
        "offer_contract": prior["offer_contract"],
        "organization_id_sha256": prior["organization_id_sha256"],
        "requested_lease_sequence": sequence,
    }


def validate_continuation_acceptance(
    envelope: dict[str, object],
    prior_lease_envelope: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    lease_key: bytes,
    renewal_receipt_key: bytes,
    continuation_key: bytes,
    state_key: bytes,
    now: datetime,
) -> dict[str, object]:
    require_exact_keys(
        envelope,
        {"schema", "acceptance", "acceptance_sha256", "signature"},
        "continuation acceptance envelope",
    )
    if envelope.get("schema") != CONTINUATION_ACCEPTANCE_SCHEMA:
        raise ActivationError("the continuation acceptance schema is invalid")
    acceptance = envelope.get("acceptance")
    signed = envelope.get("signature")
    if not isinstance(acceptance, dict) or not isinstance(signed, dict):
        raise ActivationError("the continuation acceptance is incomplete")
    if envelope.get("acceptance_sha256") != sha256_value(acceptance):
        raise ActivationError("the continuation acceptance digest is invalid")
    require_exact_keys(
        signed,
        {"algorithm", "key_id", "value"},
        "continuation acceptance signature",
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError(
            "the continuation acceptance signature algorithm is invalid"
        )
    if signed.get("key_id") != STATE_KEY_ID:
        raise ActivationError("the continuation acceptance signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(acceptance, state_key)
    ):
        raise ActivationError("the continuation acceptance signature is invalid")
    require_exact_keys(
        acceptance,
        {
            "accepted_at",
            "activation_id",
            "continuation_assertion",
            "continuation_assertion_sha256",
            "lease_event_id",
            "prior_lease_sha256",
            "requested_lease_sequence",
        },
        "continuation acceptance",
    )
    embedded = acceptance.get("continuation_assertion")
    if not isinstance(embedded, dict):
        raise ActivationError("the accepted continuation assertion is missing")
    embedded_sha = require_sha256(
        acceptance.get("continuation_assertion_sha256"),
        "accepted continuation assertion",
    )
    if not hmac.compare_digest(embedded_sha, sha256_value(embedded)):
        raise ActivationError("the accepted continuation assertion digest is invalid")
    prior_validation = validate_admission(
        prior_lease_envelope,
        receipt_key=receipt_key,
        cloud_ack_key=cloud_ack_key,
        lease_key=lease_key,
        renewal_receipt_key=renewal_receipt_key,
        continuation_key=continuation_key,
        now=now,
        protective_backup=True,
    )
    prior = prior_validation["lease"]
    assert isinstance(prior, dict)
    expected = _continuation_expectation(prior_lease_envelope, prior)
    for name in (
        "activation_id",
        "lease_event_id",
        "active_lease_sha256",
        "requested_lease_sequence",
    ):
        acceptance_name = (
            "prior_lease_sha256" if name == "active_lease_sha256" else name
        )
        if acceptance.get(acceptance_name) != expected[name]:
            raise ActivationError(
                f"the continuation acceptance {acceptance_name.replace('_', ' ')} is invalid"
            )
    accepted_at = parse_time(
        acceptance.get("accepted_at"), "continuation acceptance time"
    )
    if accepted_at > now.astimezone(timezone.utc) + timedelta(minutes=5):
        raise ActivationError("the continuation acceptance time is in the future")
    embedded_payload = embedded.get("assertion")
    if not isinstance(embedded_payload, dict):
        raise ActivationError("the accepted continuation assertion is incomplete")
    assertion_issued = parse_time(
        embedded_payload.get("issued_at"), "continuation issue time"
    )
    assertion_expires = parse_time(
        embedded_payload.get("expires_at"), "continuation expiry time"
    )
    if not assertion_issued <= accepted_at <= assertion_expires:
        raise ActivationError(
            "the continuation acceptance is not within assertion validity"
        )
    assertion = validate_continuation_assertion(
        embedded,
        key=continuation_key,
        now=accepted_at,
        expected=expected,
    )
    return {
        "acceptance": acceptance,
        "assertion": assertion,
        "prior_lease": prior,
    }


def accept_continuation(
    prior_lease_envelope: dict[str, object],
    continuation_envelope: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    lease_key: bytes,
    renewal_receipt_key: bytes,
    continuation_key: bytes,
    state_key: bytes,
    now: datetime,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    if existing is not None:
        validation = validate_continuation_acceptance(
            existing,
            prior_lease_envelope,
            receipt_key=receipt_key,
            cloud_ack_key=cloud_ack_key,
            lease_key=lease_key,
            renewal_receipt_key=renewal_receipt_key,
            continuation_key=continuation_key,
            state_key=state_key,
            now=now,
        )
        acceptance = validation["acceptance"]
        assert isinstance(acceptance, dict)
        if acceptance.get("continuation_assertion") != continuation_envelope:
            raise ActivationError(
                "the continuation retry conflicts with retained acceptance"
            )
        return existing

    prior_validation = validate_admission(
        prior_lease_envelope,
        receipt_key=receipt_key,
        cloud_ack_key=cloud_ack_key,
        lease_key=lease_key,
        renewal_receipt_key=renewal_receipt_key,
        continuation_key=continuation_key,
        now=now,
        protective_backup=True,
    )
    prior = prior_validation["lease"]
    assert isinstance(prior, dict)
    expected = _continuation_expectation(prior_lease_envelope, prior)
    validate_continuation_assertion(
        continuation_envelope,
        key=continuation_key,
        now=now,
        expected=expected,
    )
    acceptance: dict[str, object] = {
        "accepted_at": iso_time(now),
        "activation_id": expected["activation_id"],
        "continuation_assertion": continuation_envelope,
        "continuation_assertion_sha256": sha256_value(continuation_envelope),
        "lease_event_id": expected["lease_event_id"],
        "prior_lease_sha256": expected["active_lease_sha256"],
        "requested_lease_sequence": expected["requested_lease_sequence"],
    }
    return {
        "schema": CONTINUATION_ACCEPTANCE_SCHEMA,
        "acceptance": acceptance,
        "acceptance_sha256": sha256_value(acceptance),
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": STATE_KEY_ID,
            "value": signature(acceptance, state_key),
        },
    }


def issue_renewal_receipt(
    prior_lease_envelope: dict[str, object],
    backup: dict[str, object],
    restore_evidence: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    lease_key: bytes,
    renewal_receipt_key: bytes,
    continuation_key: bytes | None,
    now: datetime,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    validation = validate_admission(
        prior_lease_envelope,
        receipt_key=receipt_key,
        cloud_ack_key=cloud_ack_key,
        lease_key=lease_key,
        renewal_receipt_key=renewal_receipt_key,
        continuation_key=continuation_key,
        now=now,
        protective_backup=True,
    )
    prior = validation["lease"]
    assert isinstance(prior, dict)
    prior_sha = require_sha256(
        prior_lease_envelope.get("lease_sha256"), "prior schedule lease"
    )
    sequence = int(prior["lease_sequence"]) + 1
    lease_event_id = renewal_lease_event_id(
        str(prior["activation_id"]), prior_sha, sequence
    )
    validate_backup_evidence(backup)
    prior_receipt_envelope = prior.get("readiness_receipt")
    if not isinstance(prior_receipt_envelope, dict):
        raise ActivationError("the prior lease readiness receipt is missing")
    prior_receipt = prior_receipt_envelope.get("receipt")
    if not isinstance(prior_receipt, dict):
        raise ActivationError("the prior lease readiness receipt is incomplete")
    prior_backup = prior_receipt.get("backup")
    if not isinstance(prior_backup, dict) or sha256_value(prior_backup) == sha256_value(
        backup
    ):
        raise ActivationError("the renewal must bind a new exact backup")
    validate_restore_evidence(backup, restore_evidence)
    issued = parse_time(restore_evidence.get("completed_at"), "renewal receipt issue time")
    if issued <= parse_time(prior.get("issued_at"), "prior lease issue time"):
        raise ActivationError("the renewal recovery evidence is not newer than the lease")
    if issued > now.astimezone(timezone.utc) + timedelta(minutes=5):
        raise ActivationError("the renewal recovery evidence is in the future")
    receipt: dict[str, object] = {
        "activation_id": prior["activation_id"],
        "audience": RENEWAL_READINESS_AUDIENCE,
        "backup": backup,
        "expires_at": iso_time(issued + RECEIPT_VALIDITY),
        "issued_at": iso_time(issued),
        "issuer": RENEWAL_READINESS_ISSUER,
        "lease_event_id": lease_event_id,
        "offer_contract": prior["offer_contract"],
        "organization_id_sha256": prior["organization_id_sha256"],
        "payment_event_id_sha256": prior_receipt["payment_event_id_sha256"],
        "prior_lease_sha256": prior_sha,
        "readiness_state": "DATABASE_RECOVERY_READY",
        "recovery_scope": "database_only",
        "restore": restore_evidence,
    }
    result = {
        "schema": RENEWAL_RECEIPT_SCHEMA,
        "receipt": receipt,
        "receipt_sha256": sha256_value(receipt),
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": RENEWAL_READINESS_KEY_ID,
            "value": signature(receipt, renewal_receipt_key),
        },
    }
    if existing is not None and existing != result:
        raise ActivationError("the renewal receipt conflicts with retained state")
    return existing if existing is not None else result


def validate_renewal_receipt(
    envelope: dict[str, object],
    *,
    key: bytes,
    now: datetime,
    expected: dict[str, object],
) -> dict[str, object]:
    require_exact_keys(
        envelope,
        {"schema", "receipt", "receipt_sha256", "signature"},
        "renewal receipt envelope",
    )
    if envelope.get("schema") != RENEWAL_RECEIPT_SCHEMA:
        raise ActivationError("the renewal receipt schema is invalid")
    receipt = envelope.get("receipt")
    signed = envelope.get("signature")
    if not isinstance(receipt, dict) or not isinstance(signed, dict):
        raise ActivationError("the renewal receipt is incomplete")
    if envelope.get("receipt_sha256") != sha256_value(receipt):
        raise ActivationError("the renewal receipt digest is invalid")
    require_exact_keys(
        signed, {"algorithm", "key_id", "value"}, "renewal receipt signature"
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the renewal receipt signature algorithm is invalid")
    if signed.get("key_id") != RENEWAL_READINESS_KEY_ID:
        raise ActivationError("the renewal receipt signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(receipt, key)
    ):
        raise ActivationError("the renewal receipt signature is invalid")
    require_exact_keys(
        receipt,
        {
            "activation_id",
            "audience",
            "backup",
            "expires_at",
            "issued_at",
            "issuer",
            "lease_event_id",
            "offer_contract",
            "organization_id_sha256",
            "payment_event_id_sha256",
            "prior_lease_sha256",
            "readiness_state",
            "recovery_scope",
            "restore",
        },
        "renewal receipt",
    )
    for name, value in expected.items():
        if receipt.get(name) != value:
            raise ActivationError(f"the renewal receipt {name.replace('_', ' ')} is invalid")
    if receipt.get("issuer") != RENEWAL_READINESS_ISSUER:
        raise ActivationError("the renewal receipt issuer is invalid")
    if receipt.get("audience") != RENEWAL_READINESS_AUDIENCE:
        raise ActivationError("the renewal receipt audience is invalid")
    if receipt.get("readiness_state") != "DATABASE_RECOVERY_READY":
        raise ActivationError("the renewal receipt readiness state is invalid")
    if receipt.get("recovery_scope") != "database_only":
        raise ActivationError("the renewal receipt scope is invalid")
    require_sha256(receipt.get("payment_event_id_sha256"), "payment event ID")
    backup = receipt.get("backup")
    restore = receipt.get("restore")
    if not isinstance(backup, dict) or not isinstance(restore, dict):
        raise ActivationError("the renewal receipt evidence is incomplete")
    validate_backup_evidence(backup)
    validate_restore_evidence(backup, restore)
    issued = parse_time(receipt.get("issued_at"), "renewal receipt issue time")
    expires = parse_time(receipt.get("expires_at"), "renewal receipt expiry time")
    if expires - issued != RECEIPT_VALIDITY:
        raise ActivationError("the renewal receipt validity is invalid")
    current = now.astimezone(timezone.utc)
    if current < issued - timedelta(minutes=5) or current > expires:
        raise ActivationError("the renewal receipt is not active")
    return receipt


def renew_admission(
    prior_lease_envelope: dict[str, object],
    continuation_acceptance_envelope: dict[str, object],
    renewal_receipt_envelope: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    lease_key: bytes,
    renewal_receipt_key: bytes,
    continuation_key: bytes,
    state_key: bytes,
    now: datetime,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    acceptance_validation = validate_continuation_acceptance(
        continuation_acceptance_envelope,
        prior_lease_envelope,
        receipt_key=receipt_key,
        cloud_ack_key=cloud_ack_key,
        lease_key=lease_key,
        renewal_receipt_key=renewal_receipt_key,
        continuation_key=continuation_key,
        state_key=state_key,
        now=now,
    )
    prior = acceptance_validation["prior_lease"]
    assert isinstance(prior, dict)
    acceptance = acceptance_validation["acceptance"]
    assertion = acceptance_validation["assertion"]
    assert isinstance(acceptance, dict) and isinstance(assertion, dict)
    prior_sha = str(acceptance["prior_lease_sha256"])
    sequence = int(acceptance["requested_lease_sequence"])
    event_id = str(acceptance["lease_event_id"])
    continuation_envelope = acceptance["continuation_assertion"]
    assert isinstance(continuation_envelope, dict)
    receipt = validate_renewal_receipt(
        renewal_receipt_envelope,
        key=renewal_receipt_key,
        now=now,
        expected={
            "activation_id": prior["activation_id"],
            "lease_event_id": event_id,
            "offer_contract": prior["offer_contract"],
            "organization_id_sha256": prior["organization_id_sha256"],
            "prior_lease_sha256": prior_sha,
        },
    )
    if parse_time(assertion.get("issued_at"), "continuation issue time") > parse_time(
        receipt.get("issued_at"), "renewal receipt issue time"
    ):
        raise ActivationError("the renewal recovery proof predates the continuation")
    issued = parse_time(receipt.get("issued_at"), "renewal receipt issue time")
    payload: dict[str, object] = {
        "activation_id": prior["activation_id"],
        "audience": OPS_LEASE_AUDIENCE,
        "cloud_readiness_ack": prior["cloud_readiness_ack"],
        "continuation_assertion": continuation_envelope,
        "continuation_policy": CONTINUATION_POLICY,
        "expires_at": iso_time(issued + LEASE_VALIDITY),
        "issued_at": iso_time(issued),
        "issuer": OPS_LEASE_ISSUER,
        "lease_event_id": event_id,
        "lease_sequence": sequence,
        "offer_contract": prior["offer_contract"],
        "organization_id_sha256": prior["organization_id_sha256"],
        "prior_lease_sha256": prior_sha,
        "readiness_receipt": renewal_receipt_envelope,
        "renewal_due_at": iso_time(issued + LEASE_RENEWAL_INTERVAL),
        "requested_cadence_seconds": 43_200,
    }
    result = signed_lease(payload, key=lease_key)
    if existing is not None and existing != result:
        raise ActivationError("the lease renewal conflicts with retained state")
    return existing if existing is not None else result


def validate_cloud_lease_ack(
    envelope: dict[str, object],
    *,
    key: bytes,
    lease_envelope: dict[str, object],
    lease: dict[str, object],
    now: datetime,
) -> dict[str, object]:
    require_exact_keys(
        envelope, {"schema", "ack", "ack_sha256", "signature"}, "lease acknowledgment"
    )
    if envelope.get("schema") != CLOUD_LEASE_ACK_SCHEMA:
        raise ActivationError("the Cloud lease acknowledgment schema is invalid")
    ack = envelope.get("ack")
    signed = envelope.get("signature")
    if not isinstance(ack, dict) or not isinstance(signed, dict):
        raise ActivationError("the Cloud lease acknowledgment is incomplete")
    if envelope.get("ack_sha256") != sha256_value(ack):
        raise ActivationError("the Cloud lease acknowledgment digest is invalid")
    require_exact_keys(
        signed, {"algorithm", "key_id", "value"}, "Cloud lease signature"
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the Cloud lease signature algorithm is invalid")
    if signed.get("key_id") != CLOUD_LEASE_ACK_KEY_ID:
        raise ActivationError("the Cloud lease signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(ack, key)
    ):
        raise ActivationError("the Cloud lease acknowledgment signature is invalid")
    require_exact_keys(
        ack,
        {
            "activation_id",
            "applied_at",
            "audience",
            "cloud_revision_sha256",
            "issuer",
            "lease_event_id",
            "lease_sequence",
            "lease_sha256",
            "new_state",
            "organization_id_sha256",
            "prior_state",
        },
        "Cloud lease acknowledgment",
    )
    exact = {
        "activation_id": lease.get("activation_id"),
        "lease_event_id": lease.get("lease_event_id"),
        "lease_sequence": lease.get("lease_sequence"),
        "lease_sha256": lease_envelope.get("lease_sha256"),
        "organization_id_sha256": lease.get("organization_id_sha256"),
    }
    for name, value in exact.items():
        if ack.get(name) != value:
            raise ActivationError(f"the Cloud lease {name.replace('_', ' ')} is invalid")
    if ack.get("issuer") != CLOUD_LEASE_ACK_ISSUER:
        raise ActivationError("the Cloud lease acknowledgment issuer is invalid")
    if ack.get("audience") != CLOUD_LEASE_ACK_AUDIENCE:
        raise ActivationError("the Cloud lease acknowledgment audience is invalid")
    if ack.get("new_state") != "ACTIVE":
        raise ActivationError("the Cloud lease acknowledgment state is invalid")
    sequence = int(lease["lease_sequence"])
    if sequence == 0:
        if ack.get("prior_state") != "PENDING_SCHEDULE":
            raise ActivationError("the initial Cloud lease transition is invalid")
    elif ack.get("prior_state") not in {"ACTIVE", "RENEWAL_OVERDUE"}:
        raise ActivationError("the renewal Cloud lease transition is invalid")
    require_sha256(ack.get("cloud_revision_sha256"), "Cloud revision")
    applied = parse_time(ack.get("applied_at"), "Cloud lease application time")
    issued = parse_time(lease.get("issued_at"), "lease issue time")
    if applied < issued or applied > now.astimezone(timezone.utc) + timedelta(minutes=5):
        raise ActivationError("the Cloud lease application time is invalid")
    return ack


def validate_admission(
    envelope: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    lease_key: bytes,
    now: datetime,
    renewal_receipt_key: bytes | None = None,
    continuation_key: bytes | None = None,
    protective_backup: bool = False,
) -> dict[str, object]:
    require_exact_keys(
        envelope,
        {"schema", "lease", "lease_sha256", "signature"},
        "schedule lease",
    )
    if envelope.get("schema") != ADMISSION_SCHEMA:
        raise ActivationError("the schedule lease schema is invalid")
    admission = envelope.get("lease")
    signed = envelope.get("signature")
    if not isinstance(admission, dict) or not isinstance(signed, dict):
        raise ActivationError("the schedule lease is incomplete")
    if envelope.get("lease_sha256") != sha256_value(admission):
        raise ActivationError("the schedule lease digest is invalid")
    require_exact_keys(signed, {"algorithm", "key_id", "value"}, "lease signature")
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the schedule lease signature algorithm is invalid")
    if signed.get("key_id") != OPS_LEASE_KEY_ID:
        raise ActivationError("the schedule lease signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(admission, lease_key)
    ):
        raise ActivationError("the schedule lease signature is invalid")
    require_exact_keys(
        admission,
        {
            "activation_id",
            "audience",
            "cloud_readiness_ack",
            "continuation_assertion",
            "continuation_policy",
            "expires_at",
            "issued_at",
            "issuer",
            "lease_event_id",
            "lease_sequence",
            "offer_contract",
            "organization_id_sha256",
            "prior_lease_sha256",
            "readiness_receipt",
            "renewal_due_at",
            "requested_cadence_seconds",
        },
        "schedule lease payload",
    )
    if admission.get("issuer") != OPS_LEASE_ISSUER:
        raise ActivationError("the schedule lease issuer is invalid")
    if admission.get("audience") != OPS_LEASE_AUDIENCE:
        raise ActivationError("the schedule lease audience is invalid")
    if admission.get("offer_contract") != OFFER_CONTRACT:
        raise ActivationError("the schedule lease offer is invalid")
    if admission.get("continuation_policy") != CONTINUATION_POLICY:
        raise ActivationError("the schedule lease continuation policy is invalid")
    if admission.get("requested_cadence_seconds") != 43_200:
        raise ActivationError("the schedule lease cadence is invalid")
    activation_id = admission.get("activation_id")
    if not isinstance(activation_id, str) or ACTIVATION_ID.fullmatch(activation_id) is None:
        raise ActivationError("the schedule lease activation ID is invalid")
    require_sha256(admission.get("organization_id_sha256"), "lease organization")
    event_id = admission.get("lease_event_id")
    if not isinstance(event_id, str) or LEASE_EVENT_ID.fullmatch(event_id) is None:
        raise ActivationError("the schedule lease event ID is invalid")
    sequence = admission.get("lease_sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise ActivationError("the schedule lease sequence is invalid")
    issued = parse_time(admission.get("issued_at"), "lease issue time")
    renewal_due = parse_time(admission.get("renewal_due_at"), "lease renewal time")
    expires = parse_time(admission.get("expires_at"), "lease expiry time")
    if renewal_due - issued != LEASE_RENEWAL_INTERVAL:
        raise ActivationError("the schedule lease renewal interval is invalid")
    if expires - issued != LEASE_VALIDITY:
        raise ActivationError("the schedule lease validity is invalid")
    receipt_envelope = admission.get("readiness_receipt")
    ack_envelope = admission.get("cloud_readiness_ack")
    if not isinstance(receipt_envelope, dict) or not isinstance(ack_envelope, dict):
        raise ActivationError("the schedule lease evidence is incomplete")
    ack_payload = ack_envelope.get("ack")
    if not isinstance(ack_payload, dict):
        raise ActivationError("the schedule lease acknowledgment is incomplete")
    applied = parse_time(ack_payload.get("applied_at"), "Cloud activation time")
    if sequence == 0:
        if admission.get("prior_lease_sha256") is not None:
            raise ActivationError("the initial schedule lease has a prior lease")
        if admission.get("continuation_assertion") is not None:
            raise ActivationError("the initial schedule lease has a continuation")
        if event_id != initial_lease_event_id(activation_id):
            raise ActivationError("the initial schedule lease event ID is invalid")
        receipt = validate_receipt(receipt_envelope, key=receipt_key, now=applied)
    else:
        prior_sha = require_sha256(
            admission.get("prior_lease_sha256"), "prior schedule lease"
        )
        if renewal_receipt_key is None or continuation_key is None:
            raise ActivationError("the renewal verification keys are missing")
        receipt = validate_renewal_receipt(
            receipt_envelope,
            key=renewal_receipt_key,
            now=issued,
            expected={
                "activation_id": activation_id,
                "lease_event_id": event_id,
                "offer_contract": admission.get("offer_contract"),
                "organization_id_sha256": admission.get("organization_id_sha256"),
                "prior_lease_sha256": prior_sha,
            },
        )
        assertion_envelope = admission.get("continuation_assertion")
        if not isinstance(assertion_envelope, dict):
            raise ActivationError("the renewal continuation assertion is missing")
        if event_id != renewal_lease_event_id(activation_id, prior_sha, sequence):
            raise ActivationError("the renewal schedule lease event ID is invalid")
        assertion_payload = assertion_envelope.get("assertion")
        if not isinstance(assertion_payload, dict):
            raise ActivationError("the renewal continuation assertion is incomplete")
        assertion_issued = parse_time(
            assertion_payload.get("issued_at"), "continuation issue time"
        )
        validate_continuation_assertion(
            assertion_envelope,
            key=continuation_key,
            now=assertion_issued,
            expected={
                "activation_id": activation_id,
                "active_lease_sha256": prior_sha,
                "lease_event_id": event_id,
                "offer_contract": admission.get("offer_contract"),
                "organization_id_sha256": admission.get("organization_id_sha256"),
                "requested_lease_sequence": sequence,
            },
        )
        if assertion_issued > issued:
            raise ActivationError("the schedule lease predates its continuation")
    ack = validate_cloud_ack_signature(
        ack_envelope,
        key=cloud_ack_key,
        receipt_envelope=(receipt_envelope if sequence == 0 else None),
        receipt=receipt,
        now=now,
    )
    if admission.get("activation_id") != receipt.get("activation_id"):
        raise ActivationError("the schedule lease activation ID is invalid")
    if admission.get("organization_id_sha256") != receipt.get("organization_id_sha256"):
        raise ActivationError("the schedule lease organization is invalid")
    if admission.get("offer_contract") != receipt.get("offer_contract"):
        raise ActivationError("the schedule lease offer binding is invalid")
    if sequence == 0 and applied > parse_time(receipt.get("expires_at"), "receipt expiry time"):
        raise ActivationError("Cloud accepted an expired readiness receipt")
    if ack.get("new_state") != "PENDING_SCHEDULE":
        raise ActivationError("the schedule lease readiness is invalid")
    expected_issue_time = (
        ack_payload.get("applied_at") if sequence == 0 else receipt.get("issued_at")
    )
    if iso_time(issued) != expected_issue_time:
        raise ActivationError("the schedule lease issue time is invalid")
    current = now.astimezone(timezone.utc)
    if current < issued - timedelta(minutes=5):
        raise ActivationError("the schedule lease is not active yet")
    expired = current > expires
    renewal_overdue = current > renewal_due
    if expired and not protective_backup:
        raise ActivationError("the schedule lease has expired for customer admission")
    return {
        "customer_admission_allowed": not expired,
        "expired": expired,
        "lease": admission,
        "protective_backup_allowed": True,
        "renewal_overdue": renewal_overdue,
    }


def record_active(
    existing: dict[str, object],
    admission_envelope: dict[str, object],
    lease_ack_envelope: dict[str, object],
    *,
    receipt_key: bytes,
    cloud_ack_key: bytes,
    lease_key: bytes,
    cloud_lease_ack_key: bytes,
    now: datetime,
) -> dict[str, object]:
    validation = validate_admission(
        admission_envelope,
        receipt_key=receipt_key,
        cloud_ack_key=cloud_ack_key,
        lease_key=lease_key,
        now=now,
    )
    admission = validation["lease"]
    assert isinstance(admission, dict)
    if admission.get("lease_sequence") != 0:
        raise ActivationError("only the initial schedule lease can record activation")
    validate_cloud_lease_ack(
        lease_ack_envelope,
        key=cloud_lease_ack_key,
        lease_envelope=admission_envelope,
        lease=admission,
        now=now,
    )
    state = read_state(existing).copy()
    if state.get("stage") not in {"READY", "ACTIVE"}:
        raise ActivationError("recovery readiness must precede customer activation")
    receipt = admission.get("readiness_receipt")
    if not isinstance(receipt, dict):
        raise ActivationError("the schedule lease evidence is incomplete")
    if admission.get("activation_id") != state.get("activation_id"):
        raise ActivationError("the schedule admission binds a different activation")
    if admission.get("organization_id_sha256") != state.get("organization_id_sha256"):
        raise ActivationError("the schedule admission binds a different organization")
    if receipt.get("receipt_sha256") != state.get("readiness_receipt_sha256"):
        raise ActivationError("the schedule admission binds a different receipt")
    lease_sha = require_sha256(admission_envelope.get("lease_sha256"), "schedule lease")
    lease_ack_sha = require_sha256(
        lease_ack_envelope.get("ack_sha256"), "Cloud lease acknowledgment"
    )
    retained_lease = state.get("schedule_lease_sha256")
    retained_ack = state.get("cloud_lease_ack_sha256")
    if state.get("stage") == "ACTIVE":
        if retained_lease == lease_sha and retained_ack == lease_ack_sha:
            return existing
        raise ActivationError("the active state binds a different schedule lease")
    state["schedule_lease_sha256"] = lease_sha
    state["cloud_lease_ack_sha256"] = lease_ack_sha
    state["stage"] = "ACTIVE"
    return state_envelope(state)


def validate_deactivation_request(
    envelope: dict[str, object], *, key: bytes, now: datetime
) -> tuple[dict[str, object], str]:
    require_exact_keys(
        envelope, {"schema", "request", "signature"}, "deactivation request envelope"
    )
    if envelope.get("schema") != DEACTIVATION_REQUEST_SCHEMA:
        raise ActivationError("the deactivation request schema is invalid")
    request = envelope.get("request")
    signed = envelope.get("signature")
    if not isinstance(request, dict) or not isinstance(signed, dict):
        raise ActivationError("the deactivation request is incomplete")
    require_exact_keys(
        signed, {"algorithm", "key_id", "value"}, "deactivation request signature"
    )
    if signed.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ActivationError("the deactivation signature algorithm is invalid")
    if signed.get("key_id") != CLOUD_DEACTIVATION_KEY_ID:
        raise ActivationError("the deactivation signature key is invalid")
    actual = signed.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, signature(request, key)
    ):
        raise ActivationError("the deactivation signature is invalid")
    require_exact_keys(
        request,
        {
            "activation_id",
            "active_lease_sha256",
            "audience",
            "customer_data_remaining",
            "deactivation_id",
            "expires_at",
            "final_backup_retention_expired_at",
            "issued_at",
            "issuer",
            "paid_customer_count",
            "pending_customer_count",
            "retention_deletion_complete",
            "retention_deletion_completed_at",
            "target",
            "zero_customer_proof",
        },
        "deactivation request",
    )
    deactivation_id = request.get("deactivation_id")
    if (
        not isinstance(deactivation_id, str)
        or DEACTIVATION_ID.fullmatch(deactivation_id) is None
    ):
        raise ActivationError("the deactivation ID is invalid")
    activation_id = request.get("activation_id")
    if (
        not isinstance(activation_id, str)
        or ACTIVATION_ID.fullmatch(activation_id) is None
    ):
        raise ActivationError("the deactivation activation ID is invalid")
    if request.get("issuer") != CLOUD_DEACTIVATION_ISSUER:
        raise ActivationError("the deactivation issuer is invalid")
    if request.get("audience") != CLOUD_DEACTIVATION_AUDIENCE:
        raise ActivationError("the deactivation audience is invalid")
    if request.get("target") != "schedule_and_monitor":
        raise ActivationError("the deactivation target is invalid")
    if request.get("paid_customer_count") != 0:
        raise ActivationError("paid customer data still requires backups")
    if request.get("pending_customer_count") != 0:
        raise ActivationError("pending customer data still requires backups")
    if request.get("customer_data_remaining") is not False:
        raise ActivationError("customer data still requires backups")
    if request.get("retention_deletion_complete") is not True:
        raise ActivationError("retention or deletion work is incomplete")
    require_sha256(request.get("active_lease_sha256"), "active schedule lease")
    proof_envelope = request.get("zero_customer_proof")
    if not isinstance(proof_envelope, dict):
        raise ActivationError("the zero-customer proof is missing")
    proof, _ = validate_zero_customer_proof(proof_envelope)
    if proof.get("active_lease_sha256") != request.get("active_lease_sha256"):
        raise ActivationError("the zero-customer proof binds a different schedule lease")
    for field in (
        "paid_customer_count",
        "pending_customer_count",
        "customer_data_remaining",
        "retention_deletion_complete",
    ):
        if proof.get(field) != request.get(field):
            raise ActivationError(f"the zero-customer proof {field} does not match")
    if proof.get("observed_at") != request.get("retention_deletion_completed_at"):
        raise ActivationError("the zero-customer proof observation time does not match")
    if proof.get("final_backup_retention_expired_at") != request.get(
        "final_backup_retention_expired_at"
    ):
        raise ActivationError("the zero-customer proof retention expiry does not match")
    final_expiry = parse_time(
        request.get("final_backup_retention_expired_at"),
        "final backup retention expiry",
    )
    completed = parse_time(
        request.get("retention_deletion_completed_at"),
        "retention and deletion completion time",
    )
    issued = parse_time(request.get("issued_at"), "deactivation issue time")
    expires = parse_time(request.get("expires_at"), "deactivation expiry time")
    current = now.astimezone(timezone.utc)
    if not final_expiry <= completed <= issued <= expires:
        raise ActivationError("the deactivation times are out of order")
    if expires - issued > MAXIMUM_REQUEST_VALIDITY:
        raise ActivationError("the deactivation validity is too long")
    if issued > current + timedelta(minutes=5) or current > expires:
        raise ActivationError("the deactivation request is not active")
    return request, sha256_value(request)


def validate_zero_customer_proof(
    envelope: dict[str, object],
) -> tuple[dict[str, object], str]:
    require_exact_keys(
        envelope,
        {"schema", "proof", "proof_revision_sha256"},
        "zero-customer proof envelope",
    )
    if envelope.get("schema") != ZERO_CUSTOMER_PROOF_SCHEMA:
        raise ActivationError("the zero-customer proof schema is invalid")
    proof = envelope.get("proof")
    if not isinstance(proof, dict):
        raise ActivationError("the zero-customer proof is incomplete")
    require_exact_keys(
        proof,
        {
            "active_lease_sha256",
            "cloud_revision_sha256",
            "customer_data_remaining",
            "deletion_receipt_sha256",
            "entitlement_ledger_revision_sha256",
            "final_backup_retention_expired_at",
            "observed_at",
            "paid_customer_count",
            "pending_customer_count",
            "retention_deletion_complete",
            "retention_receipt_sha256",
        },
        "zero-customer proof",
    )
    for field in (
        "active_lease_sha256",
        "cloud_revision_sha256",
        "deletion_receipt_sha256",
        "entitlement_ledger_revision_sha256",
        "retention_receipt_sha256",
    ):
        require_sha256(proof.get(field), field.replace("_", " "))
    if proof.get("paid_customer_count") != 0:
        raise ActivationError("the zero-customer proof has paid customers")
    if proof.get("pending_customer_count") != 0:
        raise ActivationError("the zero-customer proof has pending customers")
    if proof.get("customer_data_remaining") is not False:
        raise ActivationError("the zero-customer proof has customer data")
    if proof.get("retention_deletion_complete") is not True:
        raise ActivationError("the zero-customer proof has incomplete retention work")
    observed = parse_time(proof.get("observed_at"), "zero-customer observation time")
    final_expiry = parse_time(
        proof.get("final_backup_retention_expired_at"),
        "zero-customer final backup retention expiry",
    )
    if final_expiry > observed:
        raise ActivationError("the zero-customer proof precedes final backup expiry")
    proof_sha = require_sha256(
        envelope.get("proof_revision_sha256"), "zero-customer proof revision"
    )
    if not hmac.compare_digest(proof_sha, sha256_value(proof)):
        raise ActivationError("the zero-customer proof revision is invalid")
    return proof, proof_sha


def issue_deactivation_authorization(
    request_envelope: dict[str, object],
    *,
    request_key: bytes,
    receipt_key: bytes,
    now: datetime,
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    request, request_sha = validate_deactivation_request(
        request_envelope, key=request_key, now=now
    )
    authorization = {
        "activation_id": request["activation_id"],
        "active_lease_sha256": request["active_lease_sha256"],
        "authorized_at": request["issued_at"],
        "authorized_monitor_enabled": False,
        "authorized_schedule_enabled": False,
        "deactivation_id": request["deactivation_id"],
        "empty_control_stack_retained": True,
        "proof_revision_sha256": request["zero_customer_proof"][
            "proof_revision_sha256"
        ],
        "request_sha256": request_sha,
    }
    envelope = {
        "schema": DEACTIVATION_AUTHORIZATION_SCHEMA,
        "authorization": authorization,
        "authorization_sha256": sha256_value(authorization),
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": OPS_DEACTIVATION_KEY_ID,
            "value": signature(authorization, receipt_key),
        },
    }
    if existing is not None and existing != envelope:
        raise ActivationError(
            "the deactivation retry conflicts with retained authorization"
        )
    return existing if existing is not None else envelope


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    begin_command = commands.add_parser("begin")
    begin_command.add_argument("--request", required=True)
    begin_command.add_argument("--existing-state")
    begin_command.add_argument("--hmac-key-env", required=True)
    begin_command.add_argument("--now")
    begin_command.add_argument("--output", required=True)

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

    admission_command = commands.add_parser(
        "create-lease", aliases=["create-admission"]
    )
    admission_command.add_argument("--receipt", required=True)
    admission_command.add_argument("--cloud-ack", required=True)
    admission_command.add_argument("--existing-lease")
    admission_command.add_argument("--receipt-hmac-key-env", required=True)
    admission_command.add_argument("--cloud-ack-hmac-key-env", required=True)
    admission_command.add_argument("--lease-hmac-key-env", required=True)
    admission_command.add_argument("--now")
    admission_command.add_argument("--output", required=True)

    verify_admission_command = commands.add_parser(
        "verify-lease", aliases=["verify-admission"]
    )
    verify_admission_command.add_argument("--lease", "--admission", required=True)
    verify_admission_command.add_argument("--receipt-hmac-key-env", required=True)
    verify_admission_command.add_argument("--cloud-ack-hmac-key-env", required=True)
    verify_admission_command.add_argument("--lease-hmac-key-env", required=True)
    verify_admission_command.add_argument("--renewal-receipt-hmac-key-env")
    verify_admission_command.add_argument("--continuation-hmac-key-env")
    verify_admission_command.add_argument("--protective-backup", action="store_true")
    verify_admission_command.add_argument("--now")

    renewal_receipt_command = commands.add_parser("issue-renewal-receipt")
    renewal_receipt_command.add_argument("--prior-lease", required=True)
    renewal_receipt_command.add_argument("--backup-evidence", required=True)
    renewal_receipt_command.add_argument("--restore-evidence", required=True)
    renewal_receipt_command.add_argument("--existing-receipt")
    renewal_receipt_command.add_argument("--receipt-hmac-key-env", required=True)
    renewal_receipt_command.add_argument("--cloud-ack-hmac-key-env", required=True)
    renewal_receipt_command.add_argument("--lease-hmac-key-env", required=True)
    renewal_receipt_command.add_argument(
        "--renewal-receipt-hmac-key-env", required=True
    )
    renewal_receipt_command.add_argument("--continuation-hmac-key-env")
    renewal_receipt_command.add_argument("--now")
    renewal_receipt_command.add_argument("--output", required=True)

    accept_command = commands.add_parser("accept-continuation")
    accept_command.add_argument("--prior-lease", required=True)
    accept_command.add_argument("--continuation", required=True)
    accept_command.add_argument("--existing-acceptance")
    accept_command.add_argument("--receipt-hmac-key-env", required=True)
    accept_command.add_argument("--cloud-ack-hmac-key-env", required=True)
    accept_command.add_argument("--lease-hmac-key-env", required=True)
    accept_command.add_argument("--renewal-receipt-hmac-key-env", required=True)
    accept_command.add_argument("--continuation-hmac-key-env", required=True)
    accept_command.add_argument("--state-hmac-key-env", required=True)
    accept_command.add_argument("--now")
    accept_command.add_argument("--output", required=True)

    renew_command = commands.add_parser("renew-lease")
    renew_command.add_argument("--prior-lease", required=True)
    renew_command.add_argument("--continuation-acceptance", required=True)
    renew_command.add_argument("--renewal-receipt", required=True)
    renew_command.add_argument("--existing-lease")
    renew_command.add_argument("--receipt-hmac-key-env", required=True)
    renew_command.add_argument("--cloud-ack-hmac-key-env", required=True)
    renew_command.add_argument("--lease-hmac-key-env", required=True)
    renew_command.add_argument("--renewal-receipt-hmac-key-env", required=True)
    renew_command.add_argument("--continuation-hmac-key-env", required=True)
    renew_command.add_argument("--state-hmac-key-env", required=True)
    renew_command.add_argument("--now")
    renew_command.add_argument("--output", required=True)

    active_command = commands.add_parser("record-active")
    active_command.add_argument("--state", required=True)
    active_command.add_argument("--lease", "--admission", required=True)
    active_command.add_argument("--lease-ack", required=True)
    active_command.add_argument("--receipt-hmac-key-env", required=True)
    active_command.add_argument("--cloud-ack-hmac-key-env", required=True)
    active_command.add_argument("--lease-hmac-key-env", required=True)
    active_command.add_argument("--cloud-lease-ack-hmac-key-env", required=True)
    active_command.add_argument("--now")
    active_command.add_argument("--output", required=True)

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

    deactivation_command = commands.add_parser("issue-deactivation-authorization")
    deactivation_command.add_argument("--request", required=True)
    deactivation_command.add_argument("--existing-authorization")
    deactivation_command.add_argument("--request-hmac-key-env", required=True)
    deactivation_command.add_argument("--receipt-hmac-key-env", required=True)
    deactivation_command.add_argument("--now")
    deactivation_command.add_argument("--output", required=True)
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
        elif args.command in {"create-lease", "create-admission"}:
            now = (
                parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
            )
            result = create_admission(
                read_object(args.receipt, "readiness receipt"),
                read_object(args.cloud_ack, "Cloud activation acknowledgment"),
                receipt_key=secret(args.receipt_hmac_key_env),
                cloud_ack_key=secret(args.cloud_ack_hmac_key_env),
                lease_key=secret(args.lease_hmac_key_env),
                now=now,
                existing=read_object(args.existing_lease, "existing schedule lease")
                if args.existing_lease
                else None,
            )
            write_object(args.output, result)
        elif args.command in {"verify-lease", "verify-admission"}:
            result = validate_admission(
                read_object(args.lease, "schedule lease"),
                receipt_key=secret(args.receipt_hmac_key_env),
                cloud_ack_key=secret(args.cloud_ack_hmac_key_env),
                lease_key=secret(args.lease_hmac_key_env),
                renewal_receipt_key=secret(args.renewal_receipt_hmac_key_env)
                if args.renewal_receipt_hmac_key_env
                else None,
                continuation_key=secret(args.continuation_hmac_key_env)
                if args.continuation_hmac_key_env
                else None,
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
                protective_backup=args.protective_backup,
            )
        elif args.command == "issue-renewal-receipt":
            result = issue_renewal_receipt(
                read_object(args.prior_lease, "prior schedule lease"),
                read_object(args.backup_evidence, "renewal backup evidence"),
                read_object(args.restore_evidence, "renewal restore evidence"),
                receipt_key=secret(args.receipt_hmac_key_env),
                cloud_ack_key=secret(args.cloud_ack_hmac_key_env),
                lease_key=secret(args.lease_hmac_key_env),
                renewal_receipt_key=secret(args.renewal_receipt_hmac_key_env),
                continuation_key=secret(args.continuation_hmac_key_env)
                if args.continuation_hmac_key_env
                else None,
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
                existing=read_object(args.existing_receipt, "existing renewal receipt")
                if args.existing_receipt
                else None,
            )
            write_object(args.output, result)
        elif args.command == "accept-continuation":
            result = accept_continuation(
                read_object(args.prior_lease, "prior schedule lease"),
                read_object(args.continuation, "continuation assertion"),
                receipt_key=secret(args.receipt_hmac_key_env),
                cloud_ack_key=secret(args.cloud_ack_hmac_key_env),
                lease_key=secret(args.lease_hmac_key_env),
                renewal_receipt_key=secret(args.renewal_receipt_hmac_key_env),
                continuation_key=secret(args.continuation_hmac_key_env),
                state_key=secret(args.state_hmac_key_env),
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
                existing=read_object(
                    args.existing_acceptance, "existing continuation acceptance"
                )
                if args.existing_acceptance
                else None,
            )
            write_object(args.output, result)
        elif args.command == "renew-lease":
            result = renew_admission(
                read_object(args.prior_lease, "prior schedule lease"),
                read_object(
                    args.continuation_acceptance, "continuation acceptance"
                ),
                read_object(args.renewal_receipt, "renewal readiness receipt"),
                receipt_key=secret(args.receipt_hmac_key_env),
                cloud_ack_key=secret(args.cloud_ack_hmac_key_env),
                lease_key=secret(args.lease_hmac_key_env),
                renewal_receipt_key=secret(args.renewal_receipt_hmac_key_env),
                continuation_key=secret(args.continuation_hmac_key_env),
                state_key=secret(args.state_hmac_key_env),
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
                existing=read_object(args.existing_lease, "existing renewed lease")
                if args.existing_lease
                else None,
            )
            write_object(args.output, result)
        elif args.command == "record-active":
            result = record_active(
                read_object(args.state, "activation state"),
                read_object(args.lease, "schedule lease"),
                read_object(args.lease_ack, "Cloud schedule lease acknowledgment"),
                receipt_key=secret(args.receipt_hmac_key_env),
                cloud_ack_key=secret(args.cloud_ack_hmac_key_env),
                lease_key=secret(args.lease_hmac_key_env),
                cloud_lease_ack_key=secret(args.cloud_lease_ack_hmac_key_env),
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
            )
            write_object(args.output, result)
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
        elif args.command == "resume":
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
        else:
            result = issue_deactivation_authorization(
                read_object(args.request, "deactivation request"),
                request_key=secret(args.request_hmac_key_env),
                receipt_key=secret(args.receipt_hmac_key_env),
                now=parse_time(args.now, "now")
                if args.now
                else datetime.now(timezone.utc),
                existing=read_object(
                    args.existing_authorization,
                    "existing deactivation authorization",
                )
                if args.existing_authorization
                else None,
            )
            write_object(args.output, result)
        print(json.dumps(result, sort_keys=True))
    except (ActivationError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
