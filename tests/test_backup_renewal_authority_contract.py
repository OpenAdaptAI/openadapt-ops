from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "ops/backup/renewal-authority-contract.json"


def contract() -> dict[str, object]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def canonical_payload_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def signature_commitment(domain: str, value: object) -> bytes:
    return hashlib.sha256(domain.encode("utf-8") + canonical_payload_bytes(value)).digest()


def test_contract_is_unreachable_policy_until_cross_repo_activation() -> None:
    value = contract()
    assert value["schema_version"] == (
        "openadapt.production-backup-renewal-authority-contract/v1"
    )
    assert value["status"] == "contract-only-unreachable"
    assert value["repository"] == "OpenAdaptAI/openadapt-ops"
    assert value["repository_id"] == "1172011294"
    assert value["aws"] == {"account_id": "992382684924", "region": "us-east-1"}


def test_github_acceptance_never_substitutes_for_receiver_claim() -> None:
    dispatch = contract()["dispatch_precondition"]
    assert isinstance(dispatch, dict)
    assert dispatch["github_http_204_state"] == "GITHUB_ACCEPTED"
    assert dispatch["required_claim_state"] == "RECEIVED"
    assert "GITHUB_ACCEPTED" in dispatch["forbidden_pre_effect_states"]
    assert dispatch["minimum_not_received_observation_seconds"] == 300
    assert dispatch["github_created_at_skew_seconds"] == 60
    assert dispatch["successor_attempt_increment"] == 1


def test_lifecycle_signer_is_asymmetric_and_purpose_bound() -> None:
    signer = contract()["signer"]
    assert isinstance(signer, dict)
    assert signer["kms_key_alias"] == (
        "alias/openadapt-production-backup-lifecycle-authority"
    )
    assert signer["key_id"] == "ops-backup-lifecycle-kms-p256-2026-01"
    assert signer["algorithm"] == "AWS-KMS-ECDSA-SHA256"
    assert signer["key_spec"] == "ECC_NIST_P256"
    assert signer["key_usage"] == "SIGN_VERIFY"
    assert signer["signing_algorithm"] == "ECDSA_SHA_256"
    assert signer["message_type"] == "DIGEST"
    assert signer["commitment_scheme"] == (
        "SHA256_DOMAIN_NUL_CANONICAL_JSON_LF_V1"
    )
    assert signer["commitment_preimage"].endswith("exactly one LF byte")
    assert signer["commitment_output_bytes"] == 32
    assert "Prehashed(SHA-256)" in signer["offline_verification"]
    assert signer["mixed_message_types_permitted"] is False
    assert signer["signature_fields"] == [
        "algorithm",
        "commitment_scheme",
        "key_id",
        "message_type",
        "value",
    ]
    assert "commitment_scheme" in signer["registry_entry_fields"]
    assert signer["cloud_has_kms_sign"] is False
    assert signer["cloud_has_private_key"] is False
    assert signer["purposes"] == [
        "initial-readiness-v2",
        "renewal-effect-permit-v1",
        "renewal-readiness-v2",
        "renewal-terminal-v1",
        "schedule-lease-v2",
    ]
    assert "HMAC" not in json.dumps(signer)


def test_large_schedule_lease_uses_one_digest_commitment() -> None:
    signer = contract()["signer"]
    domain = contract()["objects"]["schedule_lease"]["domain_utf8_nul"]
    payload = {
        "activation_id": "act_" + "a" * 64,
        "readiness_receipt": {"evidence": "x" * 8192},
    }
    encoded = canonical_payload_bytes(payload)
    assert len(encoded) > 4096
    commitment = signature_commitment(domain, payload)
    assert len(commitment) == signer["commitment_output_bytes"] == 32
    assert signer["message_type"] == "DIGEST"
    assert signer["mixed_message_types_permitted"] is False


def test_signature_commitment_binds_domain_lf_purpose_and_payload() -> None:
    objects = contract()["objects"]
    domain = objects["schedule_lease"]["domain_utf8_nul"]
    other_domain = objects["renewal_readiness"]["domain_utf8_nul"]
    payload = {"lease_sequence": 1, "state": "ISSUED"}
    expected = signature_commitment(domain, payload)
    canonical_without_lf = canonical_payload_bytes(payload)[:-1]
    assert expected != hashlib.sha256(
        domain.encode("utf-8") + canonical_without_lf
    ).digest()
    assert expected != hashlib.sha256(
        domain.encode("utf-8") + canonical_without_lf + b"\n\n"
    ).digest()
    assert expected != signature_commitment(other_domain, payload)
    assert expected != signature_commitment(
        domain, {"lease_sequence": 2, "state": "ISSUED"}
    )


def test_raw_digest_and_mixed_mode_confusion_is_forbidden() -> None:
    signer = contract()["signer"]
    domain = contract()["objects"]["schedule_lease"]["domain_utf8_nul"]
    payload = {"nested": "x" * 8192}
    raw_message = domain.encode("utf-8") + canonical_payload_bytes(payload)
    commitment = signature_commitment(domain, payload)
    assert len(raw_message) > 4096
    assert len(commitment) == 32
    assert raw_message != commitment
    assert hashlib.sha256(commitment).digest() != commitment
    assert signer["message_type"] == "DIGEST"
    assert "commitment_scheme" in signer["registry_entry_fields"]
    assert signer["mixed_message_types_permitted"] is False


def test_cloud_outcome_signer_is_separate_asymmetric_and_verify_only_in_ops() -> None:
    signer = contract()["cloud_outcome_signer"]
    assert signer["owner"] == "OpenAdaptAI/openadapt-cloud"
    assert signer["kms_key_alias"] == (
        "alias/openadapt-cloud-production-backup-outcome"
    )
    assert signer["key_id"] == "cloud-backup-outcome-kms-p256-2026-01"
    assert signer["algorithm"] == "AWS-KMS-ECDSA-SHA256"
    assert signer["key_spec"] == "ECC_NIST_P256"
    assert signer["signing_algorithm"] == "ECDSA_SHA_256"
    assert signer["message_type"] == "DIGEST"
    assert signer["commitment_scheme"] == (
        "SHA256_DOMAIN_NUL_CANONICAL_JSON_LF_V1"
    )
    assert signer["signature_fields"] == [
        "algorithm",
        "commitment_scheme",
        "key_id",
        "message_type",
        "value",
    ]
    assert signer["registry_schema"] == (
        "openadapt.cloud-backup-outcome-signer-registry/v1"
    )
    assert signer["revocation_schema"] == (
        "openadapt.cloud-backup-outcome-key-revocations/v1"
    )
    assert signer["cloud_has_kms_sign"] is True
    assert signer["ops_has_kms_sign"] is False
    assert signer["ops_has_private_key"] is False
    assert "after the exact database CAS or retention effect" in signer[
        "issuance_rule"
    ]
    assert "HMAC" not in json.dumps(signer)


def test_cloud_outcome_purposes_have_distinct_exact_domains() -> None:
    value = contract()
    signer = value["cloud_outcome_signer"]
    expected = {
        "initial_readiness_ack": (
            "initial-readiness-ack-v3",
            "OpenAdapt Cloud database backup readiness ack v3\0",
        ),
        "renewal_terminal_result": (
            "renewal-terminal-result-v1",
            "OpenAdapt Cloud backup renewal terminal result v1\0",
        ),
        "callback_result": (
            "schedule-lease-application-result-v1",
            "OpenAdapt Cloud backup schedule lease application result v1\0",
        ),
    }
    domains = []
    purposes = []
    for object_name, (purpose, domain) in expected.items():
        item = value["objects"][object_name]
        assert item["signature_purpose"] == purpose
        assert item["domain_utf8_nul"] == domain
        assert domain.endswith("\0")
        purposes.append(purpose)
        domains.append(domain)
    assert sorted(purposes) == signer["purposes"]
    assert len(domains) == len(set(domains))
    payload = {"result_state": "APPLIED"}
    assert len({signature_commitment(domain, payload) for domain in domains}) == 3


def test_every_signed_object_has_a_distinct_nul_domain() -> None:
    objects = contract()["objects"]
    assert isinstance(objects, dict)
    signed = (
        "initial_readiness",
        "renewal_effect_permit",
        "renewal_readiness",
        "renewal_terminal",
        "schedule_lease",
    )
    domains = []
    for name in signed:
        item = objects[name]
        assert isinstance(item, dict)
        domain = item["domain_utf8_nul"]
        assert isinstance(domain, str)
        assert domain.endswith("\0")
        domains.append(domain)
        assert item["envelope_fields"] == sorted(item["envelope_fields"])
        assert item["payload_fields"] == sorted(item["payload_fields"])
    assert len(domains) == len(set(domains))


def test_initial_readiness_binds_authenticated_claim_not_only_dispatch() -> None:
    item = contract()["objects"]["initial_readiness"]
    assert item["schema"] == "openadapt.database-backup-readiness-receipt/v2"
    fields = set(item["payload_fields"])
    assert {
        "attempt_number",
        "claim_receipt_sha256",
        "claim_sha256",
        "dispatch_attempt_id_sha256",
        "dispatch_envelope_sha256",
        "revocation_state_sha256",
        "signer_registry_sha256",
    } <= fields


def test_initial_readiness_wire_bytes_are_retained_not_reserialized() -> None:
    value = contract()
    wire = value["wire_bytes"]
    assert wire["encoding"] == "UTF-8"
    assert wire["body"] == "canonical JSON followed by exactly one LF byte"
    assert wire["request_digest_header"] == "X-OpenAdapt-Request-SHA256"
    assert wire["response_digest_header"] == "X-OpenAdapt-Response-SHA256"
    assert "curl --data-binary" in wire["send_method"]
    assert "request BYTEA" in wire["cloud_atomic_storage"]
    assert "ack BYTEA" in wire["cloud_atomic_storage"]
    assert {
        "zero trailing line feed",
        "double trailing line feed",
        "carriage-return line feed",
        "noncanonical JSON",
    } <= set(wire["forbidden_request_encodings"])
    ack = value["objects"]["initial_readiness_ack"]
    assert ack["schema"] == "openadapt.database-backup-cloud-readiness-ack/v3"
    assert {
        "claim_receipt_sha256",
        "dispatch_attempt_id_sha256",
        "readiness_receipt_sha256",
        "readiness_request_bytes_sha256",
    } <= set(ack["payload_fields"])


def test_digest_relations_bind_full_claim_permit_result_and_pointer_objects() -> None:
    relations = contract()["digest_relations"]
    assert "full closed Cloud claim receipt" in relations["claim_receipt_sha256"]
    assert "full signed renewal effect permit envelope" in relations[
        "renewal_effect_permit_sha256"
    ]
    assert "full recovery result object" in relations["recovery_result_sha256"]
    assert "full immediately re-read prior current-issued pointer object" in relations[
        "prior_pointer_sha256"
    ]
    assert "schedule lease payload" in relations["lease_sha256"]
    assert "full signed schedule lease envelope" in relations[
        "schedule_lease_sha256"
    ]


def test_renewal_permit_is_signed_before_one_exact_recovery_effect() -> None:
    item = contract()["objects"]["renewal_effect_permit"]
    assert item["schema"] == "openadapt.database-backup-renewal-effect-permit/v1"
    assert item["validity_seconds"] == 900
    assert item["idempotency_prefix"] == "renewal_effect_"
    assert item["backup_object_prefix_template"] == (
        "renewals/<lease_event_id>/<recovery_point_stamp>"
    )
    fields = set(item["payload_fields"])
    assert {
        "claim_receipt_sha256",
        "claim_sha256",
        "continuation_assertion_sha256",
        "prior_lease_sha256",
        "prior_pointer_sha256",
        "requested_lease_sequence",
        "workflow_revision",
    } <= fields


def test_renewal_readiness_binds_new_recovery_and_prior_lease() -> None:
    item = contract()["objects"]["renewal_readiness"]
    assert item["schema"] == (
        "openadapt.database-backup-renewal-readiness-receipt/v2"
    )
    fields = set(item["payload_fields"])
    assert {
        "backup",
        "restore",
        "prior_lease_sha256",
        "requested_lease_sequence",
        "recovery_result_sha256",
        "renewal_effect_permit_sha256",
        "claim_receipt_sha256",
    } <= fields


def test_schedule_lease_binds_claim_readiness_pointer_and_callback() -> None:
    item = contract()["objects"]["schedule_lease"]
    assert item["schema"] == "openadapt.database-backup-schedule-lease/v2"
    fields = set(item["payload_fields"])
    assert {
        "callback_idempotency_key",
        "claim_receipt_sha256",
        "claim_sha256",
        "prior_lease_sha256",
        "prior_pointer_sha256",
        "readiness_receipt",
        "readiness_receipt_sha256",
        "recovery_result_sha256",
    } <= fields
    assert item["validity_seconds"] == 90 * 24 * 60 * 60
    assert item["renewal_due_seconds"] == 60 * 24 * 60 * 60
    assert "schedule_lease_sha256" not in item[
        "callback_idempotency_preimage_fields"
    ]


def test_non_verified_terminal_is_signed_closed_and_never_advances_lease() -> None:
    item = contract()["objects"]["renewal_terminal"]
    assert item["schema"] == "openadapt.database-backup-renewal-terminal/v1"
    assert item["outcomes"] == ["FAILED", "RECONCILIATION_REQUIRED"]
    assert item["validity_seconds"] == 900
    assert item["idempotency_prefix"] == "renewal_terminal_"
    assert "CURRENT_POINTER_CAS_CONFLICT" in item[
        "reconciliation_required_codes"
    ]
    fields = set(item["payload_fields"])
    assert {
        "claim_receipt_sha256",
        "effect_started",
        "callback_post_started",
        "operator_action_required",
        "uncertain_external_effect",
        "last_confirmed_stage",
    } <= fields
    result = contract()["objects"]["renewal_terminal_result"]
    assert result["fixed_values"]["result_state"] == "RETAINED"


def test_callback_wrapper_and_inner_application_are_closed_without_hash_cycle() -> None:
    item = contract()["objects"]["callback_application"]
    assert item["fields"] == ["application", "application_sha256", "schema"]
    assert len(item["application_fields"]) == 12
    assert "schema" not in item["application_fields"]
    assert item["idempotency_preimage_fields"] == [
        "activation_id",
        "dispatch_attempt_id_sha256",
        "lease_event_id",
        "lease_sequence",
        "prior_lease_sha256",
        "readiness_receipt_sha256",
    ]
    assert "schedule_lease_sha256" not in item["idempotency_preimage_fields"]


def test_reusable_recovery_accepts_only_signed_authority_and_digests() -> None:
    workflow = contract()["reusable_recovery_workflow"]
    assert isinstance(workflow, dict)
    assert workflow["trigger"] == "workflow_call only"
    assert workflow["exact_caller"] == (
        "OpenAdaptAI/openadapt-ops/.github/workflows/"
        "db-backup-activate.yml@refs/heads/main"
    )
    assert set(workflow["inputs"]) == {
        "claim_receipt_sha256",
        "claim_sha256",
        "dispatch_attempt_id_sha256",
        "renewal_effect_permit_b64",
        "renewal_effect_permit_sha256",
    }
    assert "arbitrary_s3_key" in workflow["forbidden_inputs"]
    assert "database_url" in workflow["forbidden_inputs"]
    assert set(workflow["outputs"]) == {
        "backup_evidence_sha256",
        "lease_event_id",
        "recovery_point_stamp",
        "recovery_result_sha256",
        "recovery_state",
        "requested_lease_sequence",
        "restore_evidence_sha256",
    }


def test_ledger_is_append_only_except_for_exact_pointer_cas() -> None:
    ledger = contract()["ledger"]
    assert isinstance(ledger, dict)
    assert "If-None-Match *" in ledger["immutable_write"]
    pointer = ledger["current_pointer_cas"]
    assert pointer["initial"] == "If-None-Match *"
    assert pointer["renewal"] == (
        "If-Match the immediately re-read current pointer ETag"
    )
    assert pointer["required_old_digest_field"] == "prior_pointer_sha256"
    assert "no overwrite" in pointer["conflict"]
    ordering = ledger["ordering"]
    assert ordering.index("validate authenticated RECEIVED claim") < ordering.index(
        "append the exact signed renewal effect permit"
    )
    assert ordering.index("append callback-started before POST") < ordering.index(
        "perform one callback POST"
    )
    assert ordering.index("CAS the current-issued pointer") < ordering.index(
        "append callback-started before POST"
    )
    current = contract()["objects"]["current_pointer"]
    assert current["schema"] == (
        "openadapt.database-backup-current-issued-schedule-lease-pointer/v1"
    )
    assert current["fixed_values"] == {"pointer_state": "ISSUED"}
    assert "callback_result_sha256" not in current["fields"]
    assert "never means" in current["authorization_rule"]


def test_callback_is_one_use_and_status_reconciled() -> None:
    callback = contract()["callback"]
    assert isinstance(callback, dict)
    assert callback["token_secret"] == "OPS_BACKUP_SCHEDULE_LEASE_TOKEN"
    assert callback["post_path"] == "/api/internal/backup/schedule-lease"
    assert callback["status_get_path"].startswith(
        "/api/internal/backup/schedule-lease/status?"
    )
    assert callback["terminal_post_path"].endswith("/terminal")
    assert "/terminal/status?" in callback["terminal_status_get_path"]
    readiness = callback["initial_readiness"]
    assert readiness["post_path"] == "/api/internal/backup/readiness"
    assert readiness["same_semantics_different_bytes_http"] == 409
    assert readiness["invalid_bytes_http"] == 400
    assert "exactly one LF" in readiness["request_body"]
    rules = " ".join(callback["rules"])
    assert "one POST" in rules
    assert "forbids every automatic second POST" in rules
    assert "RECONCILIATION_REQUIRED" in rules
    assert "no automatic terminal POST" in rules


def test_only_fully_verified_renewal_can_authorize_operation() -> None:
    semantics = contract()["terminal_semantics"]
    assert semantics["only_verified_authorizes_customer_operation"] is True
    assert "no blind retry" in semantics["RECONCILIATION_REQUIRED"]
    assert "Cloud active lease does not advance" in semantics["FAILED"]


def test_control_evidence_and_backup_retention_are_distinct() -> None:
    retention = contract()["retention"]
    assert retention["encrypted_backup_and_manifest_days"] == 90
    assert retention["control_evidence_days"] == 2557
    assert retention["control_evidence_delete_permission"] is False
    assert retention["current_pointer_bucket_versioning_required"] is True


def test_cross_repo_vectors_cover_loss_races_replay_and_signer_failure() -> None:
    vectors = set(contract()["required_cross_repository_vectors"])
    assert {
        "github-204-lost-before-claim-initial",
        "github-204-lost-before-claim-renewal",
        "initial-readiness-zero-lf-refused",
        "initial-readiness-double-lf-refused",
        "initial-readiness-semantic-same-byte-different-conflict",
        "initial-readiness-response-lost-status-byte-identical",
        "claim-wins-resolution-race",
        "resolution-wins-delayed-claim",
        "callback-response-lost-status-uncertain",
        "callback-started-forbids-second-post",
        "failed-terminal-retained-without-lease-advance",
        "reconciliation-terminal-retained-without-lease-advance",
        "pointer-cas-conflict",
        "revoked-lifecycle-key",
        "wrong-purpose-domain-signature",
        "schedule-lease-over-4096-digest-signed",
        "raw-message-mode-refused",
        "digest-rehash-mode-refused",
        "signature-lf-omitted-refused",
        "signature-lf-doubled-refused",
        "signature-payload-tamper-refused",
        "mixed-message-type-registry-refused",
        "cloud-outcome-before-cas-refused",
        "cloud-outcome-cross-purpose-signature-refused",
        "cloud-outcome-mixed-message-type-refused",
        "cloud-outcome-revoked-key-refused",
        "cloud-outcome-wrong-spki-refused",
    } <= vectors


def test_activation_dependencies_keep_live_authority_out_of_contract_pr() -> None:
    dependencies = " ".join(contract()["activation_dependencies"])
    assert "Cloud migration 0074" in dependencies
    assert "byte-identical fixed vectors" in dependencies
    assert "created only at final cutover" in dependencies
