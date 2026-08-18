#!/usr/bin/env python3
"""Validate the public production-readiness response without trusting one boolean."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_COMPONENTS = frozenset(
    {
        "mode",
        "auth",
        "database",
        "storage",
        "runner",
        "compiler",
        "runtime_validation_trust",
        "runtime_boundary",
        "bundle_protection",
        "recorder",
        "callbacks",
        "scheduler",
        "human_decision_web_push",
        "retention",
        "security_events",
        "secrets",
        "validation_policy",
        "billing",
    }
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReadinessError(ValueError):
    """The readiness response does not prove the production contract."""


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise ReadinessError(f"{name} is missing")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReadinessError(f"{name} is not an ISO-8601 time") from error
    if result.tzinfo is None:
        raise ReadinessError(f"{name} has no timezone")
    return result.astimezone(timezone.utc)


def parse_headers(raw: str) -> tuple[int, dict[str, str]]:
    """Return the final HTTP response block emitted by ``curl -D``."""
    blocks = [block for block in re.split(r"\r?\n\r?\n", raw.strip()) if block]
    http_blocks = [block for block in blocks if block.startswith("HTTP/")]
    if not http_blocks:
        raise ReadinessError("the response has no HTTP status")
    lines = http_blocks[-1].splitlines()
    status = re.match(r"^HTTP/\S+\s+(\d{3})(?:\s|$)", lines[0])
    if status is None:
        raise ReadinessError("the HTTP status is invalid")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ReadinessError("the response has an invalid header")
        name, value = line.split(":", 1)
        key = name.strip().lower()
        headers[key] = (
            f"{headers[key]}, {value.strip()}" if key in headers else value.strip()
        )
    return int(status.group(1)), headers


def validate(
    *,
    headers_text: str,
    body_text: str,
    now: datetime,
    maximum_age_seconds: int,
) -> dict[str, object]:
    if maximum_age_seconds <= 0:
        raise ReadinessError("the maximum response age must be positive")
    if now.tzinfo is None:
        raise ReadinessError("now has no timezone")
    status, headers = parse_headers(headers_text)
    if status != 200:
        raise ReadinessError(f"the readiness endpoint returned HTTP {status}")
    content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ReadinessError("the readiness response is not JSON")
    cache_directives = {
        part.strip().lower()
        for part in headers.get("cache-control", "").split(",")
        if part.strip()
    }
    if "no-store" not in cache_directives:
        raise ReadinessError("the readiness response can be cached")

    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError as error:
        raise ReadinessError("the readiness response is not valid JSON") from error
    if not isinstance(payload, dict):
        raise ReadinessError("the readiness response is not an object")
    if payload.get("ready") is not True:
        raise ReadinessError("the production deployment is not ready")
    if payload.get("mode") != "live":
        raise ReadinessError("the production deployment is not in live mode")

    checked_at = parse_time(payload.get("checked_at"), "checked_at")
    age = (now.astimezone(timezone.utc) - checked_at).total_seconds()
    if age < -30:
        raise ReadinessError("the readiness time is in the future")
    if age > maximum_age_seconds:
        raise ReadinessError("the readiness result is stale")

    if payload.get("encrypted_writer_protocol") != 1:
        raise ReadinessError("the encrypted writer protocol is not active")
    if payload.get("encrypted_writer_role") != "active":
        raise ReadinessError("the encrypted writer role is not active")
    for name in ("encrypted_writer_key_sha256", "encrypted_writer_deployment_sha256"):
        value = payload.get(name)
        if not isinstance(value, str) or SHA256.fullmatch(value) is None:
            raise ReadinessError(f"{name} is invalid")

    raw_components = payload.get("components")
    if not isinstance(raw_components, list):
        raise ReadinessError("the readiness component list is missing")
    components: dict[str, dict[str, object]] = {}
    for component in raw_components:
        if not isinstance(component, dict) or not isinstance(
            component.get("name"), str
        ):
            raise ReadinessError("the readiness component list is invalid")
        name = component["name"]
        if name in components:
            raise ReadinessError(f"the readiness component is duplicated: {name}")
        components[name] = component

    missing = sorted(REQUIRED_COMPONENTS - components.keys())
    if missing:
        raise ReadinessError(
            f"required readiness components are missing: {', '.join(missing)}"
        )
    failed = sorted(
        name
        for name in REQUIRED_COMPONENTS
        if components[name].get("required") is not True
        or components[name].get("state") != "ready"
    )
    if failed:
        raise ReadinessError(
            f"required readiness components did not pass: {', '.join(failed)}"
        )
    for name, component in components.items():
        if component.get("required") is True and component.get("state") != "ready":
            raise ReadinessError(
                f"an additional required component did not pass: {name}"
            )

    return {
        "ready": True,
        "mode": "live",
        "checked_at": checked_at.isoformat().replace("+00:00", "Z"),
        "required_components": len(REQUIRED_COMPONENTS),
        "reported_components": len(components),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--headers", required=True)
    result.add_argument("--body", required=True)
    result.add_argument("--now")
    result.add_argument("--maximum-age-seconds", type=int, default=180)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        now = parse_time(args.now, "now") if args.now else datetime.now(timezone.utc)
        result = validate(
            headers_text=Path(args.headers).read_text(encoding="utf-8"),
            body_text=Path(args.body).read_text(encoding="utf-8"),
            now=now,
            maximum_age_seconds=args.maximum_age_seconds,
        )
    except (OSError, ReadinessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
