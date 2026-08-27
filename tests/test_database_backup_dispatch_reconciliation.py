from __future__ import annotations

import base64
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
    "resolution_fada2d1a0ce8d86df505b2df27f89b49145e3ea9ea3798133d9a6fc1f108b4e4"
)


def ingress_payload() -> tuple[dict[str, object], dict[str, object]]:
    envelope = {
        "schema": "openadapt.database-backup-activation-request/v1",
        "request": {"activation_id": ACTIVATION_ID},
        "signature": {"algorithm": "fixture", "key_id": "fixture", "value": "fixture"},
    }
    digest = MODULE._sha256(MODULE.canonical_json(envelope))
    payload = {
        "schema": MODULE.INITIAL_SCHEMA,
        "dispatch_attempt_id_sha256": ATTEMPT_DIGEST,
        "dispatch_envelope_sha256": digest,
        "activation_request_b64": base64.b64encode(
            json.dumps(envelope, indent=2).encode()
        ).decode(),
    }
    return payload, envelope


def candidate() -> dict[str, object]:
    return {
        "resolution_id": RESOLUTION_ID,
        "dispatch_kind": "INITIAL_ACTIVATION",
        "activation_id": ACTIVATION_ID,
        "organization_id_sha256": "1" * 64,
        "dispatch_attempt_id_sha256": ATTEMPT_DIGEST,
        "dispatch_envelope_sha256": ENVELOPE_DIGEST,
        "lease_event_id": None,
        "prior_lease_sha256": None,
        "requested_lease_sequence": None,
        "last_error_code": "DISPATCH_NOT_CONFIRMED",
        "reconciliation_required_at": "2026-08-27T16:00:00Z",
    }


def prepare() -> dict[str, object]:
    return MODULE.prepare_not_received_resolution(
        candidate(),
        expected_attempt_sha256=ATTEMPT_DIGEST,
        expected_envelope_sha256=ENVELOPE_DIGEST,
        issued_at="2026-08-27T16:01:00Z",
        ingress_ledger_object=None,
        github_runs=[],
    )


def test_normal_ingress_retains_exact_attempt_envelope_and_run_identity() -> None:
    payload, _ = ingress_payload()
    retained = MODULE.retain_ingress(
        MODULE.INITIAL_EVENT,
        payload,
        github_repository="OpenAdaptAI/openadapt-ops",
        github_run_id="123456",
        github_run_attempt=1,
    )
    assert retained["dispatch_attempt_id_sha256"] == ATTEMPT_DIGEST
    assert retained["dispatch_envelope_sha256"] == payload["dispatch_envelope_sha256"]
    assert retained["github_run_id"] == "123456"
    assert MODULE.ingress_ledger_key(retained).endswith(f"/{ATTEMPT_DIGEST}.json")


def test_ingress_ledger_is_no_overwrite_idempotent_and_conflict_hard() -> None:
    payload, _ = ingress_payload()
    retained = MODULE.retain_ingress(
        MODULE.INITIAL_EVENT,
        payload,
        github_repository="OpenAdaptAI/openadapt-ops",
        github_run_id="123456",
        github_run_attempt=1,
    )
    assert MODULE.classify_ingress_write(retained, None) == "CREATE"
    assert (
        MODULE.classify_ingress_write(retained, MODULE.canonical_json(retained))
        == "IDEMPOTENT"
    )
    with pytest.raises(MODULE.DispatchContractError, match="conflicting bytes"):
        MODULE.classify_ingress_write(retained, b"{}")


def test_ingress_rejects_missing_or_mismatched_dispatch_identity() -> None:
    payload, _ = ingress_payload()
    payload["dispatch_envelope_sha256"] = "0" * 64
    with pytest.raises(MODULE.DispatchContractError, match="does not match"):
        MODULE.retain_ingress(
            MODULE.INITIAL_EVENT,
            payload,
            github_repository="OpenAdaptAI/openadapt-ops",
            github_run_id="123456",
            github_run_attempt=1,
        )


def test_shared_lost_before_github_vector_builds_exact_five_minute_resolution() -> None:
    prepared = prepare()
    resolution = prepared["resolution"]
    assert len(resolution) == 15
    assert resolution["resolution_id"] == RESOLUTION_ID
    assert resolution["resolution_state"] == "NOT_RECEIVED"
    assert resolution["dispatch_attempt_id_sha256"] == ATTEMPT_DIGEST
    assert resolution["dispatch_envelope_sha256"] == ENVELOPE_DIGEST
    assert resolution["issued_at"] == "2026-08-27T16:01:00Z"
    assert resolution["expires_at"] == "2026-08-27T16:06:00Z"
    canonical = base64.b64decode(prepared["canonical_resolution_b64"])
    assert MODULE._sha256(canonical) == prepared["resolution_sha256"]


def test_no_resolution_is_prepared_when_absence_is_uncertain() -> None:
    kwargs = {
        "expected_attempt_sha256": ATTEMPT_DIGEST,
        "expected_envelope_sha256": ENVELOPE_DIGEST,
        "issued_at": "2026-08-27T16:01:00Z",
    }
    with pytest.raises(MODULE.DispatchContractError, match="ingress ledger"):
        MODULE.prepare_not_received_resolution(
            candidate(), ingress_ledger_object=b"present", github_runs=[], **kwargs
        )
    with pytest.raises(MODULE.DispatchContractError, match="can match"):
        MODULE.prepare_not_received_resolution(
            candidate(),
            ingress_ledger_object=None,
            github_runs=[
                {
                    "id": 9,
                    "event": "repository_dispatch",
                    "created_at": "2026-08-27T15:59:59Z",
                }
            ],
            **kwargs,
        )


def test_local_p256_fixture_signs_the_exact_canonical_resolution(
    tmp_path: Path,
) -> None:
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
            lambda _: {"algorithm": "HMAC-SHA256", "key_id": "shared", "value": "AA=="},
        )
