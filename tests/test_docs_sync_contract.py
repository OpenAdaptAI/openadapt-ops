from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_docs_sync", ROOT / "scripts" / "validate_docs_sync.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def values() -> dict[str, str | Path]:
    source_repository = "OpenAdaptAI/openadapt-evals"
    source_ref = "refs/heads/main"
    source_commit = "a" * 40
    source_event = "push"
    return {
        "repositories": ROOT / "repos.yml",
        "source_repository": source_repository,
        "source_ref": source_ref,
        "source_commit": source_commit,
        "source_event": source_event,
        "idempotency_key": MODULE.expected_idempotency_key(
            source_repository, source_ref, source_commit, source_event
        ),
    }


def test_exact_allowlisted_dispatch_passes() -> None:
    MODULE.validate(**values())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_repository", "OpenAdaptAI/openadapt-cloud"),
        ("source_ref", "refs/heads/release"),
        ("source_commit", "A" * 40),
        ("source_event", "repository_dispatch"),
        ("idempotency_key", "docs-sync:" + "0" * 64),
    ],
)
def test_dispatch_contract_fails_closed(field: str, value: str) -> None:
    candidate = values()
    candidate[field] = value
    with pytest.raises(MODULE.DocsSyncError):
        MODULE.validate(**candidate)
