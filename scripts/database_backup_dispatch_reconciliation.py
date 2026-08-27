#!/usr/bin/env python3
"""Retain Cloud dispatch identity and sign exact NOT_RECEIVED resolutions."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

INITIAL_EVENT = "verified_first_payment"
INITIAL_SCHEMA = "openadapt.database-backup-activation-dispatch/v1"
RENEWAL_EVENT = "database_backup_renewal"
RENEWAL_SCHEMA = "openadapt.database-backup-renewal-dispatch/v1"
RESOLUTION_SCHEMA = "openadapt.database-backup-dispatch-resolution/v1"
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
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ACTIVATION_ID = re.compile(r"^act_[0-9a-f]{64}$")
LEASE_EVENT_ID = re.compile(r"^lease_[0-9a-f]{64}$")
RESOLUTION_ID = re.compile(r"^resolution_[0-9a-f]{64}$")
CANDIDATE_FIELDS = {
    "resolution_id",
    "dispatch_kind",
    "activation_id",
    "organization_id_sha256",
    "dispatch_attempt_id_sha256",
    "dispatch_envelope_sha256",
    "lease_event_id",
    "prior_lease_sha256",
    "requested_lease_sequence",
    "last_error_code",
    "reconciliation_required_at",
}


class DispatchContractError(ValueError):
    """A dispatch identity or absence proof is incomplete or inconsistent."""


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


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


def retain_ingress(
    event_name: str,
    payload: Mapping[str, Any],
    *,
    github_repository: str,
    github_run_id: str,
    github_run_attempt: int,
) -> dict[str, Any]:
    if github_repository != "OpenAdaptAI/openadapt-ops":
        raise DispatchContractError("the GitHub repository identity is not exact")
    if not github_run_id.isdigit() or github_run_attempt < 1:
        raise DispatchContractError("the GitHub run identity is malformed")
    if event_name == INITIAL_EVENT:
        expected_fields = {
            "schema",
            "dispatch_attempt_id_sha256",
            "dispatch_envelope_sha256",
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
            "lease_event_id",
            "dispatch_attempt_id_sha256",
            "dispatch_envelope_sha256",
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
    envelope_digest = payload.get("dispatch_envelope_sha256")
    if not isinstance(attempt_digest, str) or HEX64.fullmatch(attempt_digest) is None:
        raise DispatchContractError("the dispatch attempt digest is malformed")
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
    else:
        if embedded_identity != lease_event_id:
            raise DispatchContractError("the lease event identity does not match")
        activation_id = identity.get("activation_id")
        if (
            not isinstance(activation_id, str)
            or ACTIVATION_ID.fullmatch(activation_id) is None
        ):
            raise DispatchContractError("the renewal activation identity is malformed")
    return {
        "schema": "openadapt.ops-backup-dispatch-ingress/v1",
        "event_name": event_name,
        "dispatch_kind": kind,
        "activation_id": activation_id,
        "lease_event_id": lease_event_id,
        "dispatch_attempt_id_sha256": attempt_digest,
        "dispatch_envelope_sha256": envelope_digest,
        "signed_envelope_b64": envelope_b64,
        "github_repository": github_repository,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
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


def resolution_id(candidate: Mapping[str, Any]) -> str:
    identity = {
        "activation_id": candidate.get("activation_id"),
        "dispatch_attempt_id_sha256": candidate.get("dispatch_attempt_id_sha256"),
        "dispatch_envelope_sha256": candidate.get("dispatch_envelope_sha256"),
        "dispatch_kind": candidate.get("dispatch_kind"),
        "lease_event_id": candidate.get("lease_event_id"),
        "requested_lease_sequence": candidate.get("requested_lease_sequence"),
    }
    return "resolution_" + _sha256(canonical_json(identity))


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DispatchContractError("issued_at is not an ISO-8601 time") from exc
    if result.tzinfo is None:
        raise DispatchContractError("issued_at has no timezone")
    return result.astimezone(timezone.utc)


def _assert_github_run_absence(
    runs: Sequence[Mapping[str, Any]], *, reconciliation_required_at: str
) -> None:
    _timestamp(reconciliation_required_at)
    for run in runs:
        event = run.get("event")
        created_at = run.get("created_at")
        run_id = run.get("id")
        if (
            not isinstance(event, str)
            or not isinstance(created_at, str)
            or not isinstance(run_id, int)
        ):
            raise DispatchContractError("the GitHub run inventory is incomplete")
        _timestamp(created_at)
        if event == "repository_dispatch":
            raise DispatchContractError(
                "a repository_dispatch run can match the missing delivery"
            )


def prepare_not_received_resolution(
    candidate: Mapping[str, Any],
    *,
    expected_attempt_sha256: str,
    expected_envelope_sha256: str,
    issued_at: str,
    ingress_ledger_object: bytes | None,
    github_runs: Sequence[Mapping[str, Any]],
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
    reconciliation_required_at = candidate.get("reconciliation_required_at")
    if not isinstance(reconciliation_required_at, str):
        raise DispatchContractError("the reconciliation time is missing")
    _assert_github_run_absence(
        github_runs, reconciliation_required_at=reconciliation_required_at
    )
    activation_id = candidate.get("activation_id")
    if (
        not isinstance(activation_id, str)
        or ACTIVATION_ID.fullmatch(activation_id) is None
    ):
        raise DispatchContractError("the candidate activation identity is malformed")
    kind = candidate.get("dispatch_kind")
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
    expected_resolution_id = resolution_id(candidate)
    if candidate.get("resolution_id") != expected_resolution_id:
        raise DispatchContractError("the candidate resolution identity does not match")
    issued = _timestamp(issued_at)
    expires = issued + timedelta(minutes=5)
    resolution = {
        "activation_id": activation_id,
        "audience": RESOLUTION_AUDIENCE,
        "dispatch_attempt_id_sha256": candidate["dispatch_attempt_id_sha256"],
        "dispatch_envelope_sha256": candidate["dispatch_envelope_sha256"],
        "dispatch_kind": kind,
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
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


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingress = subparsers.add_parser("retain-ingress")
    ingress.add_argument("--event-name", required=True)
    ingress.add_argument("--payload", type=Path, required=True)
    ingress.add_argument("--output", type=Path, required=True)
    ingress.add_argument("--github-repository", required=True)
    ingress.add_argument("--github-run-id", required=True)
    ingress.add_argument("--github-run-attempt", type=int, required=True)
    resolve = subparsers.add_parser("prepare-not-received")
    resolve.add_argument("--candidate", type=Path, required=True)
    resolve.add_argument("--expected-attempt-sha256", required=True)
    resolve.add_argument("--expected-envelope-sha256", required=True)
    resolve.add_argument("--issued-at", required=True)
    resolve.add_argument("--github-runs", type=Path, required=True)
    resolve.add_argument("--ingress-ledger-object", type=Path)
    resolve.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = (
        json.loads(args.payload.read_text())
        if args.command == "retain-ingress"
        else json.loads(args.candidate.read_text())
    )
    if not isinstance(value, Mapping):
        raise DispatchContractError("the input file is not an object")
    if args.command == "retain-ingress":
        output = retain_ingress(
            args.event_name,
            value,
            github_repository=args.github_repository,
            github_run_id=args.github_run_id,
            github_run_attempt=args.github_run_attempt,
        )
    else:
        runs = json.loads(args.github_runs.read_text())
        if not isinstance(runs, list) or not all(
            isinstance(run, Mapping) for run in runs
        ):
            raise DispatchContractError("the GitHub run inventory is not an array")
        existing = (
            args.ingress_ledger_object.read_bytes()
            if args.ingress_ledger_object is not None
            else None
        )
        output = prepare_not_received_resolution(
            value,
            expected_attempt_sha256=args.expected_attempt_sha256,
            expected_envelope_sha256=args.expected_envelope_sha256,
            issued_at=args.issued_at,
            ingress_ledger_object=existing,
            github_runs=runs,
        )
    if args.command == "retain-ingress":
        args.output.write_bytes(canonical_json(output))
    else:
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
