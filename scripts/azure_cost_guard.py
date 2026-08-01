#!/usr/bin/env python3
"""Report Azure temporary-VM cost risk, with an explicit deallocation option.

The normal mode is report-only.  The optional deallocation mode requires both
``--apply`` and ``--confirm-deallocate``.  It never deletes a resource.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TARGET_SUBSCRIPTION = "78add6c6-c92a-4a53-b751-eb644ac77e59"
DEFAULT_ALERT_DAILY_CAD = 5.0
LEASE_TAGS = ("lease_expires_at", "lease-expires-at", "openadapt_lease_expires_at")


class AzureCommandError(RuntimeError):
    """An Azure CLI command did not return usable JSON."""


def az_json(arguments: list[str], *, input_json: dict[str, Any] | None = None) -> Any:
    command = ["az", *arguments, "-o", "json"]
    result = subprocess.run(
        command,
        input=json.dumps(input_json) if input_json is not None else None,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        raise AzureCommandError(result.stderr.strip() or "Azure CLI failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AzureCommandError("Azure CLI did not return JSON") from error


def as_tags(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key).lower(): str(item) for key, item in value.items() if item is not None}


def tag_is_true(tags: dict[str, str], name: str) -> bool:
    return tags.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def has_autostop_policy(tags: dict[str, str]) -> bool:
    return bool(tags.get("autostop", "").strip())


def parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def age_hours(created_at: str | None, now: datetime) -> float | None:
    """Return an age in hours when Azure supplied a valid creation time."""
    if not created_at:
        return None
    created = parse_time(created_at)
    if created is None or created > now:
        return None
    return round((now - created).total_seconds() / 3600, 1)


def active_lease(tags: dict[str, str], now: datetime) -> tuple[bool, str | None]:
    """Return whether a VM has an owner and an unexpired lease."""
    owner = tags.get("owner", "").strip()
    expiry_text = next((tags[name] for name in LEASE_TAGS if tags.get(name)), None)
    expiry = parse_time(expiry_text) if expiry_text else None
    if owner and expiry and expiry > now:
        return True, expiry.isoformat()
    return False, expiry_text


def latest_cost_by_resource(subscription: str, start: datetime, end: datetime) -> dict[str, float]:
    """Read the last non-zero daily VM cost from Cost Management when available."""
    payload = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start.isoformat(), "to": end.isoformat()},
        "dataset": {
            "granularity": "Daily",
            "aggregation": {"cost": {"name": "PreTaxCost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ResourceId"}],
        },
    }
    response = az_json(
        [
            "rest",
            "--method",
            "post",
            "--url",
            "https://management.azure.com/subscriptions/"
            f"{subscription}/providers/Microsoft.CostManagement/query?api-version=2023-11-01",
            "--body",
            json.dumps(payload),
        ]
    )
    properties = response.get("properties", {}) if isinstance(response, dict) else {}
    columns = properties.get("columns", [])
    rows = properties.get("rows", [])
    names = [column.get("name") for column in columns if isinstance(column, dict)]
    try:
        cost_index, date_index, resource_index = (
            names.index("PreTaxCost"),
            names.index("UsageDate"),
            names.index("ResourceId"),
        )
    except ValueError:
        return {}
    latest: dict[str, tuple[int, float]] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) <= max(cost_index, date_index, resource_index):
            continue
        try:
            cost, date, resource = float(row[cost_index]), int(row[date_index]), str(row[resource_index]).lower()
        except (TypeError, ValueError):
            continue
        if cost > 0 and (resource not in latest or date > latest[resource][0]):
            latest[resource] = (date, cost)
    return {resource: cost for resource, (_, cost) in latest.items()}


@dataclass(frozen=True)
class Candidate:
    id: str
    name: str
    resource_group: str
    sku: str
    power_state: str
    created_at: str | None
    age_hours: float | None
    reason: str
    owner: str | None
    lease_expires_at: str | None
    protected: bool
    daily_cost_cad: float | None


def find_candidates(
    vms: list[dict[str, Any]],
    group_tags: dict[str, dict[str, str]],
    costs: dict[str, float],
    now: datetime,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for vm in vms:
        if not isinstance(vm, dict) or str(vm.get("powerState", "")).lower() != "vm running":
            continue
        group = str(vm.get("resourceGroup", ""))
        vm_tags = as_tags(vm.get("tags"))
        combined_tags = {**group_tags.get(group.lower(), {}), **vm_tags}
        temporary = tag_is_true(combined_tags, "temporary")
        autostop = has_autostop_policy(combined_tags)
        if not temporary and not autostop:
            continue
        protected, lease_expiry = active_lease(combined_tags, now)
        reason = "temporary:true" if temporary else "autostop policy"
        resource_id = str(vm.get("id", "")).lower()
        candidates.append(
            Candidate(
                id=resource_id,
                name=str(vm.get("name", "")),
                resource_group=group,
                sku=str(vm.get("hardwareProfile", {}).get("vmSize", "unknown")),
                power_state=str(vm.get("powerState", "unknown")),
                created_at=vm.get("timeCreated"),
                age_hours=age_hours(vm.get("timeCreated"), now),
                reason=reason,
                owner=combined_tags.get("owner") or None,
                lease_expires_at=lease_expiry,
                protected=protected,
                daily_cost_cad=costs.get(resource_id),
            )
        )
    return candidates


def report(candidates: list[Candidate], threshold: float) -> tuple[dict[str, Any], bool]:
    at_risk = [candidate for candidate in candidates if not candidate.protected]
    known_daily_cost = sum(candidate.daily_cost_cad or 0 for candidate in at_risk)
    # A running temporary VM with an expired or absent lease is itself the
    # actionable signal. Cost data can arrive late, so do not make alerting
    # depend on its availability. The threshold adds cost context to the alert.
    alert = bool(at_risk)
    return (
        {
            "subscription": TARGET_SUBSCRIPTION,
            "action": "report",
            "threshold_daily_cad": threshold,
            "estimated_unprotected_daily_cost_cad": round(known_daily_cost, 2),
            "cost_threshold_exceeded": known_daily_cost >= threshold,
            "alert": alert,
            "candidates": [candidate.__dict__ for candidate in candidates],
        },
        alert,
    )


def write_github_output(path: str | None, alert: bool, estimated_cost: float) -> None:
    if not path:
        return
    Path(path).write_text(
        f"alert={'true' if alert else 'false'}\n"
        f"estimated_unprotected_daily_cost_cad={estimated_cost:.2f}\n",
        encoding="utf-8",
    )


def verify_recovery_snapshot(subscription: str, snapshot_id: str) -> None:
    """Require a succeeded recovery snapshot before explicit deallocation."""
    expected_prefix = f"/subscriptions/{subscription.lower()}/"
    if not snapshot_id.lower().startswith(expected_prefix):
        raise AzureCommandError("Recovery snapshot belongs to a different subscription")
    snapshot = az_json(["snapshot", "show", "--ids", snapshot_id])
    if not isinstance(snapshot, dict) or snapshot.get("provisioningState") != "Succeeded":
        raise AzureCommandError("Recovery snapshot is not in Succeeded state")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subscription", default=TARGET_SUBSCRIPTION)
    parser.add_argument("--alert-daily-cad", type=float, default=DEFAULT_ALERT_DAILY_CAD)
    parser.add_argument("--action", choices=("report", "deallocate"), default="report")
    parser.add_argument("--apply", action="store_true", help="Perform the selected action.")
    parser.add_argument("--confirm-deallocate", action="store_true")
    parser.add_argument("--recovery-snapshot-id")
    parser.add_argument("--github-output")
    args = parser.parse_args(argv)
    if args.subscription != TARGET_SUBSCRIPTION:
        parser.error(f"This guard only permits subscription {TARGET_SUBSCRIPTION}.")
    if args.action == "deallocate" and (
        not args.apply or not args.confirm_deallocate or not args.recovery_snapshot_id
    ):
        parser.error(
            "Deallocation requires --apply, --confirm-deallocate, and --recovery-snapshot-id."
        )

    now = datetime.now(timezone.utc)
    groups = az_json(["group", "list", "--subscription", args.subscription])
    group_tags = {
        str(group.get("name", "")).lower(): as_tags(group.get("tags"))
        for group in groups
        if isinstance(group, dict)
    }
    vms = az_json(["vm", "list", "-d", "--subscription", args.subscription])
    # Do not call Cost Management when no running temporary/autostop VM exists.
    # This keeps the scheduled guard cheap while preserving cost estimates when
    # they can affect an alert or an operator decision.
    candidates = find_candidates(vms, group_tags, {}, now)
    if candidates:
        costs: dict[str, float] = {}
        try:
            costs = latest_cost_by_resource(
                args.subscription,
                now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=8),
                now,
            )
        except AzureCommandError as error:
            print(f"WARNING: Cost Management data is unavailable: {error}", file=sys.stderr)
        candidates = find_candidates(vms, group_tags, costs, now)
    payload, alert = report(candidates, args.alert_daily_cad)
    payload["action"] = args.action
    print(json.dumps(payload, indent=2, sort_keys=True))
    write_github_output(
        args.github_output,
        alert,
        payload["estimated_unprotected_daily_cost_cad"],
    )

    if args.action == "deallocate" and args.apply:
        verify_recovery_snapshot(args.subscription, args.recovery_snapshot_id)
        for candidate in candidates:
            if candidate.protected:
                continue
            subprocess.run(
                ["az", "vm", "deallocate", "--ids", candidate.id], check=True, text=True
            )
    return 2 if alert else 0


if __name__ == "__main__":
    raise SystemExit(main())
