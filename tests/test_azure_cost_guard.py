import pathlib
import sys
from datetime import datetime, timezone

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from azure_cost_guard import (  # noqa: E402
    AzureCommandError,
    active_lease,
    find_candidates,
    report,
    verify_recovery_snapshot,
)


NOW = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
RESOURCE_ID = "/subscriptions/x/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/temp"


def vm(*, tags=None, power_state="VM running"):
    return {
        "id": RESOURCE_ID,
        "name": "temp",
        "resourceGroup": "rg",
        "hardwareProfile": {"vmSize": "Standard_D4s_v4"},
        "powerState": power_state,
        "timeCreated": "2026-07-27T02:32:08Z",
        "tags": tags or {},
    }


def test_temporary_running_vm_reports_cost_and_alerts():
    candidates = find_candidates(
        [vm(tags={"temporary": "true"})], {}, {RESOURCE_ID.lower(): 6.54}, NOW
    )
    payload, alert = report(candidates, threshold=5.0)
    assert alert is True
    assert payload["estimated_unprotected_daily_cost_cad"] == 6.54
    assert candidates[0].reason == "temporary:true"
    assert candidates[0].age_hours == 129.5


def test_group_autostop_policy_selects_vm():
    candidates = find_candidates([vm()], {"rg": {"autostop": "deallocate-when-idle"}}, {}, NOW)
    assert len(candidates) == 1
    assert candidates[0].reason == "autostop policy"


def test_active_owner_lease_protects_qualification_job():
    tags = {"owner": "qualification", "lease_expires_at": "2026-08-01T13:00:00Z"}
    assert active_lease(tags, NOW) == (True, "2026-08-01T13:00:00+00:00")
    candidates = find_candidates([vm(tags={"temporary": "true", **tags})], {}, {RESOURCE_ID.lower(): 6.54}, NOW)
    payload, alert = report(candidates, threshold=0.01)
    assert candidates[0].protected is True
    assert payload["estimated_unprotected_daily_cost_cad"] == 0
    assert alert is False


def test_expired_lease_is_not_protected():
    active, _ = active_lease(
        {"owner": "qualification", "lease_expires_at": "2026-08-01T11:59:59Z"}, NOW
    )
    assert active is False


def test_deallocated_vm_is_not_a_candidate():
    assert find_candidates([vm(tags={"temporary": "true"}, power_state="VM deallocated")], {}, {}, NOW) == []


def test_unprotected_running_vm_alerts_even_when_cost_data_is_late():
    candidates = find_candidates([vm(tags={"temporary": "true"})], {}, {}, NOW)
    _, alert = report(candidates, threshold=5.0)
    assert alert is True


def test_recovery_snapshot_must_be_in_target_subscription():
    try:
        verify_recovery_snapshot(
            "target",
            "/subscriptions/other/resourceGroups/rg/providers/Microsoft.Compute/snapshots/s",
        )
    except AzureCommandError as error:
        assert "different subscription" in str(error)
    else:
        raise AssertionError("expected a rejected snapshot")


def test_recovery_snapshot_must_have_succeeded_state(mocker):
    mocker.patch("azure_cost_guard.az_json", return_value={"provisioningState": "Creating"})
    try:
        verify_recovery_snapshot(
            "target",
            "/subscriptions/target/resourceGroups/rg/providers/Microsoft.Compute/snapshots/s",
        )
    except AzureCommandError as error:
        assert "Succeeded" in str(error)
    else:
        raise AssertionError("expected an incomplete snapshot rejection")


def test_scheduled_guard_uses_step_level_secret_gate():
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/azure-cost-guard.yml").read_text(encoding="utf-8")
    )
    report = workflow["jobs"]["report"]
    steps = report["steps"]
    assert "github.actor != 'openadapt-lifecycle[bot]'" in report["if"]
    assert "github.triggering_actor != 'openadapt-lifecycle[bot]'" in report["if"]
    credentials = next(step for step in steps if step.get("id") == "credentials")
    assert credentials["env"]["AZURE_CREDENTIALS"] == "${{ secrets.AZURE_CREDENTIALS }}"
    login = next(step for step in steps if "Azure/login@" in step.get("uses", ""))
    assert login["if"] == "${{ steps.credentials.outputs.available == 'true' }}"
