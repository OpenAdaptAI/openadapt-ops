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
CLOUD_ACK_KEY = b"cloud-activation-ack-key-that-is-at-least-32-bytes"
STATE_KEY = b"ops-activation-state-key-that-is-at-least-32-bytes"
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
            "value": activation.signature(ack, CLOUD_ACK_KEY),
        },
    }


def test_paid_activation_is_exact_and_retry_safe() -> None:
    request = signed_request()
    first = activation.begin(request, key=REQUEST_KEY, now=NOW)
    retry = activation.begin(
        request, key=REQUEST_KEY, now=NOW + timedelta(hours=1), existing=first
    )
    assert retry == first

    changed = copy.deepcopy(request)
    changed["request"]["organization_id_sha256"] = "a" * 64
    changed["signature"]["value"] = activation.signature(
        changed["request"], REQUEST_KEY
    )
    with pytest.raises(activation.ActivationError, match="conflicts"):
        activation.begin(changed, key=REQUEST_KEY, now=NOW, existing=first)


def test_expired_request_requires_the_successful_authority_claim() -> None:
    expired = NOW + timedelta(hours=1)
    with pytest.raises(activation.ActivationError, match="expired"):
        activation.begin(signed_request(), key=REQUEST_KEY, now=expired)

    verified = activation.verify_claimed_request(
        signed_request(),
        key=REQUEST_KEY,
        now=expired,
        authority_claim_sha256="a" * 64,
    )
    assert verified == {
        "activation_id": ACTIVATION_ID,
        "recovery_point_stamp": "20260826T120100Z",
        "request_sha256": activation.sha256_value(signed_request()["request"]),
    }

    with pytest.raises(activation.ActivationError, match="dispatch authority claim"):
        activation.verify_claimed_request(
            signed_request(),
            key=REQUEST_KEY,
            now=expired,
            authority_claim_sha256="not-a-digest",
        )


def test_public_request_fixture_matches_the_exact_signed_contract() -> None:
    fixture = json.loads((FIXTURE_ROOT / "request.json").read_text(encoding="utf-8"))
    assert fixture == signed_request()
    activation.validate_request(fixture, key=REQUEST_KEY, now=NOW)


def test_request_refuses_unknown_fields_and_bad_signatures() -> None:
    unknown = copy.deepcopy(signed_request())
    unknown["request"]["later_contract"] = True
    unknown["signature"]["value"] = activation.signature(
        unknown["request"], REQUEST_KEY
    )
    with pytest.raises(activation.ActivationError, match="fields are not exact"):
        activation.validate_request(unknown, key=REQUEST_KEY, now=NOW)

    forged = copy.deepcopy(signed_request())
    forged["signature"]["value"] = "0" * 64
    with pytest.raises(activation.ActivationError, match="signature is invalid"):
        activation.validate_request(forged, key=REQUEST_KEY, now=NOW)


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


def test_schedule_and_renewal_commands_are_not_present() -> None:
    for command in (
        "create-lease",
        "verify-lease",
        "issue-renewal-receipt",
        "accept-continuation",
        "renew-lease",
        "record-active",
        "issue-deactivation-authorization",
    ):
        with pytest.raises(SystemExit):
            activation.parser().parse_args([command])


def test_durable_state_is_signed_and_tamper_evident() -> None:
    state = activation.begin(signed_request(), key=REQUEST_KEY, now=NOW)
    signed = activation.sign_state(state, key=STATE_KEY)
    assert activation.validate_signed_state(signed, key=STATE_KEY) == state

    changed = copy.deepcopy(signed)
    changed["state_envelope"]["state"]["stage"] = "READY"
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


def test_readiness_receipt_is_exact_signed_and_expires_after_90_days() -> None:
    state, receipt = ready()
    assert state["state"]["stage"] == "READY"
    payload = activation.validate_receipt(
        receipt,
        key=RECEIPT_KEY,
        now=datetime(2026, 8, 26, 12, 12, tzinfo=UTC),
    )
    issued = datetime.fromisoformat(str(payload["issued_at"]).replace("Z", "+00:00"))
    expires = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
    assert expires - issued == timedelta(days=90)
    assert payload["backup"]["ciphertext_storage_class"] == "GLACIER_IR"
    assert payload["backup"]["manifest_storage_class"] == "STANDARD"

    forged = copy.deepcopy(receipt)
    forged["receipt"]["backup"]["ciphertext_version_id"] = "other-version"
    forged["receipt_sha256"] = activation.sha256_value(forged["receipt"])
    with pytest.raises(activation.ActivationError, match="signature"):
        activation.validate_receipt(
            forged,
            key=RECEIPT_KEY,
            now=datetime(2026, 8, 26, 12, 12, tzinfo=UTC),
        )


def test_cloud_ack_is_exact_and_only_records_pending_schedule() -> None:
    _, receipt = ready()
    ack = signed_cloud_ack(receipt)
    result = activation.validate_cloud_readiness_ack(
        ack,
        receipt,
        receipt_key=RECEIPT_KEY,
        cloud_ack_key=CLOUD_ACK_KEY,
        now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
    )
    assert result["new_state"] == "PENDING_SCHEDULE"
    assert "activated_at" not in result
    assert "checkout_enabled" not in result
    assert "customer_use_authorized" not in result
    assert "ACTIVE" not in json.dumps(ack)
    assert "BACKUP_ACTIVE" not in json.dumps(ack)

    for field, value in (
        ("new_state", "ACTIVE"),
        ("prior_state", "DISPATCHED"),
        ("readiness_receipt_sha256", "0" * 64),
    ):
        changed = copy.deepcopy(ack)
        changed["ack"][field] = value
        changed["ack_sha256"] = activation.sha256_value(changed["ack"])
        changed["signature"]["value"] = activation.signature(
            changed["ack"], CLOUD_ACK_KEY
        )
        with pytest.raises(activation.ActivationError, match="state is invalid"):
            activation.validate_cloud_readiness_ack(
                changed,
                receipt,
                receipt_key=RECEIPT_KEY,
                cloud_ack_key=CLOUD_ACK_KEY,
                now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
            )


def test_cloud_ack_rejects_changed_receipt_ack_or_extra_authority() -> None:
    _, receipt = ready()
    ack = signed_cloud_ack(receipt)

    changed_receipt = copy.deepcopy(receipt)
    changed_receipt["receipt"]["organization_id_sha256"] = "a" * 64
    changed_receipt["receipt_sha256"] = activation.sha256_value(
        changed_receipt["receipt"]
    )
    changed_receipt["signature"]["value"] = activation.signature(
        changed_receipt["receipt"], RECEIPT_KEY
    )
    with pytest.raises(activation.ActivationError, match="state is invalid"):
        activation.validate_cloud_readiness_ack(
            ack,
            changed_receipt,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_ACK_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
        )

    changed_ack = copy.deepcopy(ack)
    changed_ack["ack"]["cloud_revision_sha256"] = "a" * 64
    changed_ack["ack_sha256"] = activation.sha256_value(changed_ack["ack"])
    with pytest.raises(activation.ActivationError, match="signature"):
        activation.validate_cloud_readiness_ack(
            changed_ack,
            receipt,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_ACK_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
        )

    extra = copy.deepcopy(ack)
    extra["ack"]["checkout_enabled"] = False
    extra["ack_sha256"] = activation.sha256_value(extra["ack"])
    extra["signature"]["value"] = activation.signature(extra["ack"], CLOUD_ACK_KEY)
    with pytest.raises(activation.ActivationError, match="fields are not exact"):
        activation.validate_cloud_readiness_ack(
            extra,
            receipt,
            receipt_key=RECEIPT_KEY,
            cloud_ack_key=CLOUD_ACK_KEY,
            now=datetime(2026, 8, 26, 12, 13, tzinfo=UTC),
        )


def test_readiness_files_require_canonical_utf8_json_and_one_lf(
    tmp_path: Path,
) -> None:
    _, receipt = ready()
    canonical = activation.stable_json(receipt) + "\n"
    path = tmp_path / "readiness.json"
    path.write_text(canonical, encoding="utf-8")
    assert activation.read_canonical_object(path, "readiness receipt") == receipt

    reordered = json.dumps(
        {
            "signature": receipt["signature"],
            "schema": receipt["schema"],
            "receipt_sha256": receipt["receipt_sha256"],
            "receipt": receipt["receipt"],
        },
        separators=(",", ":"),
    )
    for invalid in (canonical.rstrip("\n"), canonical + "\n", reordered + "\n"):
        path.write_text(invalid, encoding="utf-8")
        with pytest.raises(
            activation.ActivationError, match="canonical JSON plus one LF"
        ):
            activation.read_canonical_object(path, "readiness receipt")


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
    ready_state, _ = activation.issue_receipt(restored, key=RECEIPT_KEY)
    cases = (
        (pending, {"backup": True, "restore": True, "receipt": True}),
        (backed_up, {"backup": False, "restore": True, "receipt": True}),
        (restored, {"backup": False, "restore": False, "receipt": True}),
        (ready_state, {"backup": False, "restore": False, "receipt": False}),
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
