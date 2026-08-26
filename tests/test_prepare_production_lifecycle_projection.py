from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prepare_production_lifecycle_projection",
    ROOT / "scripts" / "prepare_production_lifecycle_projection.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_bytes() -> dict[str, bytes]:
    return {key: f"{key}\n".encode() for key in MODULE.EXPECTED_PATHS}


def fetcher(values: dict[str, bytes]):
    def fetch(url: str) -> bytes:
        path = url.split("/", 6)[-1]
        key = next(key for key, value in MODULE.EXPECTED_PATHS.items() if value == path)
        return values[key]

    return fetch


def inputs() -> tuple[dict[str, str], dict[str, bytes]]:
    values = source_bytes()
    commit = "a" * 40
    admissions = MODULE.digest(values["admissions"])
    head = MODULE.ledger_head_sha256(
        admissions, MODULE.digest(values["evidence_registry"])
    )
    return (
        {
            "source_commit": commit,
            "source_repository": MODULE.SOURCE_REPOSITORY,
            "source_ref": MODULE.SOURCE_REF,
            "source_event": MODULE.SOURCE_EVENT,
            "candidate_admissions_sha256": admissions,
            "candidate_ledger_head_sha256": head,
            "idempotency_key": MODULE.projection_idempotency_key(
                source_commit=commit,
                candidate_admissions_sha256=admissions,
                candidate_ledger_head_sha256=head,
            ),
        },
        values,
    )


def test_exact_projection_inputs_build_a_commit_bound_inventory() -> None:
    candidate, values = inputs()
    source = MODULE.prepare(**candidate, fetch_bytes=fetcher(values))
    assert source["source_commit"] == "a" * 40
    assert set(source["files"]) == set(MODULE.EXPECTED_PATHS)
    assert source["files"]["admissions"]["sha256"] == MODULE.digest(
        values["admissions"]
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_repository", "OpenAdaptAI/openadapt-ops"),
        ("source_ref", "refs/heads/release"),
        ("source_event", "repository_dispatch"),
        ("candidate_admissions_sha256", "sha256:" + "0" * 64),
        ("candidate_ledger_head_sha256", "sha256:" + "0" * 64),
        ("idempotency_key", "sha256:" + "0" * 64),
    ],
)
def test_projection_inputs_fail_closed(field: str, value: str) -> None:
    candidate, values = inputs()
    candidate[field] = value
    with pytest.raises(MODULE.ProjectionInputError):
        MODULE.prepare(**candidate, fetch_bytes=fetcher(values))
