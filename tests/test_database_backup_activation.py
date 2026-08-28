from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "database_backup_activation.py"
SPEC = importlib.util.spec_from_file_location("database_backup_activation", MODULE_PATH)
assert SPEC and SPEC.loader
activation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(activation)

UTC = timezone.utc
REQUEST_KEY = b"payment-signal-key-that-is-at-least-32-bytes"
RECEIPT_KEY = b"readiness-receipt-key-that-is-at-least-32-bytes"
CLOUD_KEY = b"cloud-activation-ack-key-that-is-at-least-32-bytes"
LEASE_KEY = b"ops-schedule-lease-key-that-is-at-least-32-bytes"
CONTINUATION_KEY = b"cloud-continuation-key-that-is-at-least-32-bytes"
RENEWAL_RECEIPT_KEY = b"ops-renewal-receipt-key-that-is-at-least-32-bytes"
LEASE_ACK_KEY = b"cloud-lease-ack-key-that-is-at-least-32-bytes"
STATE_KEY = b"ops-activation-state-key-that-is-at-least-32-bytes"
DEACTIVATION_KEY = b"cloud-deactivation-key-that-is-at-least-32-bytes"
DEACTIVATION_RECEIPT_KEY = b"ops-deactivation-key-that-is-at-least-32-bytes"
NOW = datetime(2026, 8, 26, 12, 1, tzinfo=UTC)
ACTIVATION_ID = "act_" + "1" * 32
ORGANIZATION_SHA = "2" * 64
PAYMENT_SHA = "3" * 64
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "database_backup_activation"


def signed_request() -> dict[str, object]:
    request = {
        "activation_id": ACTIVATION_ID,
        "amount_total_minor": 50_000,
        "audience": activation.PAYMENT_SIGNAL_AUDIENCE,
        "currency": "usd",
        "expires_at": "2026-08-26T12:15:00Z",
        "first_verified_payment": True,
        "issued_at": "2026-08-26T12:00:00Z",
        "issuer": activation.PAYMENT_SIGNAL_ISSUER,
        "offer_contract": activation.OFFER_CONTRACT,
        "organization_id_sha256": ORGANIZATION_SHA,
        "payment_event_id_sha256": PAYMENT_SHA,
        "payment_status": "paid",
        "recovery_point_stamp": "20260826T120100Z",
        "verified_payment_at": "2026-08-26T11:59:00Z",
    }
    return {
        "schema": activation.REQUEST_SCHEMA,
        "request": request,
        "signature": {
            "algorithm": activation.SIGNATURE_ALGORITHM,
            "key_id": activation.PAYMENT_SIGNAL_KEY_ID,
            "value": activation.signature(request, REQUEST_KEY),
        },
    }


def backup_evidence() -> dict[str, object]:
    checksum = base64.b64encode(hashlib.sha256(b"cipher").digest()).decode()
    manifest_checksum = base64.b64encode(hashlib.sha256(b"manifest").digest()).decode()
    stamp = "20260826T120100Z"
    return {
        "artifact_sha256": "4" * 64,
        "aws_account_id": activation.AWS_ACCOUNT_ID,
        "aws_region": activation.AWS_REGION,
        "backup_contract_sha256": "5" * 64,
        "bucket_name": activation.BUCKET,
        "ciphertext_bytes": 1_073_741_824,
        "ciphertext_checksum_sha256": checksum,
        "ciphertext_gib": "1.000000000",
        "ciphertext_key": f"daily/{stamp}/db-backup-{stamp}.tar.gz.age",
        "ciphertext_sha256": "6" * 64,
        "ciphertext_storage_class": "GLACIER_IR",
        "ciphertext_version_id": "cipher-version-1",
        "manifest_checksum_sha256": manifest_checksum,
        "manifest_key": f"daily/{stamp}/artifact-manifest.json",
        "manifest_sha256": "7" * 64,
        "manifest_storage_class": "STANDARD",
        "manifest_version_id": "manifest-version-1",
        "recovery_point_stamp": stamp,
        "repository_commit": "8" * 40,
        "workflow_run_id": "12345",
    }


def restore_evidence(backup: dict[str, object]) -> dict[str, object]:
    return {
        "schema": activation.RESTORE_SCHEMA,
        "artifact_sha256": backup["artifact_sha256"],
        "aws_account_id": backup["aws_account_id"],
        "aws_region": backup["aws_region"],
        "backup_contract_sha256": backup["backup_contract_sha256"],
        "bucket_name": backup["bucket_name"],
        "ciphertext_key": backup["ciphertext_key"],
        "ciphertext_version_id": backup["ciphertext_version_id"],
        "completed_at": "2026-08-26T12:11:00Z",
        "database_restored": True,
        "manifest_key": backup["manifest_key"],
        "manifest_version_id": backup["manifest_version_id"],
        "rpo_seconds_at_start": 120,
        "rto_seconds": 480,
        "started_at": "2026-08-26T12:03:00Z",
        "storage_restored": False,
    }


def ready() -> tuple[dict[str, object], dict[str, object]]:
    state = activation.begin(signed_request(), key=REQUEST_KEY, now=NOW)
    backup = backup_evidence()
    state = activation.record_backup(state, backup)
    state = activation.record_restore(state, restore_evidence(backup))
    return activation.issue_receipt(state, key=RECEIPT_KEY)


def signed_cloud_ack(receipt: dict[str, object]) -> dict[str, object]:
    payload = receipt["receipt"]
    assert isinstance(payload, dict)
    ack = {
        "activation_id": payload["activation_id"],
        "applied_at": "2026-08-26T12:12:00Z",
        "audience": activation.CLOUD_ACK_AUDIENCE,
        "cloud_revision_sha256": "9" * 64,
        "idempotency_key": payload["activation_id"],
        "issuer": activation.CLOUD_ACK_ISSUER,
        "new_state": "PENDING_SCHEDULE",
        "organization_id_sha256": payload["organization_id_sha256"],
        "prior_state": "PENDING_RECOVERY",
        "readiness_receipt_sha256": receipt["receipt_sha256"],
    }
    return {
        "schema": activation.CLOUD_ACK_SCHEMA,
        "ack": ack,
        "ack_sha256": activation.sha256_value(ack),
        "signature": {
            "algorithm": activation.SIGNATURE_ALGORITHM,
            "key_id": activation.CLOUD_ACK_KEY_ID,
            "value": activation.signature(ack, CLOUD_KEY),
        },
    }


def initial_lease() -> tuple[
    dict[str, object], dict[str, object], dict[str, object]
]:
    state, receipt = ready()
    lease = activation.create_admission(
        receipt,
        signed_cloud_ack(receipt),
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
    )
    return state, receipt, lease


def signed_lease_ack(
    lease: dict[str, object], *, prior_state: str = "PENDING_SCHEDULE"
) -> dict[str, object]:
    payload = lease["lease"]
    assert isinstance(payload, dict)
    ack = {
        "activation_id": payload["activation_id"],
        "applied_at": "2026-08-26T12:13:00Z"
        if payload["lease_sequence"] == 0
        else "2026-10-25T12:13:00Z",
        "audience": activation.CLOUD_LEASE_ACK_AUDIENCE,
        "cloud_revision_sha256": "b" * 64,
        "issuer": activation.CLOUD_LEASE_ACK_ISSUER,
        "lease_event_id": payload["lease_event_id"],
        "lease_sequence": payload["lease_sequence"],
        "lease_sha256": lease["lease_sha256"],
        "new_state": "ACTIVE",
        "organization_id_sha256": payload["organization_id_sha256"],
        "prior_state": prior_state,
    }
    return {
        "schema": activation.CLOUD_LEASE_ACK_SCHEMA,
        "ack": ack,
        "ack_sha256": activation.sha256_value(ack),
        "signature": {
            "algorithm": activation.SIGNATURE_ALGORITHM,
            "key_id": activation.CLOUD_LEASE_ACK_KEY_ID,
            "value": activation.signature(ack, LEASE_ACK_KEY),
        },
    }


def renewal_evidence() -> tuple[dict[str, object], dict[str, object]]:
    backup = backup_evidence()
    stamp = "20261025T120100Z"
    backup.update(
        {
            "artifact_sha256": "a" * 64,
            "ciphertext_key": f"daily/{stamp}/db-backup-{stamp}.tar.gz.age",
            "ciphertext_sha256": "b" * 64,
            "ciphertext_version_id": "cipher-version-2",
            "manifest_key": f"daily/{stamp}/artifact-manifest.json",
            "manifest_sha256": "c" * 64,
            "manifest_version_id": "manifest-version-2",
            "recovery_point_stamp": stamp,
            "workflow_run_id": "23456",
        }
    )
    restore = restore_evidence(backup)
    restore["started_at"] = "2026-10-25T12:03:00Z"
    restore["completed_at"] = "2026-10-25T12:11:00Z"
    return backup, restore


def renewal_contract(
    prior_lease: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    backup, restore = renewal_evidence()
    now = datetime(2026, 10, 25, 12, 13, tzinfo=UTC)
    receipt = activation.issue_renewal_receipt(
        prior_lease,
        backup,
        restore,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        renewal_receipt_key=RENEWAL_RECEIPT_KEY,
        continuation_key=CONTINUATION_KEY,
        now=now,
    )
    prior_sha = prior_lease["lease_sha256"]
    assert isinstance(prior_sha, str)
    event_id = activation.renewal_lease_event_id(ACTIVATION_ID, prior_sha, 1)
    assertion = {
        "activation_id": ACTIVATION_ID,
        "active_lease_sha256": prior_sha,
        "audience": activation.CLOUD_CONTINUATION_AUDIENCE,
        "backup_required": True,
        "cloud_revision_sha256": "d" * 64,
        "customer_data_remaining": False,
        "expires_at": "2026-10-25T12:15:00Z",
        "issued_at": "2026-10-25T12:00:00Z",
        "issuer": activation.CLOUD_CONTINUATION_ISSUER,
        "lease_event_id": event_id,
        "offer_contract": activation.OFFER_CONTRACT,
        "organization_id_sha256": ORGANIZATION_SHA,
        "paid_customer_count": 1,
        "pending_customer_count": 0,
        "requested_lease_sequence": 1,
        "service_state": "ACTIVE",
    }
    continuation = {
        "schema": activation.CONTINUATION_SCHEMA,
        "assertion": assertion,
        "assertion_sha256": activation.sha256_value(assertion),
        "signature": {
            "algorithm": activation.SIGNATURE_ALGORITHM,
            "key_id": activation.CLOUD_CONTINUATION_KEY_ID,
            "value": activation.signature(assertion, CONTINUATION_KEY),
        },
    }
    return receipt, continuation


def accepted_continuation(
    prior_lease: dict[str, object],
    continuation: dict[str, object],
    *,
    now: datetime = datetime(2026, 10, 25, 12, 1, tzinfo=UTC),
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    return activation.accept_continuation(
        prior_lease,
        continuation,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        renewal_receipt_key=RENEWAL_RECEIPT_KEY,
        continuation_key=CONTINUATION_KEY,
        state_key=STATE_KEY,
        now=now,
        existing=existing,
    )


def signed_deactivation_request() -> dict[str, object]:
    proof = {
        "active_lease_sha256": "a" * 64,
        "cloud_revision_sha256": "c" * 64,
        "customer_data_remaining": False,
        "deletion_receipt_sha256": "d" * 64,
        "entitlement_ledger_revision_sha256": "e" * 64,
        "final_backup_retention_expired_at": "2026-11-25T11:00:00Z",
        "observed_at": "2026-11-25T11:30:00Z",
        "paid_customer_count": 0,
        "pending_customer_count": 0,
        "retention_deletion_complete": True,
        "retention_receipt_sha256": "f" * 64,
    }
    proof_envelope = {
        "schema": activation.ZERO_CUSTOMER_PROOF_SCHEMA,
        "proof": proof,
        "proof_revision_sha256": activation.sha256_value(proof),
    }
    request = {
        "activation_id": ACTIVATION_ID,
        "active_lease_sha256": "a" * 64,
        "audience": activation.CLOUD_DEACTIVATION_AUDIENCE,
        "customer_data_remaining": False,
        "deactivation_id": "deact_" + "b" * 32,
        "expires_at": "2026-11-25T12:15:00Z",
        "final_backup_retention_expired_at": "2026-11-25T11:00:00Z",
        "issued_at": "2026-11-25T12:00:00Z",
        "issuer": activation.CLOUD_DEACTIVATION_ISSUER,
        "paid_customer_count": 0,
        "pending_customer_count": 0,
        "retention_deletion_complete": True,
        "retention_deletion_completed_at": "2026-11-25T11:30:00Z",
        "target": "schedule_and_monitor",
        "zero_customer_proof": proof_envelope,
    }
    return {
        "schema": activation.DEACTIVATION_REQUEST_SCHEMA,
        "request": request,
        "signature": {
            "algorithm": activation.SIGNATURE_ALGORITHM,
            "key_id": activation.CLOUD_DEACTIVATION_KEY_ID,
            "value": activation.signature(request, DEACTIVATION_KEY),
        },
    }


def test_paid_activation_is_exact_and_retry_safe() -> None:
    request = signed_request()
    first = activation.begin(request, key=REQUEST_KEY, now=NOW)
    retry = activation.begin(
        request,
        key=REQUEST_KEY,
        now=NOW + timedelta(hours=1),
        existing=first,
    )
    assert retry == first

    changed = copy.deepcopy(request)
    changed["request"]["organization_id_sha256"] = "a" * 64
    changed["signature"]["value"] = activation.signature(
        changed["request"], REQUEST_KEY
    )
    with pytest.raises(activation.ActivationError, match="conflicts"):
        activation.begin(changed, key=REQUEST_KEY, now=NOW, existing=first)


def test_public_request_fixture_matches_the_exact_signed_contract() -> None:
    fixture = json.loads((FIXTURE_ROOT / "request.json").read_text(encoding="utf-8"))
    assert fixture == signed_request()
    activation.validate_request(fixture, key=REQUEST_KEY, now=NOW)


def test_resume_cli_accepts_multiple_signed_state_arguments() -> None:
    parsed = activation.parser().parse_args(
        [
            "resume",
            "--request",
            "request.json",
            "--signed-state",
            "pending.json",
            "--signed-state",
            "ready.json",
            "--request-hmac-key-env",
            "REQUEST_KEY",
            "--state-hmac-key-env",
            "STATE_KEY",
            "--output",
            "state.json",
        ]
    )
    assert parsed.signed_state == ["pending.json", "ready.json"]


def test_durable_state_is_signed_and_tamper_evident() -> None:
    state = activation.begin(signed_request(), key=REQUEST_KEY, now=NOW)
    signed = activation.sign_state(state, key=STATE_KEY)
    assert activation.validate_signed_state(signed, key=STATE_KEY) == state

    changed = copy.deepcopy(signed)
    changed["state_envelope"]["state"]["stage"] = "ACTIVE"
    changed["state_envelope"]["state_sha256"] = activation.sha256_value(
        changed["state_envelope"]["state"]
    )
    with pytest.raises(activation.ActivationError, match="signature"):
        activation.validate_signed_state(changed, key=STATE_KEY)


def test_activation_refuses_wrong_class_and_failed_restore() -> None:
    state = activation.begin(signed_request(), key=REQUEST_KEY, now=NOW)
    backup = backup_evidence()
    backup["ciphertext_storage_class"] = "STANDARD"
    with pytest.raises(activation.ActivationError, match="GLACIER_IR"):
        activation.record_backup(state, backup)

    backup = backup_evidence()
    state = activation.record_backup(state, backup)
    evidence = restore_evidence(backup)
    evidence["database_restored"] = False
    with pytest.raises(activation.ActivationError, match="did not pass"):
        activation.record_restore(state, evidence)
    with pytest.raises(activation.ActivationError, match="restore gate"):
        activation.issue_receipt(state, key=RECEIPT_KEY)


def test_initial_schedule_lease_is_signed_exact_and_retry_safe() -> None:
    _, receipt, lease = initial_lease()
    payload = lease["lease"]
    assert payload["lease_sequence"] == 0
    assert payload["prior_lease_sha256"] is None
    assert payload["continuation_assertion"] is None
    assert payload["issued_at"] == "2026-08-26T12:12:00Z"
    assert payload["renewal_due_at"] == "2026-10-25T12:12:00Z"
    assert payload["expires_at"] == "2026-11-24T12:12:00Z"
    assert payload["lease_event_id"] == activation.initial_lease_event_id(
        ACTIVATION_ID
    )

    status = activation.validate_admission(
        lease,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
    )
    assert status["renewal_overdue"] is False
    assert status["customer_admission_allowed"] is True
    assert (
        activation.create_admission(
            receipt,
            signed_cloud_ack(receipt),
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
            existing=lease,
        )
        == lease
    )

    tampered = copy.deepcopy(lease)
    tampered["lease"]["requested_cadence_seconds"] = 86_400
    tampered["lease_sha256"] = activation.sha256_value(tampered["lease"])
    with pytest.raises(activation.ActivationError, match="signature"):
        activation.validate_admission(
            tampered,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
        )

    changed_ack = signed_cloud_ack(receipt)
    changed_ack["ack"]["cloud_revision_sha256"] = "f" * 64
    changed_ack["ack_sha256"] = activation.sha256_value(changed_ack["ack"])
    changed_ack["signature"]["value"] = activation.signature(
        changed_ack["ack"], CLOUD_KEY
    )
    with pytest.raises(activation.ActivationError, match="conflicts"):
        activation.create_admission(
            receipt,
            changed_ack,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
            existing=lease,
        )


def test_expired_lease_blocks_customer_admission_but_keeps_protection() -> None:
    _, _, lease = initial_lease()
    expired_at = datetime(2026, 11, 25, 12, 13, tzinfo=UTC)
    with pytest.raises(activation.ActivationError, match="expired for customer"):
        activation.validate_admission(
            lease,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            now=expired_at,
        )
    status = activation.validate_admission(
        lease,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        now=expired_at,
        protective_backup=True,
    )
    assert status == {
        "customer_admission_allowed": False,
        "expired": True,
        "lease": lease["lease"],
        "protective_backup_allowed": True,
        "renewal_overdue": True,
    }


def test_continuation_acceptance_survives_expiry_and_rejects_backdating() -> None:
    _, _, prior = initial_lease()
    receipt, continuation = renewal_contract(prior)
    acceptance = accepted_continuation(prior, continuation)
    payload = acceptance["acceptance"]
    assert acceptance["schema"] == activation.CONTINUATION_ACCEPTANCE_SCHEMA
    assert acceptance["signature"]["key_id"] == activation.STATE_KEY_ID
    assert payload["accepted_at"] == "2026-10-25T12:01:00Z"
    assert payload["continuation_assertion"] == continuation
    assert payload["continuation_assertion_sha256"] == activation.sha256_value(
        continuation
    )

    after_assertion_expiry = datetime(2026, 10, 25, 12, 30, tzinfo=UTC)
    assert (
        accepted_continuation(
            prior,
            continuation,
            now=after_assertion_expiry,
            existing=acceptance,
        )
        == acceptance
    )

    forged = copy.deepcopy(acceptance)
    forged["acceptance"]["accepted_at"] = "2026-10-25T11:59:00Z"
    forged["acceptance_sha256"] = activation.sha256_value(forged["acceptance"])
    forged["signature"]["value"] = activation.signature(
        forged["acceptance"], STATE_KEY
    )
    with pytest.raises(activation.ActivationError, match="not within assertion validity"):
        activation.validate_continuation_acceptance(
            forged,
            prior,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            renewal_receipt_key=RENEWAL_RECEIPT_KEY,
            continuation_key=CONTINUATION_KEY,
            state_key=STATE_KEY,
            now=after_assertion_expiry,
        )

    renewed = activation.renew_admission(
        prior,
        acceptance,
        receipt,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        renewal_receipt_key=RENEWAL_RECEIPT_KEY,
        continuation_key=CONTINUATION_KEY,
        state_key=STATE_KEY,
        now=after_assertion_expiry,
    )
    retained = json.loads(
        (FIXTURE_ROOT / "renewed-schedule-lease.json").read_text(encoding="utf-8")
    )
    assert renewed == retained


def test_renewal_binds_sequence_prior_assertion_and_new_recovery() -> None:
    _, _, prior = initial_lease()
    receipt, continuation = renewal_contract(prior)
    acceptance = accepted_continuation(prior, continuation)
    now = datetime(2026, 10, 25, 12, 13, tzinfo=UTC)
    renewed = activation.renew_admission(
        prior,
        acceptance,
        receipt,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        renewal_receipt_key=RENEWAL_RECEIPT_KEY,
        continuation_key=CONTINUATION_KEY,
        state_key=STATE_KEY,
        now=now,
    )
    payload = renewed["lease"]
    assert payload["lease_sequence"] == 1
    assert payload["prior_lease_sha256"] == prior["lease_sha256"]
    assert payload["continuation_assertion"] == continuation
    assert payload["readiness_receipt"] == receipt
    assert payload["lease_event_id"] == activation.renewal_lease_event_id(
        ACTIVATION_ID, prior["lease_sha256"], 1
    )
    status = activation.validate_admission(
        renewed,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        renewal_receipt_key=RENEWAL_RECEIPT_KEY,
        continuation_key=CONTINUATION_KEY,
        now=now,
    )
    assert status["customer_admission_allowed"] is True
    assert (
        activation.renew_admission(
            prior,
            acceptance,
            receipt,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            renewal_receipt_key=RENEWAL_RECEIPT_KEY,
            continuation_key=CONTINUATION_KEY,
            state_key=STATE_KEY,
            now=now,
            existing=renewed,
        )
        == renewed
    )

    fixtures = {
        "initial-schedule-lease.json": prior,
        "initial-schedule-lease-ack.json": signed_lease_ack(prior),
        "renewal-continuation-assertion.json": continuation,
        "renewal-readiness-receipt.json": receipt,
        "renewed-schedule-lease.json": renewed,
    }
    for name, expected in fixtures.items():
        retained = json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
        assert retained == expected

    changed = copy.deepcopy(continuation)
    changed["assertion"]["cloud_revision_sha256"] = "e" * 64
    changed["assertion_sha256"] = activation.sha256_value(changed["assertion"])
    changed["signature"]["value"] = activation.signature(
        changed["assertion"], CONTINUATION_KEY
    )
    with pytest.raises(activation.ActivationError, match="conflicts"):
        activation.accept_continuation(
            prior,
            changed,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            renewal_receipt_key=RENEWAL_RECEIPT_KEY,
            continuation_key=CONTINUATION_KEY,
            state_key=STATE_KEY,
            now=now,
            existing=acceptance,
        )


def test_renewal_rejects_bad_signatures_and_empty_customer_state() -> None:
    _, _, prior = initial_lease()
    receipt, continuation = renewal_contract(prior)
    acceptance = accepted_continuation(prior, continuation)
    now = datetime(2026, 10, 25, 12, 13, tzinfo=UTC)

    bad_receipt = copy.deepcopy(receipt)
    bad_receipt["signature"]["value"] = "0" * 64
    with pytest.raises(activation.ActivationError, match="receipt signature"):
        activation.renew_admission(
            prior,
            acceptance,
            bad_receipt,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            renewal_receipt_key=RENEWAL_RECEIPT_KEY,
            continuation_key=CONTINUATION_KEY,
            state_key=STATE_KEY,
            now=now,
        )

    empty = copy.deepcopy(continuation)
    empty["assertion"]["paid_customer_count"] = 0
    empty["assertion"]["pending_customer_count"] = 0
    empty["assertion"]["customer_data_remaining"] = False
    empty["assertion_sha256"] = activation.sha256_value(empty["assertion"])
    empty["signature"]["value"] = activation.signature(
        empty["assertion"], CONTINUATION_KEY
    )
    with pytest.raises(activation.ActivationError, match="no protected customer"):
        activation.accept_continuation(
            prior,
            empty,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            renewal_receipt_key=RENEWAL_RECEIPT_KEY,
            continuation_key=CONTINUATION_KEY,
            state_key=STATE_KEY,
            now=now,
        )

    with pytest.raises(activation.ActivationError, match="assertion is not active"):
        activation.accept_continuation(
            prior,
            continuation,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            renewal_receipt_key=RENEWAL_RECEIPT_KEY,
            continuation_key=CONTINUATION_KEY,
            state_key=STATE_KEY,
            now=datetime(2026, 10, 25, 12, 16, tzinfo=UTC),
        )


def test_signed_cloud_lease_ack_is_the_only_record_active_gate() -> None:
    state, receipt, lease = initial_lease()
    with pytest.raises(activation.ActivationError, match="schema"):
        activation.record_active(
            state,
            lease,
            signed_cloud_ack(receipt),
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            cloud_lease_ack_key=LEASE_ACK_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
        )
    lease_ack = signed_lease_ack(lease)
    wrong_key = copy.deepcopy(lease_ack)
    wrong_key["signature"]["value"] = activation.signature(
        wrong_key["ack"], CONTINUATION_KEY
    )
    with pytest.raises(activation.ActivationError, match="lease acknowledgment signature"):
        activation.record_active(
            state,
            lease,
            wrong_key,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            cloud_lease_ack_key=LEASE_ACK_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
        )
    active = activation.record_active(
        state,
        lease,
        lease_ack,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        cloud_lease_ack_key=LEASE_ACK_KEY,
        now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
    )
    assert active["state"]["stage"] == "ACTIVE"
    assert active["state"]["schedule_lease_sha256"] == lease["lease_sha256"]
    assert (
        activation.record_active(
            active,
            lease,
            lease_ack,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_KEY,
            lease_key=LEASE_KEY,
            cloud_lease_ack_key=LEASE_ACK_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
        )
        == active
    )


def test_expired_request_cannot_create_late_retained_state() -> None:
    state = activation.begin(signed_request(), key=REQUEST_KEY, now=NOW)
    payload = state["state"].copy()
    payload["created_at"] = "2026-08-26T12:16:00Z"
    late = activation.state_envelope(payload)
    with pytest.raises(activation.ActivationError, match="not created in time"):
        activation.begin(
            signed_request(),
            key=REQUEST_KEY,
            now=NOW + timedelta(hours=1),
            existing=late,
        )


def test_exact_stage_replays_succeed_but_conflicting_replays_fail() -> None:
    state = activation.begin(signed_request(), key=REQUEST_KEY, now=NOW)
    backup = backup_evidence()
    bound = activation.record_backup(state, backup)
    assert activation.record_backup(bound, backup) == bound

    changed = copy.deepcopy(backup)
    changed["ciphertext_version_id"] = "cipher-version-2"
    with pytest.raises(activation.ActivationError, match="different backup"):
        activation.record_backup(bound, changed)

    restore = restore_evidence(backup)
    restored = activation.record_restore(bound, restore)
    assert activation.record_restore(restored, restore) == restored
    changed_restore = copy.deepcopy(restore)
    changed_restore["rto_seconds"] = 481
    with pytest.raises(activation.ActivationError, match="different restore"):
        activation.record_restore(restored, changed_restore)


def test_concurrent_duplicate_claims_select_one_exact_signed_state() -> None:
    request = signed_request()
    state = activation.begin(request, key=REQUEST_KEY, now=NOW)
    signed = activation.sign_state(state, key=STATE_KEY)
    assert (
        activation.resume(
            request,
            request_key=REQUEST_KEY,
            state_key=STATE_KEY,
            now=NOW + timedelta(hours=1),
            signed_states=[signed, copy.deepcopy(signed)],
        )
        == state
    )

    conflict_state = copy.deepcopy(state)
    conflict_state["state"]["attempt_count"] = 2
    conflict_state["state_sha256"] = activation.sha256_value(conflict_state["state"])
    conflict = activation.sign_state(conflict_state, key=STATE_KEY)
    with pytest.raises(activation.ActivationError, match="conflicting PENDING_BACKUP"):
        activation.resume(
            request,
            request_key=REQUEST_KEY,
            state_key=STATE_KEY,
            now=NOW,
            signed_states=[signed, conflict],
        )


def test_same_activation_id_with_different_request_is_rejected_on_resume() -> None:
    request = signed_request()
    state = activation.begin(request, key=REQUEST_KEY, now=NOW)
    signed = activation.sign_state(state, key=STATE_KEY)
    changed = copy.deepcopy(request)
    changed["request"]["payment_event_id_sha256"] = "a" * 64
    changed["signature"]["value"] = activation.signature(
        changed["request"], REQUEST_KEY
    )
    with pytest.raises(activation.ActivationError, match="conflicts"):
        activation.resume(
            changed,
            request_key=REQUEST_KEY,
            state_key=STATE_KEY,
            now=NOW,
            signed_states=[signed],
        )


def test_crash_at_each_recorded_stage_resumes_only_incomplete_work() -> None:
    request = signed_request()
    pending = activation.begin(request, key=REQUEST_KEY, now=NOW)
    backup = backup_evidence()
    backed_up = activation.record_backup(pending, backup)
    restored = activation.record_restore(backed_up, restore_evidence(backup))
    ready_state, receipt = activation.issue_receipt(restored, key=RECEIPT_KEY)
    ack = signed_cloud_ack(receipt)
    admission = activation.create_admission(
        receipt,
        ack,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
    )
    active = activation.record_active(
        ready_state,
        admission,
        signed_lease_ack(admission),
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_KEY,
        lease_key=LEASE_KEY,
        cloud_lease_ack_key=LEASE_ACK_KEY,
        now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
    )
    cases = (
        (pending, {"backup": True, "restore": True, "receipt": True, "callback": True}),
        (
            backed_up,
            {"backup": False, "restore": True, "receipt": True, "callback": True},
        ),
        (
            restored,
            {"backup": False, "restore": False, "receipt": True, "callback": True},
        ),
        (
            ready_state,
            {"backup": False, "restore": False, "receipt": False, "callback": True},
        ),
        (
            active,
            {"backup": False, "restore": False, "receipt": False, "callback": False},
        ),
    )
    retained: list[dict[str, object]] = []
    for state, expected in cases:
        retained.append(activation.sign_state(state, key=STATE_KEY))
        resumed = activation.resume(
            request,
            request_key=REQUEST_KEY,
            state_key=STATE_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
            signed_states=retained,
        )
        assert resumed == state
        assert activation.required_actions(resumed) == expected


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("paid_customer_count", 1, "paid customer data"),
        ("pending_customer_count", 1, "pending customer data"),
        ("customer_data_remaining", True, "customer data"),
        ("retention_deletion_complete", False, "incomplete"),
        (
            "final_backup_retention_expired_at",
            "2026-11-26T11:00:00Z",
            "retention expiry does not match",
        ),
    ],
)
def test_deactivation_refuses_until_zero_customer_shutdown_is_proven(
    field: str, value: object, message: str
) -> None:
    envelope = signed_deactivation_request()
    envelope["request"][field] = value
    envelope["signature"]["value"] = activation.signature(
        envelope["request"], DEACTIVATION_KEY
    )
    with pytest.raises(activation.ActivationError, match=message):
        activation.validate_deactivation_request(
            envelope,
            key=DEACTIVATION_KEY,
            now=datetime(2026, 11, 25, 12, 1, tzinfo=UTC),
        )


def test_deactivation_refuses_a_mismatched_or_rewritten_proof() -> None:
    envelope = signed_deactivation_request()
    envelope["request"]["zero_customer_proof"]["proof"]["cloud_revision_sha256"] = (
        "0" * 64
    )
    envelope["signature"]["value"] = activation.signature(
        envelope["request"], DEACTIVATION_KEY
    )
    with pytest.raises(activation.ActivationError, match="proof revision is invalid"):
        activation.validate_deactivation_request(
            envelope,
            key=DEACTIVATION_KEY,
            now=datetime(2026, 11, 25, 12, 1, tzinfo=UTC),
        )


def test_public_deactivation_fixture_matches_the_exact_signed_contract() -> None:
    fixture = json.loads(
        (FIXTURE_ROOT / "deactivation-request.json").read_text(encoding="utf-8")
    )
    assert fixture == signed_deactivation_request()
    activation.validate_deactivation_request(
        fixture,
        key=DEACTIVATION_KEY,
        now=datetime(2026, 11, 25, 12, 1, tzinfo=UTC),
    )


def test_deactivation_authorization_is_idempotent_and_keeps_empty_stack() -> None:
    request = signed_deactivation_request()
    now = datetime(2026, 11, 25, 12, 1, tzinfo=UTC)
    authorization = activation.issue_deactivation_authorization(
        request,
        request_key=DEACTIVATION_KEY,
        receipt_key=DEACTIVATION_RECEIPT_KEY,
        now=now,
    )
    assert authorization["authorization"]["authorized_schedule_enabled"] is False
    assert authorization["authorization"]["authorized_monitor_enabled"] is False
    assert authorization["authorization"]["empty_control_stack_retained"] is True
    assert (
        activation.issue_deactivation_authorization(
            request,
            request_key=DEACTIVATION_KEY,
            receipt_key=DEACTIVATION_RECEIPT_KEY,
            now=now + timedelta(minutes=1),
            existing=authorization,
        )
        == authorization
    )

    changed = copy.deepcopy(request)
    changed["request"]["zero_customer_proof"]["proof"]["cloud_revision_sha256"] = (
        "0" * 64
    )
    changed["request"]["zero_customer_proof"]["proof_revision_sha256"] = (
        activation.sha256_value(changed["request"]["zero_customer_proof"]["proof"])
    )
    changed["signature"]["value"] = activation.signature(
        changed["request"], DEACTIVATION_KEY
    )
    with pytest.raises(activation.ActivationError, match="conflicts"):
        activation.issue_deactivation_authorization(
            changed,
            request_key=DEACTIVATION_KEY,
            receipt_key=DEACTIVATION_RECEIPT_KEY,
            now=now,
            existing=authorization,
        )
