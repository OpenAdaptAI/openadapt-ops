from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "database_backup_dispatch_reconciliation",
    ROOT / "scripts" / "database_backup_dispatch_reconciliation.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

ACTIVATION_ID = "act_2d49200bcccc6d2b70a392991a6390325d1ab2e7e0c16c81dfc63d1673efa10b"
ENVELOPE_DIGEST = "b31d46c369c8a754dba069033a900b46d64009138834b06d4ece5eede827602f"
ATTEMPT_DIGEST = "76c5e382d0045c0bc1ba849090f947b7076d2cbd04e56d35820fdf7e8d9dec6e"
RESOLUTION_ID = (
    "resolution_fee98ae0e1c9ac366ebfb2fb67fbe549b48a43190033503d9e77a7b1745e8ecf"
)
SIGNING_KEY = "cloud-payment-signal-fixture-key-0123456789abcdef"
WORKFLOW_REVISION = "a" * 40


def encoded(value: object) -> str:
    return base64.b64encode(MODULE.canonical_json(value)).decode()


def ingress_payload() -> tuple[dict[str, object], dict[str, object]]:
    envelope = {
        "schema": "openadapt.database-backup-activation-request/v1",
        "request": {"activation_id": ACTIVATION_ID},
        "signature": {"algorithm": "fixture", "key_id": "fixture", "value": "fixture"},
    }
    envelope_digest = MODULE._sha256(MODULE.canonical_json(envelope))
    attempt_identity = {
        "activation_id": ACTIVATION_ID,
        "attempt_number": 1,
        "dispatch_envelope_sha256": envelope_digest,
        "dispatch_kind": "INITIAL_ACTIVATION",
    }
    attempt_digest = MODULE._sha256(MODULE.canonical_json(attempt_identity))
    attempt = {
        "activation_id": ACTIVATION_ID,
        "attempt_number": 1,
        "audience": MODULE.ATTEMPT_AUDIENCE,
        "dispatch_attempt_id_sha256": attempt_digest,
        "dispatch_envelope_sha256": envelope_digest,
        "dispatch_kind": "INITIAL_ACTIVATION",
        "issuer": MODULE.ATTEMPT_ISSUER,
        "lease_event_id": None,
        "offer_contract": MODULE.OFFER_CONTRACT,
    }
    attempt_bytes = MODULE.canonical_json(attempt)
    attempt_envelope = {
        "schema": MODULE.ATTEMPT_SCHEMA,
        "attempt": attempt,
        "attempt_sha256": MODULE._sha256(attempt_bytes),
        "signature": {
            "algorithm": "HMAC-SHA256",
            "key_id": MODULE.INITIAL_ATTEMPT_KEY_ID,
            "value": hmac.new(
                SIGNING_KEY.encode(), attempt_bytes, hashlib.sha256
            ).hexdigest(),
        },
    }
    payload = {
        "schema": MODULE.INITIAL_SCHEMA,
        "attempt_number": 1,
        "dispatch_attempt_id_sha256": attempt_digest,
        "dispatch_envelope_sha256": envelope_digest,
        "dispatch_attempt_b64": encoded(attempt_envelope),
        "activation_request_b64": encoded(envelope),
    }
    return payload, envelope


def candidate() -> dict[str, object]:
    return {
        "resolution_id": RESOLUTION_ID,
        "dispatch_kind": "INITIAL_ACTIVATION",
        "activation_id": ACTIVATION_ID,
        "attempt_number": 1,
        "organization_id_sha256": "1" * 64,
        "dispatch_attempt_id_sha256": ATTEMPT_DIGEST,
        "dispatch_envelope_sha256": ENVELOPE_DIGEST,
        "lease_event_id": None,
        "prior_lease_sha256": None,
        "requested_lease_sequence": None,
        "last_error_code": "DISPATCH_NOT_CONFIRMED",
        "dispatch_attempted_at": "2026-08-27T16:00:00Z",
        "reconciliation_required_at": "2026-08-27T16:00:00Z",
    }


def empty_inventory(*, observed_at: str = "2026-08-27T16:05:00Z") -> dict[str, object]:
    empty = {"total_count": 0, "workflow_runs": []}
    inventory = MODULE.observe_github_run_inventory(
        dispatch_attempted_at="2026-08-27T16:00:00Z",
        observed_at=observed_at,
        repository={
            "full_name": MODULE.INVENTORY_REPOSITORY,
            "id": MODULE.INVENTORY_REPOSITORY_ID,
        },
        workflow={
            "id": "90210",
            "path": MODULE.INVENTORY_WORKFLOW_PATH,
            "state": "active",
        },
        principal={
            "app_id": "555",
            "app_slug": "openadapt-backup-control",
            "installation_id": "777",
            "target_id": MODULE.INVENTORY_OWNER_ID,
            "target_type": "Organization",
        },
        fetch_page=lambda *_: empty,
    )
    return MODULE.account_github_run_inventory(
        inventory,
        fetch_object=lambda _: pytest.fail("an empty inventory fetched a locator"),
    )


def prepare() -> dict[str, object]:
    return MODULE.prepare_not_received_resolution(
        candidate(),
        expected_attempt_sha256=ATTEMPT_DIGEST,
        expected_envelope_sha256=ENVELOPE_DIGEST,
        issued_at="2026-08-27T16:05:00Z",
        ingress_ledger_object=None,
        github_inventory=empty_inventory(),
    )


def retain(payload: dict[str, object]) -> dict[str, object]:
    return MODULE.retain_ingress(
        MODULE.INITIAL_EVENT,
        payload,
        github_repository=MODULE.INVENTORY_REPOSITORY,
        github_repository_id=MODULE.INVENTORY_REPOSITORY_ID,
        github_run_id="123456",
        github_run_attempt=1,
        received_at="2026-08-27T15:59:59Z",
        workflow_revision=WORKFLOW_REVISION,
        dispatch_signing_key=SIGNING_KEY,
    )


def inventory_scope() -> dict[str, object]:
    return {
        "dispatch_attempted_at": "2026-08-27T16:00:00Z",
        "observed_at": "2026-08-27T16:05:00Z",
        "repository": {
            "full_name": MODULE.INVENTORY_REPOSITORY,
            "id": MODULE.INVENTORY_REPOSITORY_ID,
        },
        "workflow": {
            "id": "90210",
            "path": MODULE.INVENTORY_WORKFLOW_PATH,
            "state": "active",
        },
        "principal": {
            "app_id": "555",
            "app_slug": "openadapt-backup-control",
            "installation_id": "777",
            "target_id": MODULE.INVENTORY_OWNER_ID,
            "target_type": "Organization",
        },
    }


def test_absence_inventory_targets_the_repository_dispatch_activation_workflow() -> None:
    assert MODULE.INVENTORY_WORKFLOW_PATH == ".github/workflows/db-backup-activate.yml"
    assert MODULE.INVENTORY_EVENT == "repository_dispatch"


def test_normal_ingress_retains_digests_and_exact_run_identity_without_envelope() -> None:
    payload, _ = ingress_payload()
    retained = retain(payload)
    assert retained["dispatch_attempt_id_sha256"] == payload["dispatch_attempt_id_sha256"]
    assert retained["dispatch_envelope_sha256"] == payload["dispatch_envelope_sha256"]
    assert retained["attempt_number"] == 1
    assert retained["github_repository_id"] == MODULE.INVENTORY_REPOSITORY_ID
    assert retained["github_run_id"] == "123456"
    assert retained["workflow_revision"] == WORKFLOW_REVISION
    assert "activation_request_b64" not in retained
    assert "dispatch_attempt_b64" not in retained
    assert MODULE.ingress_ledger_key(retained).endswith(
        f"/{payload['dispatch_attempt_id_sha256']}.json"
    )
    locator = MODULE.build_dispatch_run_locator(retained)
    assert set(locator) == MODULE.RUN_LOCATOR_FIELDS
    assert locator["dispatch_attempt_id_sha256"] == payload[
        "dispatch_attempt_id_sha256"
    ]
    assert locator["ingress_ledger_sha256"] == MODULE._sha256(
        MODULE.canonical_json(retained)
    )
    assert MODULE.run_locator_key("123456", 1).endswith("/123456/1.json")


def test_ingress_ledger_is_no_overwrite_idempotent_and_conflict_hard() -> None:
    payload, _ = ingress_payload()
    retained = retain(payload)
    assert MODULE.classify_ingress_write(retained, None) == "CREATE"
    assert MODULE.classify_ingress_write(
        retained, MODULE.canonical_json(retained)
    ) == "IDEMPOTENT"
    with pytest.raises(MODULE.DispatchContractError, match="conflicting bytes"):
        MODULE.classify_ingress_write(retained, b"{}")


def test_ingress_rejects_mismatched_attempt_digest_and_invalid_signature() -> None:
    payload, _ = ingress_payload()
    payload["dispatch_attempt_id_sha256"] = "0" * 64
    with pytest.raises(MODULE.DispatchContractError, match="attempt digest"):
        retain(payload)
    payload, _ = ingress_payload()
    attempt = json.loads(base64.b64decode(str(payload["dispatch_attempt_b64"])))
    attempt["signature"]["value"] = "0" * 64
    payload["dispatch_attempt_b64"] = encoded(attempt)
    with pytest.raises(MODULE.DispatchContractError, match="signature"):
        retain(payload)


def test_shared_lost_before_github_vector_builds_exact_five_minute_resolution() -> None:
    prepared = prepare()
    resolution = prepared["resolution"]
    assert len(resolution) == 16
    assert resolution["resolution_id"] == RESOLUTION_ID
    assert resolution["attempt_number"] == 1
    assert resolution["resolution_state"] == "NOT_RECEIVED"
    assert resolution["dispatch_attempt_id_sha256"] == ATTEMPT_DIGEST
    assert resolution["dispatch_envelope_sha256"] == ENVELOPE_DIGEST
    assert resolution["issued_at"] == "2026-08-27T16:05:00Z"
    assert resolution["expires_at"] == "2026-08-27T16:10:00Z"
    canonical = base64.b64decode(prepared["canonical_resolution_b64"])
    assert MODULE._sha256(canonical) == prepared["resolution_sha256"]


def test_no_resolution_is_prepared_when_absence_is_uncertain() -> None:
    kwargs = {
        "expected_attempt_sha256": ATTEMPT_DIGEST,
        "expected_envelope_sha256": ENVELOPE_DIGEST,
        "issued_at": "2026-08-27T16:05:00Z",
    }
    with pytest.raises(MODULE.DispatchContractError, match="ingress ledger"):
        MODULE.prepare_not_received_resolution(
            candidate(),
            ingress_ledger_object=b"present",
            github_inventory=empty_inventory(),
            **kwargs,
        )
    evidence = empty_inventory()
    evidence["runs"] = [{"id": "9"}]
    unsigned = dict(evidence)
    unsigned.pop("evidence_sha256")
    evidence["evidence_sha256"] = MODULE._sha256(MODULE.canonical_json(unsigned))
    with pytest.raises(MODULE.DispatchContractError, match="incomplete|can match"):
        MODULE.prepare_not_received_resolution(
            candidate(),
            ingress_ledger_object=None,
            github_inventory=evidence,
            **kwargs,
        )


def test_inventory_requires_complete_stable_pagination_and_minimum_window() -> None:
    evidence = empty_inventory()
    assert evidence["dispatch_attempted_at"] == "2026-08-27T16:00:00Z"
    assert evidence["range_start"] == "2026-08-27T15:59:00Z"
    assert evidence["observation_completed_at"] == "2026-08-27T16:05:00Z"
    assert evidence["eventual_consistency_delay_seconds"] == 300
    assert evidence["github_created_at_skew_seconds"] == 60
    with pytest.raises(MODULE.DispatchContractError, match="too short"):
        empty_inventory(observed_at="2026-08-27T16:04:59Z")

    run = {
        "id": "1",
        "run_attempt": 1,
        "event": MODULE.INVENTORY_EVENT,
        "head_branch": "main",
        "head_sha": "a" * 40,
        "workflow_id": "90210",
        "created_at": "2026-08-27T16:01:00Z",
        "run_started_at": "2026-08-27T16:01:01Z",
        "status": "completed",
        "conclusion": "success",
    }
    pages = iter(
        [
            {"total_count": 101, "workflow_runs": [run] * 100},
            {"total_count": 101, "workflow_runs": []},
        ]
    )
    with pytest.raises(MODULE.DispatchContractError, match="pagination ended"):
        MODULE.observe_github_run_inventory(
            **inventory_scope(), fetch_page=lambda *_: next(pages)
        )


def test_inventory_rejects_ambiguous_run_and_changed_high_water() -> None:
    malformed = {"total_count": 1, "workflow_runs": [{"id": "1"}]}
    with pytest.raises(MODULE.DispatchContractError, match="ambiguous"):
        MODULE.observe_github_run_inventory(
            **inventory_scope(), fetch_page=lambda *_: malformed
        )

    empty_then_changed = iter(
        [
            {"total_count": 0, "workflow_runs": []},
            {"total_count": 1, "workflow_runs": []},
        ]
    )
    with pytest.raises(MODULE.DispatchContractError, match="high-water total changed"):
        MODULE.observe_github_run_inventory(
            **inventory_scope(), fetch_page=lambda *_: next(empty_then_changed)
        )


def test_inventory_requires_a_backed_global_locator_for_every_run() -> None:
    payload, _ = ingress_payload()
    retained = retain(payload)
    locator = MODULE.build_dispatch_run_locator(retained)
    run = {
        "id": retained["github_run_id"],
        "run_attempt": retained["github_run_attempt"],
        "event": MODULE.INVENTORY_EVENT,
        "head_branch": "main",
        "head_sha": retained["workflow_revision"],
        "workflow_id": "90210",
        "created_at": "2026-08-27T16:01:00Z",
        "run_started_at": "2026-08-27T16:01:01Z",
        "status": "completed",
        "conclusion": "success",
    }
    page = {"total_count": 1, "workflow_runs": [run]}
    observed = MODULE.observe_github_run_inventory(
        **inventory_scope(), fetch_page=lambda *_: page
    )
    objects = {
        MODULE.run_locator_key(
            str(retained["github_run_id"]), int(retained["github_run_attempt"])
        ): MODULE.canonical_json(locator),
        MODULE.ingress_ledger_key(retained): MODULE.canonical_json(retained),
    }
    accounted = MODULE.account_github_run_inventory(
        observed, fetch_object=lambda key: objects[key]
    )
    assert len(accounted["run_accounts"]) == 1
    MODULE.prepare_not_received_resolution(
        candidate(),
        expected_attempt_sha256=ATTEMPT_DIGEST,
        expected_envelope_sha256=ENVELOPE_DIGEST,
        issued_at="2026-08-27T16:05:00Z",
        ingress_ledger_object=None,
        github_inventory=accounted,
    )
    with pytest.raises((KeyError, MODULE.DispatchContractError)):
        MODULE.account_github_run_inventory(
            observed, fetch_object=lambda key: {}[key]
        )


def test_delayed_attempt_cannot_continue_after_not_received_resolution() -> None:
    MODULE.assert_cloud_attempt_unresolved(
        candidate(),
        http_status=404,
        response={"error": "ACTIVATION_NOT_FOUND", "message": "Not retained."},
    )
    status = {
        "schema": MODULE.STATUS_SCHEMA,
        "resolution_id": RESOLUTION_ID,
        "dispatch_kind": "INITIAL_ACTIVATION",
        "reissue_state": "QUEUED",
        "replacement_payload_sha256": "d" * 64,
        "replacement_dispatch_envelope_sha256": "e" * 64,
        "attempt_count": 0,
        "consumed_at": "2026-08-27T16:05:01Z",
        "delivered_at": None,
    }
    with pytest.raises(MODULE.DispatchContractError, match="already resolved"):
        MODULE.assert_cloud_attempt_unresolved(
            candidate(), http_status=200, response=status
        )
    with pytest.raises(MODULE.DispatchContractError, match="uncertain"):
        MODULE.assert_cloud_attempt_unresolved(
            candidate(),
            http_status=500,
            response={"error": "INTERNAL_ERROR", "message": "Unavailable."},
        )


def test_claim_wins_and_resolution_wins_are_mutually_exclusive() -> None:
    payload, _ = ingress_payload()
    claim_request = MODULE.build_dispatch_claim(retain(payload))
    claim_receipt = {
        "schema": MODULE.CLAIM_RECEIPT_SCHEMA,
        "dispatch_attempt_id_sha256": payload["dispatch_attempt_id_sha256"],
        "attempt_state": "RECEIVED",
        "claim_sha256": claim_request["claim_sha256"],
        "received_at": "2026-08-27T16:00:01Z",
    }
    claim_result = MODULE.verify_dispatch_claim_receipt(
        claim_request, http_status=200, response=claim_receipt
    )
    assert claim_result["claim_sha256"] == claim_request["claim_sha256"]

    with pytest.raises(MODULE.DispatchContractError, match="lost the atomic"):
        MODULE.verify_resolution_reissue_receipt(
            {
                "schema": MODULE.RESOLUTION_SCHEMA,
                "resolution": prepare()["resolution"],
                "resolution_sha256": prepare()["resolution_sha256"],
                "signature": {
                    "algorithm": MODULE.SIGNATURE_ALGORITHM,
                    "key_id": MODULE.SIGNATURE_KEY_ID,
                    "value": "fixture",
                },
            },
            http_status=409,
            response={
                "error": "DISPATCH_ATTEMPT_ALREADY_RECEIVED",
                "message": "The original attempt was received.",
            },
        )

    with pytest.raises(MODULE.DispatchContractError, match="did not win"):
        MODULE.verify_dispatch_claim_receipt(
            claim_request,
            http_status=409,
            response={
                "error": "DISPATCH_ATTEMPT_ALREADY_RESOLVED",
                "message": "The original attempt was resolved.",
            },
        )


def test_queue_is_closed_and_recomputes_attempt_and_resolution_id() -> None:
    queue = {
        "schema": "openadapt.cloud-backup-dispatch-reconciliation-queue/v1",
        "candidates": [candidate()],
    }
    assert MODULE.validate_candidate_queue(queue) == [candidate()]
    queue["candidates"][0]["attempt_number"] = 2
    with pytest.raises(MODULE.DispatchContractError, match="attempt digest"):
        MODULE.validate_candidate_queue(queue)


def test_local_p256_fixture_signs_the_exact_canonical_resolution(tmp_path: Path) -> None:
    private_key = tmp_path / "fixture-private.pem"
    public_key = tmp_path / "fixture-public.pem"
    message = tmp_path / "resolution.json"
    signature_path = tmp_path / "resolution.sig"
    subprocess.run(
        [
            "openssl",
            "ecparam",
            "-name",
            "prime256v1",
            "-genkey",
            "-noout",
            "-out",
            str(private_key),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "ec", "-in", str(private_key), "-pubout", "-out", str(public_key)],
        check=True,
        capture_output=True,
    )
    prepared = prepare()
    canonical = base64.b64decode(prepared["canonical_resolution_b64"])
    message.write_bytes(canonical)
    subprocess.run(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-sign",
            str(private_key),
            "-out",
            str(signature_path),
            str(message),
        ],
        check=True,
        capture_output=True,
    )

    def signer(value: bytes) -> dict[str, str]:
        assert value == canonical
        return {
            "algorithm": MODULE.SIGNATURE_ALGORITHM,
            "key_id": MODULE.SIGNATURE_KEY_ID,
            "value": base64.b64encode(signature_path.read_bytes()).decode(),
        }

    envelope = MODULE.sign_prepared_resolution(prepared, signer)
    assert set(envelope) == {"schema", "resolution", "resolution_sha256", "signature"}
    verified = subprocess.run(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-verify",
            str(public_key),
            "-signature",
            str(signature_path),
            str(message),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0
    assert "Verified OK" in verified.stdout


def test_shared_hmac_signature_is_rejected() -> None:
    with pytest.raises(MODULE.DispatchContractError, match="algorithm is not exact"):
        MODULE.sign_prepared_resolution(
            prepare(),
            lambda _: {
                "algorithm": "HMAC-SHA256",
                "key_id": "shared",
                "value": "AA==",
            },
        )
