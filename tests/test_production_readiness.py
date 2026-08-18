from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_production_readiness import (
    REQUIRED_COMPONENTS,
    ReadinessError,
    validate,
)

NOW = datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc)
HEADERS = """HTTP/2 200\r
content-type: application/json\r
cache-control: no-store,max-age=0\r
\r
"""


def payload() -> dict[str, object]:
    return {
        "ready": True,
        "mode": "live",
        "checked_at": "2026-08-18T15:59:30Z",
        "encrypted_writer_protocol": 1,
        "encrypted_writer_role": "active",
        "encrypted_writer_key_sha256": "a" * 64,
        "encrypted_writer_deployment_sha256": "b" * 64,
        "components": [
            {"name": name, "required": True, "state": "ready", "detail": "ok"}
            for name in sorted(REQUIRED_COMPONENTS)
        ]
        + [{"name": "sandbox", "required": False, "state": "not_ready"}],
    }


def check(value: dict[str, object], headers: str = HEADERS) -> dict[str, object]:
    return validate(
        headers_text=headers,
        body_text=json.dumps(value),
        now=NOW,
        maximum_age_seconds=180,
    )


def test_complete_live_contract_passes() -> None:
    result = check(payload())
    assert result["ready"] is True
    assert result["required_components"] == len(REQUIRED_COMPONENTS)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: value.update(ready=False), "not ready"),
        (lambda value: value.update(mode="mock"), "not in live mode"),
        (lambda value: value.update(checked_at="2026-08-18T15:50:00Z"), "stale"),
        (
            lambda value: value.update(encrypted_writer_role="standby"),
            "writer role is not active",
        ),
    ],
)
def test_false_success_top_level_response_is_rejected(change, message: str) -> None:
    value = payload()
    change(value)
    with pytest.raises(ReadinessError, match=message):
        check(value)


def test_missing_required_component_is_rejected() -> None:
    value = payload()
    value["components"] = [
        component
        for component in value["components"]
        if component["name"] != "human_decision_web_push"
    ]
    with pytest.raises(ReadinessError, match="human_decision_web_push"):
        check(value)


def test_required_component_failure_is_rejected_even_when_ready_is_true() -> None:
    value = payload()
    next(
        component
        for component in value["components"]
        if component["name"] == "database"
    )["state"] = "not_ready"
    with pytest.raises(ReadinessError, match="database"):
        check(value)


def test_new_required_component_failure_is_rejected() -> None:
    value = payload()
    value["components"].append(
        {"name": "new_dependency", "required": True, "state": "not_ready"}
    )
    with pytest.raises(ReadinessError, match="new_dependency"):
        check(value)


def test_cacheable_response_is_rejected() -> None:
    with pytest.raises(ReadinessError, match="cached"):
        check(payload(), HEADERS.replace("no-store,max-age=0", "max-age=300"))


def test_nonpositive_maximum_age_is_rejected() -> None:
    with pytest.raises(ReadinessError, match="must be positive"):
        validate(
            headers_text=HEADERS,
            body_text=json.dumps(payload()),
            now=NOW,
            maximum_age_seconds=0,
        )
