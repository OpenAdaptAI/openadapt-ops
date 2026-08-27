#!/usr/bin/env python3
"""Retain Cloud dispatch identity and sign exact NOT_RECEIVED resolutions."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

INITIAL_EVENT = "verified_first_payment"
INITIAL_SCHEMA = "openadapt.database-backup-activation-dispatch/v1"
RENEWAL_EVENT = "database_backup_renewal"
RENEWAL_SCHEMA = "openadapt.database-backup-renewal-dispatch/v1"
ATTEMPT_SCHEMA = "openadapt.database-backup-dispatch-attempt/v1"
ATTEMPT_AUDIENCE = "OpenAdaptAI/openadapt-ops:database-backup-dispatch"
ATTEMPT_ISSUER = "openadapt-cloud"
INITIAL_ATTEMPT_KEY_ID = "cloud-payment-signal-hmac-2026-01"
RENEWAL_ATTEMPT_KEY_ID = "cloud-backup-continuation-hmac-2026-01"
RESOLUTION_SCHEMA = "openadapt.database-backup-dispatch-resolution/v1"
STATUS_SCHEMA = "openadapt.cloud-backup-dispatch-reconciliation-status/v1"
CLAIM_SCHEMA = "openadapt.database-backup-dispatch-claim/v1"
CLAIM_RECEIPT_SCHEMA = "openadapt.cloud-backup-dispatch-claim-receipt/v1"
REISSUE_SCHEMA = "openadapt.cloud-backup-dispatch-reissue/v1"
RESOLUTION_AUDIENCE = "openadapt-cloud:database-backup-dispatch-resolution"
OFFER_CONTRACT = "openadapt-cloud-managed-browser-v1"
SIGNATURE_ALGORITHM = "AWS-KMS-ECDSA-SHA256"
SIGNATURE_KEY_ID = "ops-backup-dispatch-resolution-kms-p256-2026-01"
KMS_ACCOUNT_ID = "992382684924"
KMS_REGION = "us-east-1"
KMS_ALIAS = "alias/openadapt-production-backup-dispatch-resolution"
KMS_KEY_SPEC = "ECC_NIST_P256"
KMS_KEY_USAGE = "SIGN_VERIFY"
KMS_SIGNING_ALGORITHM = "ECDSA_SHA_256"
INVENTORY_SCHEMA = "openadapt.ops-backup-github-run-inventory/v2"
RUN_LOCATOR_SCHEMA = "openadapt.ops-backup-dispatch-run-locator/v1"
INVENTORY_PRINCIPAL_LOGIN = "github-actions[bot]"
INVENTORY_PRINCIPAL_ID = "41898282"
INVENTORY_REPOSITORY = "OpenAdaptAI/openadapt-ops"
INVENTORY_REPOSITORY_ID = "1172011294"
INVENTORY_OWNER_ID = "132681217"
INVENTORY_WORKFLOW_PATH = ".github/workflows/db-backup-activate.yml"
INVENTORY_EVENT = "repository_dispatch"
INVENTORY_REF = "refs/heads/main"
MINIMUM_OBSERVATION_SECONDS = 300
GITHUB_CREATED_AT_SKEW_SECONDS = 60
INVENTORY_PAGE_SIZE = 100
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ACTIVATION_ID = re.compile(r"^act_[0-9a-f]{64}$")
LEASE_EVENT_ID = re.compile(r"^lease_[0-9a-f]{64}$")
RESOLUTION_ID = re.compile(r"^resolution_[0-9a-f]{64}$")
CANDIDATE_FIELDS = {
    "resolution_id",
    "dispatch_kind",
    "activation_id",
    "attempt_number",
    "organization_id_sha256",
    "dispatch_attempt_id_sha256",
    "dispatch_envelope_sha256",
    "lease_event_id",
    "prior_lease_sha256",
    "requested_lease_sequence",
    "last_error_code",
    "dispatch_attempted_at",
    "reconciliation_required_at",
}
INGRESS_FIELDS = {
    "schema",
    "event_name",
    "dispatch_kind",
    "activation_id",
    "attempt_number",
    "lease_event_id",
    "requested_lease_sequence",
    "resolution_id",
    "dispatch_attempt_id_sha256",
    "dispatch_attempt_sha256",
    "dispatch_envelope_sha256",
    "github_repository",
    "github_repository_id",
    "github_run_id",
    "github_run_attempt",
    "received_at",
    "workflow_revision",
}
STATUS_FIELDS = {
    "schema",
    "resolution_id",
    "dispatch_kind",
    "reissue_state",
    "replacement_payload_sha256",
    "replacement_dispatch_envelope_sha256",
    "attempt_count",
    "consumed_at",
    "delivered_at",
}
RUN_LOCATOR_FIELDS = {
    "schema",
    "event_name",
    "github_repository",
    "github_repository_id",
    "github_run_id",
    "github_run_attempt",
    "workflow_revision",
    "dispatch_attempt_id_sha256",
    "dispatch_envelope_sha256",
    "ingress_ledger_key",
    "ingress_ledger_sha256",
}


def validate_candidate_queue(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    if set(value) != {"schema", "candidates"} or value.get("schema") != (
        "openadapt.cloud-backup-dispatch-reconciliation-queue/v1"
    ):
        raise DispatchContractError("the Cloud reconciliation queue is not closed")
    candidates = value.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 50:
        raise DispatchContractError("the Cloud reconciliation candidate list is malformed")
    result: list[dict[str, Any]] = []
    seen_attempts: set[str] = set()
    seen_resolutions: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping) or set(candidate) != CANDIDATE_FIELDS:
            raise DispatchContractError("a Cloud reconciliation candidate is not closed")
        activation_id = candidate.get("activation_id")
        attempt_number = candidate.get("attempt_number")
        kind = candidate.get("dispatch_kind")
        lease_event_id = candidate.get("lease_event_id")
        prior_lease = candidate.get("prior_lease_sha256")
        sequence = candidate.get("requested_lease_sequence")
        if (
            not isinstance(activation_id, str)
            or ACTIVATION_ID.fullmatch(activation_id) is None
            or not isinstance(attempt_number, int)
            or isinstance(attempt_number, bool)
            or attempt_number < 1
        ):
            raise DispatchContractError("a Cloud candidate attempt identity is malformed")
        for name in (
            "organization_id_sha256",
            "dispatch_attempt_id_sha256",
            "dispatch_envelope_sha256",
        ):
            digest = candidate.get(name)
            if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
                raise DispatchContractError("a Cloud candidate digest is malformed")
        if kind == "INITIAL_ACTIVATION":
            if any(item is not None for item in (lease_event_id, prior_lease, sequence)):
                raise DispatchContractError("an initial Cloud candidate has renewal identity")
            attempt_identity = {
                "activation_id": activation_id,
                "attempt_number": attempt_number,
                "dispatch_envelope_sha256": candidate["dispatch_envelope_sha256"],
                "dispatch_kind": kind,
            }
        elif kind == "LEASE_RENEWAL":
            if (
                not isinstance(lease_event_id, str)
                or LEASE_EVENT_ID.fullmatch(lease_event_id) is None
                or not isinstance(prior_lease, str)
                or HEX64.fullmatch(prior_lease) is None
                or not isinstance(sequence, int)
                or isinstance(sequence, bool)
                or sequence < 1
            ):
                raise DispatchContractError("a renewal Cloud candidate is incomplete")
            attempt_identity = {
                "attempt_number": attempt_number,
                "dispatch_envelope_sha256": candidate["dispatch_envelope_sha256"],
                "dispatch_kind": kind,
                "lease_event_id": lease_event_id,
            }
        else:
            raise DispatchContractError("a Cloud candidate kind is not authorized")
        if _sha256(canonical_json(attempt_identity)) != candidate.get(
            "dispatch_attempt_id_sha256"
        ):
            raise DispatchContractError("a Cloud candidate attempt digest does not match")
        expected_resolution_id = resolution_id(candidate)
        if candidate.get("resolution_id") != expected_resolution_id:
            raise DispatchContractError("a Cloud candidate resolution ID does not match")
        dispatch_attempted_at = candidate.get("dispatch_attempted_at")
        reconciliation_required_at = candidate.get("reconciliation_required_at")
        if not isinstance(dispatch_attempted_at, str) or not isinstance(
            reconciliation_required_at, str
        ):
            raise DispatchContractError("a Cloud candidate dispatch time is missing")
        attempted = _timestamp(dispatch_attempted_at)
        reconciliation_required = _timestamp(reconciliation_required_at)
        if attempted > reconciliation_required:
            raise DispatchContractError(
                "a Cloud candidate reconciliation precedes its dispatch attempt"
            )
        last_error = candidate.get("last_error_code")
        if last_error is not None and (
            not isinstance(last_error, str)
            or not last_error
            or len(last_error.encode("utf-8")) > 128
        ):
            raise DispatchContractError("a Cloud candidate error code is malformed")
        attempt_digest = candidate["dispatch_attempt_id_sha256"]
        if attempt_digest in seen_attempts or expected_resolution_id in seen_resolutions:
            raise DispatchContractError("the Cloud candidate queue repeats an identity")
        seen_attempts.add(attempt_digest)
        seen_resolutions.add(expected_resolution_id)
        result.append(dict(candidate))
    return result


class DispatchContractError(ValueError):
    """A dispatch identity or absence proof is incomplete or inconsistent."""


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _parse_canonical_object(raw: bytes, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DispatchContractError(f"the {label} is not valid JSON") from exc
    if not isinstance(value, Mapping) or canonical_json(value) != raw:
        raise DispatchContractError(f"the {label} is not exact canonical JSON")
    return value


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _decode_envelope(value: str) -> Mapping[str, Any]:
    try:
        raw = base64.b64decode(value, validate=True)
        envelope = json.loads(raw)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DispatchContractError(
            "the signed envelope is not valid base64 JSON"
        ) from exc
    if not isinstance(envelope, Mapping):
        raise DispatchContractError("the signed envelope is not an object")
    return envelope


def _verify_dispatch_attempt(
    encoded_attempt: str,
    *,
    signing_key: str,
    activation_id: str,
    attempt_number: int,
    attempt_digest: str,
    envelope_digest: str,
    kind: str,
    lease_event_id: str | None,
) -> str:
    if len(signing_key.encode("utf-8")) < 32:
        raise DispatchContractError("the Cloud dispatch signing key is not configured")
    envelope = _decode_envelope(encoded_attempt)
    if set(envelope) != {"schema", "attempt", "attempt_sha256", "signature"}:
        raise DispatchContractError("the signed dispatch attempt is not closed")
    attempt = envelope.get("attempt")
    signature = envelope.get("signature")
    if not isinstance(attempt, Mapping) or set(attempt) != {
        "activation_id",
        "attempt_number",
        "audience",
        "dispatch_attempt_id_sha256",
        "dispatch_envelope_sha256",
        "dispatch_kind",
        "issuer",
        "lease_event_id",
        "offer_contract",
    }:
        raise DispatchContractError("the signed dispatch attempt identity is not closed")
    expected_attempt = {
        "activation_id": activation_id,
        "attempt_number": attempt_number,
        "audience": ATTEMPT_AUDIENCE,
        "dispatch_attempt_id_sha256": attempt_digest,
        "dispatch_envelope_sha256": envelope_digest,
        "dispatch_kind": kind,
        "issuer": ATTEMPT_ISSUER,
        "lease_event_id": lease_event_id,
        "offer_contract": OFFER_CONTRACT,
    }
    if dict(attempt) != expected_attempt:
        raise DispatchContractError("the signed dispatch attempt identity does not match")
    encoded = canonical_json(attempt)
    attempt_sha256 = _sha256(encoded)
    if envelope.get("schema") != ATTEMPT_SCHEMA or envelope.get(
        "attempt_sha256"
    ) != attempt_sha256:
        raise DispatchContractError("the signed dispatch attempt digest does not match")
    expected_key_id = (
        INITIAL_ATTEMPT_KEY_ID if kind == "INITIAL_ACTIVATION" else RENEWAL_ATTEMPT_KEY_ID
    )
    if not isinstance(signature, Mapping) or set(signature) != {
        "algorithm",
        "key_id",
        "value",
    }:
        raise DispatchContractError("the dispatch attempt signature is not closed")
    actual_signature = signature.get("value")
    expected_signature = hmac.new(
        signing_key.encode("utf-8"), encoded, hashlib.sha256
    ).hexdigest()
    if (
        signature.get("algorithm") != "HMAC-SHA256"
        or signature.get("key_id") != expected_key_id
        or not isinstance(actual_signature, str)
        or HEX64.fullmatch(actual_signature) is None
        or not hmac.compare_digest(actual_signature, expected_signature)
    ):
        raise DispatchContractError("the dispatch attempt signature is invalid")
    return attempt_sha256


def retain_ingress(
    event_name: str,
    payload: Mapping[str, Any],
    *,
    github_repository: str,
    github_repository_id: str,
    github_run_id: str,
    github_run_attempt: int,
    received_at: str,
    workflow_revision: str,
    dispatch_signing_key: str,
) -> dict[str, Any]:
    if (
        github_repository != INVENTORY_REPOSITORY
        or github_repository_id != INVENTORY_REPOSITORY_ID
    ):
        raise DispatchContractError("the GitHub repository identity is not exact")
    if (
        re.fullmatch(r"[1-9][0-9]{0,19}", github_run_id) is None
        or not isinstance(github_run_attempt, int)
        or isinstance(github_run_attempt, bool)
        or github_run_attempt < 1
    ):
        raise DispatchContractError("the GitHub run identity is malformed")
    normalized_received_at = _iso(_timestamp(received_at))
    if re.fullmatch(r"[0-9a-f]{40}", workflow_revision) is None:
        raise DispatchContractError("the workflow revision is not an exact commit")
    if event_name == INITIAL_EVENT:
        expected_fields = {
            "schema",
            "attempt_number",
            "dispatch_attempt_id_sha256",
            "dispatch_envelope_sha256",
            "dispatch_attempt_b64",
            "activation_request_b64",
        }
        if set(payload) != expected_fields or payload.get("schema") != INITIAL_SCHEMA:
            raise DispatchContractError("the initial dispatch payload is not exact")
        envelope_b64 = payload["activation_request_b64"]
        kind = "INITIAL_ACTIVATION"
        identity_parent = "request"
        identity_name = "activation_id"
        lease_event_id = None
    elif event_name == RENEWAL_EVENT:
        expected_fields = {
            "schema",
            "attempt_number",
            "lease_event_id",
            "dispatch_attempt_id_sha256",
            "dispatch_envelope_sha256",
            "dispatch_attempt_b64",
            "continuation_assertion_b64",
        }
        if set(payload) != expected_fields or payload.get("schema") != RENEWAL_SCHEMA:
            raise DispatchContractError("the renewal dispatch payload is not exact")
        envelope_b64 = payload["continuation_assertion_b64"]
        kind = "LEASE_RENEWAL"
        identity_parent = "assertion"
        identity_name = "lease_event_id"
        lease_event_id = payload["lease_event_id"]
        if (
            not isinstance(lease_event_id, str)
            or LEASE_EVENT_ID.fullmatch(lease_event_id) is None
        ):
            raise DispatchContractError("the renewal lease event identity is malformed")
    else:
        raise DispatchContractError("the dispatch event type is not authorized")
    attempt_digest = payload.get("dispatch_attempt_id_sha256")
    attempt_number = payload.get("attempt_number")
    envelope_digest = payload.get("dispatch_envelope_sha256")
    if not isinstance(attempt_digest, str) or HEX64.fullmatch(attempt_digest) is None:
        raise DispatchContractError("the dispatch attempt digest is malformed")
    if (
        not isinstance(attempt_number, int)
        or isinstance(attempt_number, bool)
        or attempt_number < 1
    ):
        raise DispatchContractError("the dispatch attempt number is malformed")
    if not isinstance(envelope_digest, str) or HEX64.fullmatch(envelope_digest) is None:
        raise DispatchContractError("the dispatch envelope digest is malformed")
    if not isinstance(envelope_b64, str):
        raise DispatchContractError("the signed envelope is missing")
    envelope = _decode_envelope(envelope_b64)
    if _sha256(canonical_json(envelope)) != envelope_digest:
        raise DispatchContractError("the dispatch envelope digest does not match")
    identity = envelope.get(identity_parent)
    if not isinstance(identity, Mapping):
        raise DispatchContractError("the signed envelope identity is missing")
    embedded_identity = identity.get(identity_name)
    if kind == "INITIAL_ACTIVATION":
        if (
            not isinstance(embedded_identity, str)
            or ACTIVATION_ID.fullmatch(embedded_identity) is None
        ):
            raise DispatchContractError("the activation identity is malformed")
        activation_id = embedded_identity
        requested_lease_sequence = None
    else:
        if embedded_identity != lease_event_id:
            raise DispatchContractError("the lease event identity does not match")
        activation_id = identity.get("activation_id")
        if (
            not isinstance(activation_id, str)
            or ACTIVATION_ID.fullmatch(activation_id) is None
        ):
            raise DispatchContractError("the renewal activation identity is malformed")
        requested_lease_sequence = identity.get("requested_lease_sequence")
        if (
            not isinstance(requested_lease_sequence, int)
            or isinstance(requested_lease_sequence, bool)
            or requested_lease_sequence < 1
        ):
            raise DispatchContractError("the renewal lease sequence is malformed")
    attempt_identity = (
        {
            "activation_id": activation_id,
            "attempt_number": attempt_number,
            "dispatch_envelope_sha256": envelope_digest,
            "dispatch_kind": kind,
        }
        if kind == "INITIAL_ACTIVATION"
        else {
            "attempt_number": attempt_number,
            "dispatch_envelope_sha256": envelope_digest,
            "dispatch_kind": kind,
            "lease_event_id": lease_event_id,
        }
    )
    if _sha256(canonical_json(attempt_identity)) != attempt_digest:
        raise DispatchContractError("the dispatch attempt digest does not match")
    dispatch_attempt_b64 = payload.get("dispatch_attempt_b64")
    if not isinstance(dispatch_attempt_b64, str):
        raise DispatchContractError("the signed dispatch attempt is missing")
    dispatch_attempt_sha256 = _verify_dispatch_attempt(
        dispatch_attempt_b64,
        signing_key=dispatch_signing_key,
        activation_id=activation_id,
        attempt_number=attempt_number,
        attempt_digest=attempt_digest,
        envelope_digest=envelope_digest,
        kind=kind,
        lease_event_id=lease_event_id,
    )
    status_resolution_id = resolution_id(
        {
            "activation_id": activation_id,
            "attempt_number": attempt_number,
            "dispatch_attempt_id_sha256": attempt_digest,
            "dispatch_envelope_sha256": envelope_digest,
            "dispatch_kind": kind,
            "lease_event_id": lease_event_id,
            "requested_lease_sequence": requested_lease_sequence,
        }
    )
    return {
        "schema": "openadapt.ops-backup-dispatch-ingress/v1",
        "event_name": event_name,
        "dispatch_kind": kind,
        "activation_id": activation_id,
        "attempt_number": attempt_number,
        "lease_event_id": lease_event_id,
        "requested_lease_sequence": requested_lease_sequence,
        "resolution_id": status_resolution_id,
        "dispatch_attempt_id_sha256": attempt_digest,
        "dispatch_attempt_sha256": dispatch_attempt_sha256,
        "dispatch_envelope_sha256": envelope_digest,
        "github_repository": github_repository,
        "github_repository_id": github_repository_id,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "received_at": normalized_received_at,
        "workflow_revision": workflow_revision,
    }


def ingress_ledger_key(ingress: Mapping[str, Any]) -> str:
    digest = ingress.get("dispatch_attempt_id_sha256")
    if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
        raise DispatchContractError("the retained attempt digest is malformed")
    return f"dispatch-ingress/sha256/{digest[:2]}/{digest}.json"


def classify_ingress_write(
    ingress: Mapping[str, Any], existing_bytes: bytes | None
) -> str:
    """Return CREATE or IDEMPOTENT; reject an occupied key with other bytes."""

    expected = canonical_json(ingress)
    if existing_bytes is None:
        return "CREATE"
    if existing_bytes == expected:
        return "IDEMPOTENT"
    raise DispatchContractError("the dispatch ingress ledger key has conflicting bytes")


def build_dispatch_run_locator(ingress: Mapping[str, Any]) -> dict[str, Any]:
    if set(ingress) != INGRESS_FIELDS or ingress.get("schema") != (
        "openadapt.ops-backup-dispatch-ingress/v1"
    ):
        raise DispatchContractError("the retained dispatch ingress is not exact")
    build_dispatch_claim(ingress)
    ingress_bytes = canonical_json(ingress)
    return {
        "schema": RUN_LOCATOR_SCHEMA,
        "event_name": ingress["event_name"],
        "github_repository": ingress["github_repository"],
        "github_repository_id": ingress["github_repository_id"],
        "github_run_id": ingress["github_run_id"],
        "github_run_attempt": ingress["github_run_attempt"],
        "workflow_revision": ingress["workflow_revision"],
        "dispatch_attempt_id_sha256": ingress["dispatch_attempt_id_sha256"],
        "dispatch_envelope_sha256": ingress["dispatch_envelope_sha256"],
        "ingress_ledger_key": ingress_ledger_key(ingress),
        "ingress_ledger_sha256": _sha256(ingress_bytes),
    }


def run_locator_key(run_id: str, run_attempt: int) -> str:
    if (
        re.fullmatch(r"[1-9][0-9]{0,19}", run_id) is None
        or not isinstance(run_attempt, int)
        or isinstance(run_attempt, bool)
        or run_attempt < 1
    ):
        raise DispatchContractError("the GitHub run locator identity is malformed")
    return (
        "dispatch-run-locators/github/"
        f"{INVENTORY_REPOSITORY_ID}/{run_id}/{run_attempt}.json"
    )


def resolution_id(candidate: Mapping[str, Any]) -> str:
    identity = {
        "activation_id": candidate.get("activation_id"),
        "attempt_number": candidate.get("attempt_number"),
        "dispatch_attempt_id_sha256": candidate.get("dispatch_attempt_id_sha256"),
        "dispatch_envelope_sha256": candidate.get("dispatch_envelope_sha256"),
        "dispatch_kind": candidate.get("dispatch_kind"),
        "lease_event_id": candidate.get("lease_event_id"),
        "requested_lease_sequence": candidate.get("requested_lease_sequence"),
    }
    return "resolution_" + _sha256(canonical_json(identity))


def assert_cloud_attempt_unresolved(
    candidate: Mapping[str, Any], *, http_status: int, response: Mapping[str, Any]
) -> None:
    """Fail if Cloud retained a NOT_RECEIVED winner or returned uncertainty."""

    expected_resolution_id = resolution_id(candidate)
    if candidate.get("resolution_id") != expected_resolution_id:
        raise DispatchContractError("the candidate resolution identity does not match")
    if http_status == 404:
        if set(response) != {"error", "message"} or response.get(
            "error"
        ) != "ACTIVATION_NOT_FOUND" or (
            not isinstance(response.get("message"), str)
            or not response["message"]
            or len(response["message"].encode("utf-8")) > 1024
        ):
            raise DispatchContractError("the Cloud unresolved response is not exact")
        return
    if http_status != 200:
        raise DispatchContractError("the Cloud resolution state is uncertain")
    if set(response) != STATUS_FIELDS or response.get("schema") != STATUS_SCHEMA:
        raise DispatchContractError("the Cloud resolution status is not closed")
    if (
        response.get("resolution_id") != expected_resolution_id
        or response.get("dispatch_kind") != candidate.get("dispatch_kind")
        or response.get("reissue_state")
        not in {
            "QUEUED",
            "SENDING",
            "DELIVERED",
            "RECONCILIATION_REQUIRED",
            "SUPERSEDED",
        }
    ):
        raise DispatchContractError("the Cloud resolution status identity does not match")
    for name in (
        "replacement_payload_sha256",
        "replacement_dispatch_envelope_sha256",
    ):
        value = response.get(name)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise DispatchContractError("the Cloud replacement digest is malformed")
    attempt_count = response.get("attempt_count")
    if response["reissue_state"] == "SUPERSEDED":
        if attempt_count is not None:
            raise DispatchContractError("the superseded attempt count is not null")
    elif (
        not isinstance(attempt_count, int)
        or isinstance(attempt_count, bool)
        or attempt_count < 0
    ):
        raise DispatchContractError("the Cloud replacement attempt count is malformed")
    _timestamp(str(response.get("consumed_at")))
    delivered_at = response.get("delivered_at")
    if delivered_at is not None:
        _timestamp(str(delivered_at))
    raise DispatchContractError("the dispatch attempt was already resolved NOT_RECEIVED")


def build_dispatch_claim(ingress: Mapping[str, Any]) -> dict[str, Any]:
    if set(ingress) != INGRESS_FIELDS or ingress.get("schema") != (
        "openadapt.ops-backup-dispatch-ingress/v1"
    ):
        raise DispatchContractError("the retained dispatch ingress is not exact")
    attempt_number = ingress.get("attempt_number")
    run_attempt = ingress.get("github_run_attempt")
    run_id = ingress.get("github_run_id")
    revision = ingress.get("workflow_revision")
    if (
        not isinstance(attempt_number, int)
        or isinstance(attempt_number, bool)
        or attempt_number < 1
        or not isinstance(run_attempt, int)
        or isinstance(run_attempt, bool)
        or run_attempt < 1
        or not isinstance(run_id, str)
        or re.fullmatch(r"[1-9][0-9]{0,19}", run_id) is None
        or not isinstance(revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", revision) is None
    ):
        raise DispatchContractError("the retained claim run identity is malformed")
    for name in ("dispatch_attempt_id_sha256", "dispatch_envelope_sha256"):
        value = ingress.get(name)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise DispatchContractError("the retained claim digest is malformed")
    if (
        ingress.get("github_repository") != INVENTORY_REPOSITORY
        or ingress.get("github_repository_id") != INVENTORY_REPOSITORY_ID
    ):
        raise DispatchContractError("the retained claim repository is not exact")
    claim = {
        "attempt_number": attempt_number,
        "dispatch_attempt_id_sha256": ingress["dispatch_attempt_id_sha256"],
        "dispatch_envelope_sha256": ingress["dispatch_envelope_sha256"],
        "github_repository": INVENTORY_REPOSITORY,
        "github_run_attempt": run_attempt,
        "github_run_id": run_id,
        "workflow_revision": revision,
    }
    envelope = {"schema": CLAIM_SCHEMA, "claim": claim}
    return {
        "envelope": envelope,
        "claim_sha256": _sha256(canonical_json(claim)),
        "idempotency_key": "claim_" + _sha256(canonical_json(claim)),
    }


def verify_dispatch_claim_receipt(
    claim_request: Mapping[str, Any], *, http_status: int, response: Mapping[str, Any]
) -> dict[str, Any]:
    if set(claim_request) != {"envelope", "claim_sha256", "idempotency_key"}:
        raise DispatchContractError("the dispatch claim request is not exact")
    envelope = claim_request.get("envelope")
    if not isinstance(envelope, Mapping) or set(envelope) != {"schema", "claim"}:
        raise DispatchContractError("the dispatch claim envelope is not exact")
    claim = envelope.get("claim")
    if not isinstance(claim, Mapping):
        raise DispatchContractError("the dispatch claim identity is missing")
    claim_digest = _sha256(canonical_json(claim))
    if (
        envelope.get("schema") != CLAIM_SCHEMA
        or claim_request.get("claim_sha256") != claim_digest
        or claim_request.get("idempotency_key") != "claim_" + claim_digest
    ):
        raise DispatchContractError("the dispatch claim request digest does not match")
    if http_status != 200:
        raise DispatchContractError("the dispatch claim did not win the atomic state change")
    if set(response) != {
        "schema",
        "dispatch_attempt_id_sha256",
        "attempt_state",
        "claim_sha256",
        "received_at",
    } or response.get("schema") != CLAIM_RECEIPT_SCHEMA:
        raise DispatchContractError("the dispatch claim receipt is not closed")
    if (
        response.get("dispatch_attempt_id_sha256")
        != claim.get("dispatch_attempt_id_sha256")
        or response.get("attempt_state") != "RECEIVED"
        or response.get("claim_sha256") != claim_digest
    ):
        raise DispatchContractError("the dispatch claim receipt identity does not match")
    _timestamp(str(response.get("received_at")))
    return {
        "claim_sha256": claim_digest,
        "claim_receipt_sha256": _sha256(canonical_json(response)),
        "dispatch_attempt_id_sha256": response["dispatch_attempt_id_sha256"],
    }


def verify_resolution_reissue_receipt(
    resolution_envelope: Mapping[str, Any],
    *,
    http_status: int,
    response: Mapping[str, Any],
) -> dict[str, Any]:
    resolution = resolution_envelope.get("resolution")
    if (
        set(resolution_envelope)
        != {"schema", "resolution", "resolution_sha256", "signature"}
        or resolution_envelope.get("schema") != RESOLUTION_SCHEMA
        or not isinstance(resolution, Mapping)
    ):
        raise DispatchContractError("the signed NOT_RECEIVED envelope is not exact")
    if http_status != 200:
        raise DispatchContractError("the NOT_RECEIVED resolution lost the atomic state change")
    if set(response) != {
        "schema",
        "resolution_id",
        "dispatch_kind",
        "reissue_state",
        "replacement_payload_sha256",
        "replacement_dispatch_envelope_sha256",
    } or response.get("schema") != REISSUE_SCHEMA:
        raise DispatchContractError("the Cloud reissue receipt is not closed")
    if (
        response.get("resolution_id") != resolution.get("resolution_id")
        or response.get("dispatch_kind") != resolution.get("dispatch_kind")
        or response.get("reissue_state") != "QUEUED"
    ):
        raise DispatchContractError("the Cloud reissue receipt identity does not match")
    for name in (
        "replacement_payload_sha256",
        "replacement_dispatch_envelope_sha256",
    ):
        value = response.get(name)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise DispatchContractError("the Cloud reissue digest is malformed")
    return {
        "resolution_id": response["resolution_id"],
        "reissue_receipt_sha256": _sha256(canonical_json(response)),
        "replacement_dispatch_envelope_sha256": response[
            "replacement_dispatch_envelope_sha256"
        ],
    }


def verify_retained_resolution_status(
    resolution_envelope: Mapping[str, Any],
    reissue_response: Mapping[str, Any],
    *,
    http_status: int,
    status_response: Mapping[str, Any],
) -> dict[str, Any]:
    resolution = resolution_envelope.get("resolution")
    if not isinstance(resolution, Mapping):
        raise DispatchContractError("the retained resolution is missing")
    if http_status != 200 or set(status_response) != STATUS_FIELDS or status_response.get(
        "schema"
    ) != STATUS_SCHEMA:
        raise DispatchContractError("the retained Cloud resolution status is not closed")
    if (
        status_response.get("resolution_id") != resolution.get("resolution_id")
        or status_response.get("dispatch_kind") != resolution.get("dispatch_kind")
        or status_response.get("replacement_payload_sha256")
        != reissue_response.get("replacement_payload_sha256")
        or status_response.get("replacement_dispatch_envelope_sha256")
        != reissue_response.get("replacement_dispatch_envelope_sha256")
        or status_response.get("reissue_state")
        not in {
            "QUEUED",
            "SENDING",
            "DELIVERED",
            "RECONCILIATION_REQUIRED",
            "SUPERSEDED",
        }
    ):
        raise DispatchContractError("the retained Cloud resolution status does not match")
    for name in (
        "replacement_payload_sha256",
        "replacement_dispatch_envelope_sha256",
    ):
        value = status_response.get(name)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise DispatchContractError("the retained Cloud replacement digest is malformed")
    attempt_count = status_response.get("attempt_count")
    if status_response["reissue_state"] == "SUPERSEDED":
        if attempt_count is not None:
            raise DispatchContractError("the retained superseded count is not null")
    elif (
        not isinstance(attempt_count, int)
        or isinstance(attempt_count, bool)
        or attempt_count < 0
    ):
        raise DispatchContractError("the retained replacement attempt count is malformed")
    _timestamp(str(status_response.get("consumed_at")))
    if status_response.get("delivered_at") is not None:
        _timestamp(str(status_response["delivered_at"]))
    return {
        "resolution_id": status_response["resolution_id"],
        "status_sha256": _sha256(canonical_json(status_response)),
        "reissue_state": status_response["reissue_state"],
    }


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DispatchContractError("issued_at is not an ISO-8601 time") from exc
    if result.tzinfo is None:
        raise DispatchContractError("issued_at has no timezone")
    return result.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _page_digest(value: Mapping[str, Any]) -> str:
    return _sha256(canonical_json(value))


def observe_github_run_inventory(
    *,
    dispatch_attempted_at: str,
    observed_at: str,
    repository: Mapping[str, Any],
    workflow: Mapping[str, Any],
    principal: Mapping[str, Any],
    fetch_page: Callable[[int, int, str, str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    """Fetch every run in the bounded window and prove a stable high-water mark."""

    attempted = _timestamp(dispatch_attempted_at)
    observed = _timestamp(observed_at)
    if (observed - attempted).total_seconds() < MINIMUM_OBSERVATION_SECONDS:
        raise DispatchContractError("the GitHub observation window is too short")
    if repository != {
        "full_name": INVENTORY_REPOSITORY,
        "id": INVENTORY_REPOSITORY_ID,
    }:
        raise DispatchContractError("the GitHub inventory repository is not exact")
    if set(workflow) != {"id", "path", "state"} or (
        not isinstance(workflow.get("id"), str)
        or not workflow["id"].isdigit()
        or workflow.get("path") != INVENTORY_WORKFLOW_PATH
        or workflow.get("state") != "active"
    ):
        raise DispatchContractError("the GitHub inventory workflow is not exact")
    if set(principal) != {
        "app_id",
        "app_slug",
        "installation_id",
        "target_id",
        "target_type",
    } or (
        not isinstance(principal.get("app_id"), str)
        or not principal["app_id"].isdigit()
        or not isinstance(principal.get("installation_id"), str)
        or not principal["installation_id"].isdigit()
        or not isinstance(principal.get("app_slug"), str)
        or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?", principal["app_slug"])
        is None
        or principal.get("target_id") != INVENTORY_OWNER_ID
        or principal.get("target_type") != "Organization"
    ):
        raise DispatchContractError("the GitHub inventory principal is not exact")
    range_start = _iso(
        attempted - timedelta(seconds=GITHUB_CREATED_AT_SKEW_SECONDS)
    )
    range_end = _iso(observed)
    pages: list[dict[str, Any]] = []
    runs: list[Mapping[str, Any]] = []
    total_count: int | None = None
    page = 1
    while True:
        response = fetch_page(
            page,
            INVENTORY_PAGE_SIZE,
            INVENTORY_EVENT,
            range_start,
            range_end,
        )
        if not isinstance(response, Mapping) or set(response) != {
            "total_count",
            "workflow_runs",
        }:
            raise DispatchContractError("a GitHub run inventory page is not exact")
        count = response.get("total_count")
        values = response.get("workflow_runs")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise DispatchContractError("the GitHub run total is malformed")
        if not isinstance(values, list) or len(values) > INVENTORY_PAGE_SIZE:
            raise DispatchContractError("a GitHub run page is malformed")
        if total_count is None:
            total_count = count
        elif count != total_count:
            raise DispatchContractError("the GitHub run inventory changed while paging")
        page_runs: list[Mapping[str, Any]] = []
        for run in values:
            if not isinstance(run, Mapping) or set(run) != {
                "id",
                "run_attempt",
                "event",
                "head_branch",
                "head_sha",
                "workflow_id",
                "created_at",
                "run_started_at",
                "status",
                "conclusion",
            }:
                raise DispatchContractError("a GitHub run identity is ambiguous")
            if (
                not isinstance(run.get("id"), str)
                or not run["id"].isdigit()
                or not isinstance(run.get("run_attempt"), int)
                or isinstance(run.get("run_attempt"), bool)
                or run["run_attempt"] < 1
                or run.get("event") != INVENTORY_EVENT
                or run.get("head_branch") != "main"
                or run.get("workflow_id") != workflow["id"]
                or not isinstance(run.get("head_sha"), str)
                or re.fullmatch(r"[0-9a-f]{40}", run["head_sha"]) is None
                or run.get("status")
                not in {
                    "queued",
                    "in_progress",
                    "completed",
                    "waiting",
                    "requested",
                    "pending",
                }
                or (
                    run.get("conclusion") is not None
                    and run.get("conclusion")
                    not in {
                        "action_required",
                        "cancelled",
                        "failure",
                        "neutral",
                        "skipped",
                        "stale",
                        "startup_failure",
                        "success",
                        "timed_out",
                    }
                )
            ):
                raise DispatchContractError("a GitHub run does not have exact identity")
            created = _timestamp(str(run.get("created_at")))
            started_at = run.get("run_started_at")
            if started_at is not None:
                _timestamp(str(started_at))
            if created < _timestamp(range_start) or created > _timestamp(range_end):
                raise DispatchContractError("a GitHub run is outside the query range")
            page_runs.append(run)
        pages.append(
            {
                "page": page,
                "per_page": INVENTORY_PAGE_SIZE,
                "response_sha256": _page_digest(response),
                "run_ids": [run["id"] for run in page_runs],
            }
        )
        runs.extend(page_runs)
        if len(runs) >= count:
            if len(runs) != count:
                raise DispatchContractError("the GitHub run inventory exceeds its total")
            break
        if len(values) != INVENTORY_PAGE_SIZE:
            raise DispatchContractError("GitHub pagination ended before the total")
        page += 1
        if page > 10:
            raise DispatchContractError("the GitHub run inventory exceeds 1000 results")
    run_ids = [run["id"] for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise DispatchContractError("the GitHub run inventory repeats a run")
    final_page_one = fetch_page(
        1, INVENTORY_PAGE_SIZE, INVENTORY_EVENT, range_start, range_end
    )
    if not isinstance(final_page_one, Mapping) or set(final_page_one) != {
        "total_count",
        "workflow_runs",
    }:
        raise DispatchContractError("the final GitHub high-water page is not exact")
    if final_page_one.get("total_count") != total_count:
        raise DispatchContractError("the GitHub run high-water total changed")
    initial_high_water = run_ids[0] if run_ids else None
    final_values = final_page_one.get("workflow_runs")
    if not isinstance(final_values, list):
        raise DispatchContractError("the final GitHub high-water runs are malformed")
    final_high_water = final_values[0].get("id") if final_values else None
    if final_high_water != initial_high_water or _page_digest(final_page_one) != pages[0][
        "response_sha256"
    ]:
        raise DispatchContractError("the GitHub run high-water mark changed")
    evidence_without_digest: dict[str, Any] = {
        "schema": INVENTORY_SCHEMA,
        "repository": INVENTORY_REPOSITORY,
        "repository_id": INVENTORY_REPOSITORY_ID,
        "workflow_path": INVENTORY_WORKFLOW_PATH,
        "workflow_id": workflow["id"],
        "event": INVENTORY_EVENT,
        "ref": INVENTORY_REF,
        "authenticated_principal": dict(principal),
        "dispatch_attempted_at": _iso(attempted),
        "range_start": range_start,
        "range_end": range_end,
        "observation_completed_at": _iso(observed),
        "eventual_consistency_delay_seconds": MINIMUM_OBSERVATION_SECONDS,
        "github_created_at_skew_seconds": GITHUB_CREATED_AT_SKEW_SECONDS,
        "pages": pages,
        "total_count": total_count,
        "initial_high_water_run_id": initial_high_water,
        "final_high_water_run_id": final_high_water,
        "final_page_one_sha256": _page_digest(final_page_one),
        "runs": [dict(run) for run in runs],
    }
    return {
        **evidence_without_digest,
        "evidence_sha256": _sha256(canonical_json(evidence_without_digest)),
    }


def _github_json(token: str, path: str) -> Mapping[str, Any]:
    if len(token.encode("utf-8")) < 32 or any(character.isspace() for character in token):
        raise DispatchContractError("the GitHub inventory credential is not configured")
    request = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "openadapt-ops-backup-control",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise DispatchContractError("the GitHub inventory query did not succeed")
            value = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DispatchContractError("the GitHub inventory query failed closed") from exc
    if not isinstance(value, Mapping):
        raise DispatchContractError("the GitHub inventory response is not an object")
    return value


def fetch_authoritative_github_inventory(
    *,
    dispatch_attempted_at: str,
    observed_at: str,
    token: str,
    expected_app_id: str,
    expected_app_slug: str,
    expected_installation_id: str,
    fetch_json: Callable[[str, str], Mapping[str, Any]] = _github_json,
) -> dict[str, Any]:
    """Query GitHub directly; no caller-supplied run list can prove absence."""

    installation = fetch_json(token, "/installation")
    principal = {
        "app_id": str(installation.get("app_id", "")),
        "app_slug": installation.get("app_slug"),
        "installation_id": str(installation.get("id", "")),
        "target_id": str(installation.get("target_id", "")),
        "target_type": installation.get("target_type"),
    }
    expected_principal = {
        "app_id": expected_app_id,
        "app_slug": expected_app_slug,
        "installation_id": expected_installation_id,
        "target_id": INVENTORY_OWNER_ID,
        "target_type": "Organization",
    }
    if principal != expected_principal:
        raise DispatchContractError("the GitHub inventory token identity does not match")
    repository_response = fetch_json(token, f"/repos/{INVENTORY_REPOSITORY}")
    repository = {
        "full_name": repository_response.get("full_name"),
        "id": str(repository_response.get("id", "")),
    }
    workflow_response = fetch_json(
        token,
        f"/repos/{INVENTORY_REPOSITORY}/actions/workflows/"
        + urllib.parse.quote(INVENTORY_WORKFLOW_PATH, safe=""),
    )
    workflow = {
        "id": str(workflow_response.get("id", "")),
        "path": workflow_response.get("path"),
        "state": workflow_response.get("state"),
    }

    def fetch_page(
        page: int,
        per_page: int,
        event: str,
        range_start: str,
        range_end: str,
    ) -> Mapping[str, Any]:
        query = urllib.parse.urlencode(
            {
                "branch": "main",
                "created": f"{range_start}..{range_end}",
                "event": event,
                "exclude_pull_requests": "true",
                "page": str(page),
                "per_page": str(per_page),
            }
        )
        raw = fetch_json(
            token,
            f"/repos/{INVENTORY_REPOSITORY}/actions/workflows/{workflow['id']}/runs?{query}",
        )
        raw_runs = raw.get("workflow_runs")
        if not isinstance(raw_runs, list):
            raise DispatchContractError("the GitHub run inventory page is malformed")
        normalized: list[dict[str, Any]] = []
        for raw_run in raw_runs:
            if not isinstance(raw_run, Mapping):
                raise DispatchContractError("a GitHub run identity is ambiguous")
            normalized.append(
                {
                    "id": str(raw_run.get("id", "")),
                    "run_attempt": raw_run.get("run_attempt"),
                    "event": raw_run.get("event"),
                    "head_branch": raw_run.get("head_branch"),
                    "head_sha": raw_run.get("head_sha"),
                    "workflow_id": str(raw_run.get("workflow_id", "")),
                    "created_at": raw_run.get("created_at"),
                    "run_started_at": raw_run.get("run_started_at"),
                    "status": raw_run.get("status"),
                    "conclusion": raw_run.get("conclusion"),
                }
            )
        return {
            "total_count": raw.get("total_count"),
            "workflow_runs": normalized,
        }

    return observe_github_run_inventory(
        dispatch_attempted_at=dispatch_attempted_at,
        observed_at=observed_at,
        repository=repository,
        workflow=workflow,
        principal=principal,
        fetch_page=fetch_page,
    )


def account_github_run_inventory(
    inventory: Mapping[str, Any],
    *,
    fetch_object: Callable[[str], bytes],
) -> dict[str, Any]:
    unsigned = dict(inventory)
    evidence_digest = unsigned.pop("evidence_sha256", None)
    if evidence_digest != _sha256(canonical_json(unsigned)):
        raise DispatchContractError("the GitHub inventory digest does not match")
    if "run_accounts" in unsigned:
        raise DispatchContractError("the GitHub inventory was already accounted")
    runs = unsigned.get("runs")
    if not isinstance(runs, list):
        raise DispatchContractError("the GitHub inventory run list is malformed")
    accounts: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, Mapping):
            raise DispatchContractError("a GitHub run cannot be accounted")
        run_id = run.get("id")
        run_attempt = run.get("run_attempt")
        if not isinstance(run_id, str) or not isinstance(run_attempt, int):
            raise DispatchContractError("a GitHub run locator identity is malformed")
        locator_key = run_locator_key(run_id, run_attempt)
        locator_bytes = fetch_object(locator_key)
        locator = _parse_canonical_object(locator_bytes, "GitHub run locator")
        if set(locator) != RUN_LOCATOR_FIELDS or locator.get("schema") != (
            RUN_LOCATOR_SCHEMA
        ):
            raise DispatchContractError("a GitHub run locator is not closed")
        if (
            locator.get("github_repository") != INVENTORY_REPOSITORY
            or locator.get("github_repository_id") != INVENTORY_REPOSITORY_ID
            or locator.get("github_run_id") != run_id
            or locator.get("github_run_attempt") != run_attempt
            or locator.get("workflow_revision") != run.get("head_sha")
            or locator.get("event_name") not in {INITIAL_EVENT, RENEWAL_EVENT}
        ):
            raise DispatchContractError("a GitHub run locator identity does not match")
        for field in (
            "dispatch_attempt_id_sha256",
            "dispatch_envelope_sha256",
            "ingress_ledger_sha256",
        ):
            digest = locator.get(field)
            if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
                raise DispatchContractError("a GitHub run locator digest is malformed")
        expected_ingress_key = (
            "dispatch-ingress/sha256/"
            f"{locator['dispatch_attempt_id_sha256'][:2]}/"
            f"{locator['dispatch_attempt_id_sha256']}.json"
        )
        if locator.get("ingress_ledger_key") != expected_ingress_key:
            raise DispatchContractError("a GitHub run locator ledger key is not exact")
        ingress_bytes = fetch_object(expected_ingress_key)
        if _sha256(ingress_bytes) != locator["ingress_ledger_sha256"]:
            raise DispatchContractError("a retained ingress ledger digest does not match")
        ingress = _parse_canonical_object(ingress_bytes, "retained ingress ledger")
        if build_dispatch_run_locator(ingress) != locator:
            raise DispatchContractError("a GitHub run locator is not backed by its ingress")
        accounts.append(
            {
                "github_run_id": run_id,
                "github_run_attempt": run_attempt,
                "locator_key": locator_key,
                "locator_sha256": _sha256(locator_bytes),
                "dispatch_attempt_id_sha256": locator[
                    "dispatch_attempt_id_sha256"
                ],
                "dispatch_envelope_sha256": locator["dispatch_envelope_sha256"],
                "ingress_ledger_key": expected_ingress_key,
                "ingress_ledger_sha256": locator["ingress_ledger_sha256"],
            }
        )
    accounted = {**unsigned, "run_accounts": accounts}
    return {
        **accounted,
        "evidence_sha256": _sha256(canonical_json(accounted)),
    }


def fetch_s3_object(
    key: str,
    *,
    bucket: str,
    expected_owner: str,
) -> bytes:
    if not bucket or expected_owner != KMS_ACCOUNT_ID or not key:
        raise DispatchContractError("the S3 backup-control authority is not exact")
    with tempfile.TemporaryDirectory(prefix="openadapt-backup-control-") as directory:
        target = Path(directory) / "object.json"
        result = subprocess.run(
            [
                "aws",
                "s3api",
                "get-object",
                "--bucket",
                bucket,
                "--key",
                key,
                "--expected-bucket-owner",
                expected_owner,
                str(target),
            ],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0 or not target.is_file():
            raise DispatchContractError(
                "an authoritative S3 run-locator object is absent or unreadable"
            )
        return target.read_bytes()


def assert_s3_object_absent(
    key: str,
    *,
    bucket: str,
    expected_owner: str,
) -> None:
    if not bucket or expected_owner != KMS_ACCOUNT_ID or not key:
        raise DispatchContractError("the S3 backup-control authority is not exact")
    result = subprocess.run(
        [
            "aws",
            "s3api",
            "head-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--expected-bucket-owner",
            expected_owner,
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        raise DispatchContractError("the dispatch attempt exists in the ingress ledger")
    error = result.stderr.decode("utf-8", errors="replace")
    if "An error occurred (404)" not in error and "(NoSuchKey)" not in error:
        raise DispatchContractError("the S3 ingress-ledger state is uncertain")


def _assert_github_run_absence(
    evidence: Mapping[str, Any],
    *,
    dispatch_attempted_at: str,
    issued_at: str,
    missing_attempt_sha256: str,
) -> None:
    expected_fields = {
        "schema", "repository", "repository_id", "workflow_path", "workflow_id",
        "event", "ref", "authenticated_principal", "dispatch_attempted_at",
        "range_start", "range_end", "observation_completed_at",
        "eventual_consistency_delay_seconds", "github_created_at_skew_seconds",
        "pages", "total_count",
        "initial_high_water_run_id", "final_high_water_run_id",
        "final_page_one_sha256", "runs", "run_accounts", "evidence_sha256",
    }
    if set(evidence) != expected_fields or evidence.get("schema") != INVENTORY_SCHEMA:
        raise DispatchContractError("the GitHub run inventory evidence is not exact")
    unsigned = dict(evidence)
    digest = unsigned.pop("evidence_sha256")
    if digest != _sha256(canonical_json(unsigned)):
        raise DispatchContractError("the GitHub run inventory digest does not match")
    attempted = _timestamp(dispatch_attempted_at)
    issued = _timestamp(issued_at)
    expected_start = attempted - timedelta(seconds=GITHUB_CREATED_AT_SKEW_SECONDS)
    if (
        evidence.get("repository") != INVENTORY_REPOSITORY
        or evidence.get("repository_id") != INVENTORY_REPOSITORY_ID
        or evidence.get("workflow_path") != INVENTORY_WORKFLOW_PATH
        or not isinstance(evidence.get("workflow_id"), str)
        or not evidence["workflow_id"].isdigit()
        or evidence.get("event") != INVENTORY_EVENT
        or evidence.get("ref") != INVENTORY_REF
        or _timestamp(str(evidence.get("dispatch_attempted_at"))) != attempted
        or _timestamp(str(evidence.get("range_start"))) != expected_start
    ):
        raise DispatchContractError("the GitHub run inventory scope is not exact")
    principal = evidence.get("authenticated_principal")
    if not isinstance(principal, Mapping) or set(principal) != {
        "app_id",
        "app_slug",
        "installation_id",
        "target_id",
        "target_type",
    } or (
        not isinstance(principal.get("app_id"), str)
        or not principal["app_id"].isdigit()
        or not isinstance(principal.get("installation_id"), str)
        or not principal["installation_id"].isdigit()
        or not isinstance(principal.get("app_slug"), str)
        or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?", principal["app_slug"])
        is None
        or principal.get("target_id") != INVENTORY_OWNER_ID
        or principal.get("target_type") != "Organization"
    ):
        raise DispatchContractError("the GitHub inventory principal is not exact")
    if (
        _timestamp(str(evidence.get("range_end"))) != issued
        or _timestamp(str(evidence.get("observation_completed_at"))) != issued
    ):
        raise DispatchContractError("the inventory high-water time is not the issue time")
    if (issued - attempted).total_seconds() < MINIMUM_OBSERVATION_SECONDS:
        raise DispatchContractError("the inventory observation window is too short")
    if (
        evidence.get("eventual_consistency_delay_seconds")
        != MINIMUM_OBSERVATION_SECONDS
        or evidence.get("github_created_at_skew_seconds")
        != GITHUB_CREATED_AT_SKEW_SECONDS
    ):
        raise DispatchContractError("the inventory minimum observation is not exact")
    runs = evidence.get("runs")
    if not isinstance(runs, list) or evidence.get("total_count") != len(runs):
        raise DispatchContractError("the GitHub run inventory is incomplete")
    accounts = evidence.get("run_accounts")
    if not isinstance(accounts, list) or len(accounts) != len(runs):
        raise DispatchContractError("the GitHub run inventory is not fully accounted")
    account_fields = {
        "github_run_id",
        "github_run_attempt",
        "locator_key",
        "locator_sha256",
        "dispatch_attempt_id_sha256",
        "dispatch_envelope_sha256",
        "ingress_ledger_key",
        "ingress_ledger_sha256",
    }
    for run, account in zip(runs, accounts, strict=True):
        if not isinstance(run, Mapping) or not isinstance(account, Mapping) or set(
            account
        ) != account_fields:
            raise DispatchContractError("a GitHub run account is not closed")
        if (
            account.get("github_run_id") != run.get("id")
            or account.get("github_run_attempt") != run.get("run_attempt")
            or account.get("locator_key")
            != run_locator_key(str(run.get("id")), run.get("run_attempt"))
        ):
            raise DispatchContractError("a GitHub run account identity does not match")
        for field in (
            "locator_sha256",
            "dispatch_attempt_id_sha256",
            "dispatch_envelope_sha256",
            "ingress_ledger_sha256",
        ):
            value = account.get(field)
            if not isinstance(value, str) or HEX64.fullmatch(value) is None:
                raise DispatchContractError("a GitHub run account digest is malformed")
        expected_ingress_key = (
            "dispatch-ingress/sha256/"
            f"{account['dispatch_attempt_id_sha256'][:2]}/"
            f"{account['dispatch_attempt_id_sha256']}.json"
        )
        if account.get("ingress_ledger_key") != expected_ingress_key:
            raise DispatchContractError("a GitHub run account ledger key is not exact")
        if account["dispatch_attempt_id_sha256"] == missing_attempt_sha256:
            raise DispatchContractError(
                "the missing dispatch attempt has an accounted GitHub run"
            )
    empty_response = {"total_count": 0, "workflow_runs": []}
    empty_digest = _page_digest(empty_response)
    if evidence.get("total_count") == 0 and (
        evidence.get("pages")
        != [
            {
                "page": 1,
                "per_page": INVENTORY_PAGE_SIZE,
                "response_sha256": empty_digest,
                "run_ids": [],
            }
        ]
        or evidence.get("initial_high_water_run_id") is not None
        or evidence.get("final_high_water_run_id") is not None
        or evidence.get("final_page_one_sha256") != empty_digest
    ):
        raise DispatchContractError("the empty GitHub run inventory is not complete")


def prepare_not_received_resolution(
    candidate: Mapping[str, Any],
    *,
    expected_attempt_sha256: str,
    expected_envelope_sha256: str,
    issued_at: str,
    ingress_ledger_object: bytes | None,
    github_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    if set(candidate) != CANDIDATE_FIELDS:
        raise DispatchContractError("the reconciliation candidate is not closed")
    for field in (
        "organization_id_sha256",
        "dispatch_attempt_id_sha256",
        "dispatch_envelope_sha256",
    ):
        value = candidate.get(field)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise DispatchContractError(f"the candidate {field} is malformed")
    if candidate["dispatch_attempt_id_sha256"] != expected_attempt_sha256:
        raise DispatchContractError("the candidate dispatch attempt does not match")
    if candidate["dispatch_envelope_sha256"] != expected_envelope_sha256:
        raise DispatchContractError("the candidate dispatch envelope does not match")
    if ingress_ledger_object is not None:
        raise DispatchContractError("the dispatch attempt exists in the ingress ledger")
    dispatch_attempted_at = candidate.get("dispatch_attempted_at")
    reconciliation_required_at = candidate.get("reconciliation_required_at")
    if not isinstance(dispatch_attempted_at, str) or not isinstance(
        reconciliation_required_at, str
    ):
        raise DispatchContractError("the candidate dispatch times are missing")
    if _timestamp(dispatch_attempted_at) > _timestamp(reconciliation_required_at):
        raise DispatchContractError(
            "the candidate reconciliation precedes its dispatch attempt"
        )
    _assert_github_run_absence(
        github_inventory,
        dispatch_attempted_at=dispatch_attempted_at,
        issued_at=issued_at,
        missing_attempt_sha256=expected_attempt_sha256,
    )
    activation_id = candidate.get("activation_id")
    if (
        not isinstance(activation_id, str)
        or ACTIVATION_ID.fullmatch(activation_id) is None
    ):
        raise DispatchContractError("the candidate activation identity is malformed")
    kind = candidate.get("dispatch_kind")
    attempt_number = candidate.get("attempt_number")
    if (
        not isinstance(attempt_number, int)
        or isinstance(attempt_number, bool)
        or attempt_number < 1
    ):
        raise DispatchContractError("the candidate attempt number is malformed")
    lease_event_id = candidate.get("lease_event_id")
    prior_lease = candidate.get("prior_lease_sha256")
    sequence = candidate.get("requested_lease_sequence")
    if kind == "INITIAL_ACTIVATION":
        if any(value is not None for value in (lease_event_id, prior_lease, sequence)):
            raise DispatchContractError("the initial candidate has renewal identity")
    elif kind == "LEASE_RENEWAL":
        if (
            not isinstance(lease_event_id, str)
            or LEASE_EVENT_ID.fullmatch(lease_event_id) is None
            or not isinstance(prior_lease, str)
            or HEX64.fullmatch(prior_lease) is None
            or not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or sequence < 1
        ):
            raise DispatchContractError("the renewal candidate identity is incomplete")
    else:
        raise DispatchContractError("the candidate dispatch kind is not authorized")
    attempt_identity = (
        {
            "activation_id": activation_id,
            "attempt_number": attempt_number,
            "dispatch_envelope_sha256": candidate["dispatch_envelope_sha256"],
            "dispatch_kind": kind,
        }
        if kind == "INITIAL_ACTIVATION"
        else {
            "attempt_number": attempt_number,
            "dispatch_envelope_sha256": candidate["dispatch_envelope_sha256"],
            "dispatch_kind": kind,
            "lease_event_id": lease_event_id,
        }
    )
    if _sha256(canonical_json(attempt_identity)) != candidate[
        "dispatch_attempt_id_sha256"
    ]:
        raise DispatchContractError("the candidate dispatch attempt digest does not match")
    expected_resolution_id = resolution_id(candidate)
    if candidate.get("resolution_id") != expected_resolution_id:
        raise DispatchContractError("the candidate resolution identity does not match")
    issued = _timestamp(issued_at)
    expires = issued + timedelta(minutes=5)
    resolution = {
        "activation_id": activation_id,
        "attempt_number": attempt_number,
        "audience": RESOLUTION_AUDIENCE,
        "dispatch_attempt_id_sha256": candidate["dispatch_attempt_id_sha256"],
        "dispatch_envelope_sha256": candidate["dispatch_envelope_sha256"],
        "dispatch_kind": kind,
        "expires_at": _iso(expires),
        "issued_at": _iso(issued),
        "issuer": "openadapt-ops",
        "lease_event_id": lease_event_id,
        "offer_contract": OFFER_CONTRACT,
        "organization_id_sha256": candidate["organization_id_sha256"],
        "prior_lease_sha256": prior_lease,
        "requested_lease_sequence": sequence,
        "resolution_id": expected_resolution_id,
        "resolution_state": "NOT_RECEIVED",
    }
    encoded = canonical_json(resolution)
    return {
        "schema": "openadapt.ops-backup-dispatch-resolution-signing-request/v1",
        "resolution": resolution,
        "resolution_sha256": _sha256(encoded),
        "canonical_resolution_b64": base64.b64encode(encoded).decode("ascii"),
        "absence_evidence": dict(github_inventory),
        "absence_evidence_sha256": github_inventory["evidence_sha256"],
    }


def sign_prepared_resolution(
    prepared: Mapping[str, Any],
    signer: Callable[[bytes], Mapping[str, Any]],
) -> dict[str, Any]:
    if set(prepared) != {
        "schema",
        "resolution",
        "resolution_sha256",
        "canonical_resolution_b64",
        "absence_evidence",
        "absence_evidence_sha256",
    } or prepared.get("schema") != (
        "openadapt.ops-backup-dispatch-resolution-signing-request/v1"
    ):
        raise DispatchContractError("the resolution signing request is not exact")
    resolution = prepared.get("resolution")
    if not isinstance(resolution, Mapping):
        raise DispatchContractError("the prepared resolution is missing")
    encoded = canonical_json(resolution)
    if _sha256(encoded) != prepared.get("resolution_sha256"):
        raise DispatchContractError("the prepared resolution digest does not match")
    if base64.b64encode(encoded).decode("ascii") != prepared.get(
        "canonical_resolution_b64"
    ):
        raise DispatchContractError("the prepared canonical bytes do not match")
    evidence = prepared.get("absence_evidence")
    if not isinstance(evidence, Mapping) or evidence.get("evidence_sha256") != prepared.get(
        "absence_evidence_sha256"
    ):
        raise DispatchContractError("the prepared absence evidence does not match")
    signature = signer(encoded)
    if not isinstance(signature, Mapping) or set(signature) != {
        "algorithm",
        "key_id",
        "value",
    }:
        raise DispatchContractError("the asymmetric signer result is not exact")
    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        raise DispatchContractError("the resolution signature algorithm is not exact")
    if signature.get("key_id") != SIGNATURE_KEY_ID:
        raise DispatchContractError(
            "the resolution signature key identity is not exact"
        )
    value = signature.get("value")
    if not isinstance(value, str):
        raise DispatchContractError("the resolution signature value is missing")
    try:
        der = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise DispatchContractError(
            "the resolution signature is not base64 DER"
        ) from exc
    if not der or der[0] != 0x30:
        raise DispatchContractError("the resolution signature is not a DER sequence")
    return {
        "schema": RESOLUTION_SCHEMA,
        "resolution": dict(resolution),
        "resolution_sha256": prepared["resolution_sha256"],
        "signature": dict(signature),
    }


def sign_kms_response(
    prepared: Mapping[str, Any],
    kms_response: Mapping[str, Any],
    *,
    expected_key_arn: str,
) -> dict[str, Any]:
    if set(kms_response) != {"KeyId", "Signature", "SigningAlgorithm"}:
        raise DispatchContractError("the AWS KMS signing response is not closed")
    if (
        not re.fullmatch(
            rf"arn:aws:kms:{KMS_REGION}:{KMS_ACCOUNT_ID}:key/[0-9a-f-]{{36}}",
            expected_key_arn,
        )
        or kms_response.get("KeyId") != expected_key_arn
        or kms_response.get("SigningAlgorithm") != KMS_SIGNING_ALGORITHM
        or not isinstance(kms_response.get("Signature"), str)
    ):
        raise DispatchContractError("the AWS KMS signing identity is not exact")
    return sign_prepared_resolution(
        prepared,
        lambda _: {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": SIGNATURE_KEY_ID,
            "value": kms_response["Signature"],
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingress = subparsers.add_parser("retain-ingress")
    ingress.add_argument("--event-name", required=True)
    ingress.add_argument("--payload", type=Path, required=True)
    ingress.add_argument("--output", type=Path, required=True)
    ingress.add_argument("--github-repository", required=True)
    ingress.add_argument("--github-repository-id", required=True)
    ingress.add_argument("--github-run-id", required=True)
    ingress.add_argument("--github-run-attempt", type=int, required=True)
    ingress.add_argument("--received-at", required=True)
    ingress.add_argument("--workflow-revision", required=True)
    ingress.add_argument("--dispatch-signing-key-env", required=True)

    locator = subparsers.add_parser("build-run-locator")
    locator.add_argument("--ingress", type=Path, required=True)
    locator.add_argument("--output", type=Path, required=True)

    resolve = subparsers.add_parser("prepare-not-received")
    resolve.add_argument("--candidate", type=Path, required=True)
    resolve.add_argument("--expected-attempt-sha256", required=True)
    resolve.add_argument("--expected-envelope-sha256", required=True)
    resolve.add_argument("--github-token-env", required=True)
    resolve.add_argument("--expected-app-id", required=True)
    resolve.add_argument("--expected-app-slug", required=True)
    resolve.add_argument("--expected-installation-id", required=True)
    resolve.add_argument("--s3-bucket", required=True)
    resolve.add_argument("--s3-expected-owner", required=True)
    resolve.add_argument("--output", type=Path, required=True)

    claim = subparsers.add_parser("build-claim")
    claim.add_argument("--ingress", type=Path, required=True)
    claim.add_argument("--output", type=Path, required=True)

    claim_receipt = subparsers.add_parser("verify-claim-receipt")
    claim_receipt.add_argument("--claim-request", type=Path, required=True)
    claim_receipt.add_argument("--response", type=Path, required=True)
    claim_receipt.add_argument("--http-status", type=int, required=True)
    claim_receipt.add_argument("--output", type=Path, required=True)

    status = subparsers.add_parser("assert-unresolved")
    status.add_argument("--candidate", type=Path, required=True)
    status.add_argument("--response", type=Path, required=True)
    status.add_argument("--http-status", type=int, required=True)

    queue = subparsers.add_parser("validate-queue")
    queue.add_argument("--queue", type=Path, required=True)
    queue.add_argument("--output", type=Path, required=True)

    kms = subparsers.add_parser("seal-kms-signature")
    kms.add_argument("--prepared", type=Path, required=True)
    kms.add_argument("--kms-response", type=Path, required=True)
    kms.add_argument("--expected-kms-key-arn", required=True)
    kms.add_argument("--output", type=Path, required=True)

    reissue = subparsers.add_parser("verify-reissue-receipt")
    reissue.add_argument("--resolution", type=Path, required=True)
    reissue.add_argument("--response", type=Path, required=True)
    reissue.add_argument("--http-status", type=int, required=True)
    reissue.add_argument("--output", type=Path, required=True)

    retained_status = subparsers.add_parser("verify-resolution-status")
    retained_status.add_argument("--resolution", type=Path, required=True)
    retained_status.add_argument("--reissue-response", type=Path, required=True)
    retained_status.add_argument("--status-response", type=Path, required=True)
    retained_status.add_argument("--http-status", type=int, required=True)
    retained_status.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "retain-ingress":
        value = json.loads(args.payload.read_text())
        if not isinstance(value, Mapping):
            raise DispatchContractError("the input file is not an object")
        output = retain_ingress(
            args.event_name,
            value,
            github_repository=args.github_repository,
            github_repository_id=args.github_repository_id,
            github_run_id=args.github_run_id,
            github_run_attempt=args.github_run_attempt,
            received_at=args.received_at,
            workflow_revision=args.workflow_revision,
            dispatch_signing_key=os.environ.get(args.dispatch_signing_key_env, ""),
        )
        args.output.write_bytes(canonical_json(output))
        return 0

    if args.command == "build-run-locator":
        ingress_value = json.loads(args.ingress.read_text())
        if not isinstance(ingress_value, Mapping):
            raise DispatchContractError("the retained ingress is not an object")
        args.output.write_bytes(
            canonical_json(build_dispatch_run_locator(ingress_value))
        )
        return 0

    if args.command == "prepare-not-received":
        value = json.loads(args.candidate.read_text())
        if not isinstance(value, Mapping):
            raise DispatchContractError("the input file is not an object")
        dispatch_attempted_at = value.get("dispatch_attempted_at")
        if not isinstance(dispatch_attempted_at, str):
            raise DispatchContractError("the dispatch attempt time is missing")
        if HEX64.fullmatch(args.expected_attempt_sha256) is None:
            raise DispatchContractError("the expected dispatch attempt digest is malformed")
        issued_at = _iso(datetime.now(timezone.utc))
        inventory = fetch_authoritative_github_inventory(
            dispatch_attempted_at=dispatch_attempted_at,
            observed_at=issued_at,
            token=os.environ.get(args.github_token_env, ""),
            expected_app_id=args.expected_app_id,
            expected_app_slug=args.expected_app_slug,
            expected_installation_id=args.expected_installation_id,
        )
        inventory = account_github_run_inventory(
            inventory,
            fetch_object=lambda key: fetch_s3_object(
                key,
                bucket=args.s3_bucket,
                expected_owner=args.s3_expected_owner,
            ),
        )
        candidate_key = (
            "dispatch-ingress/sha256/"
            f"{args.expected_attempt_sha256[:2]}/"
            f"{args.expected_attempt_sha256}.json"
        )
        assert_s3_object_absent(
            candidate_key,
            bucket=args.s3_bucket,
            expected_owner=args.s3_expected_owner,
        )
        output = prepare_not_received_resolution(
            value,
            expected_attempt_sha256=args.expected_attempt_sha256,
            expected_envelope_sha256=args.expected_envelope_sha256,
            issued_at=issued_at,
            ingress_ledger_object=None,
            github_inventory=inventory,
        )
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
        return 0

    if args.command == "build-claim":
        ingress_value = json.loads(args.ingress.read_text())
        if not isinstance(ingress_value, Mapping):
            raise DispatchContractError("the retained ingress is not an object")
        args.output.write_bytes(canonical_json(build_dispatch_claim(ingress_value)))
        return 0

    if args.command == "verify-claim-receipt":
        request_value = json.loads(args.claim_request.read_text())
        response_value = json.loads(args.response.read_text())
        if not isinstance(request_value, Mapping) or not isinstance(
            response_value, Mapping
        ):
            raise DispatchContractError("the claim receipt input is not an object")
        output = verify_dispatch_claim_receipt(
            request_value,
            http_status=args.http_status,
            response=response_value,
        )
        args.output.write_bytes(canonical_json(output))
        return 0

    if args.command == "assert-unresolved":
        candidate_value = json.loads(args.candidate.read_text())
        response_value = json.loads(args.response.read_text())
        if not isinstance(candidate_value, Mapping) or not isinstance(
            response_value, Mapping
        ):
            raise DispatchContractError("the Cloud status input is not an object")
        assert_cloud_attempt_unresolved(
            candidate_value,
            http_status=args.http_status,
            response=response_value,
        )
        return 0

    if args.command == "validate-queue":
        queue_value = json.loads(args.queue.read_text())
        if not isinstance(queue_value, Mapping):
            raise DispatchContractError("the Cloud queue input is not an object")
        output = {
            "schema": queue_value.get("schema"),
            "candidates": validate_candidate_queue(queue_value),
        }
        args.output.write_bytes(canonical_json(output))
        return 0

    if args.command == "seal-kms-signature":
        prepared_value = json.loads(args.prepared.read_text())
        kms_value = json.loads(args.kms_response.read_text())
        if not isinstance(prepared_value, Mapping) or not isinstance(
            kms_value, Mapping
        ):
            raise DispatchContractError("the KMS signing input is not an object")
        output = sign_kms_response(
            prepared_value,
            kms_value,
            expected_key_arn=args.expected_kms_key_arn,
        )
        args.output.write_bytes(canonical_json(output))
        return 0

    if args.command == "verify-reissue-receipt":
        resolution_value = json.loads(args.resolution.read_text())
        response_value = json.loads(args.response.read_text())
        if not isinstance(resolution_value, Mapping) or not isinstance(
            response_value, Mapping
        ):
            raise DispatchContractError("the reissue receipt input is not an object")
        output = verify_resolution_reissue_receipt(
            resolution_value,
            http_status=args.http_status,
            response=response_value,
        )
        args.output.write_bytes(canonical_json(output))
        return 0

    resolution_value = json.loads(args.resolution.read_text())
    reissue_value = json.loads(args.reissue_response.read_text())
    status_value = json.loads(args.status_response.read_text())
    if not all(
        isinstance(value, Mapping)
        for value in (resolution_value, reissue_value, status_value)
    ):
        raise DispatchContractError("the retained status input is not an object")
    output = verify_retained_resolution_status(
        resolution_value,
        reissue_value,
        http_status=args.http_status,
        status_response=status_value,
    )
    args.output.write_bytes(canonical_json(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
