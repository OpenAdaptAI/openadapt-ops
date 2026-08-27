"""Protect the credential, ciphertext, and durable-alert workflow boundaries."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

REJECT_LIFECYCLE_WORKFLOWS = (
    ".github/workflows/action-pin-sweep.yml",
    ".github/workflows/azure-cost-guard.yml",
    ".github/workflows/db-backup-freshness.yml",
    ".github/workflows/db-backup.yml",
    ".github/workflows/default-branch-sweep.yml",
    ".github/workflows/prod-health-alert.yml",
    ".github/workflows/production-lifecycle-policy.yml",
    ".github/workflows/published-version-claims.yml",
    ".github/workflows/workspace-staleness-sweep.yml",
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def workflow(path: str) -> dict:
    value = yaml.load(read(path), Loader=yaml.BaseLoader)
    assert isinstance(value, dict)
    return value


def test_every_non_lifecycle_dispatch_refuses_the_lifecycle_app() -> None:
    for path in REJECT_LIFECYCLE_WORKFLOWS:
        value = workflow(path)
        concurrency = value["concurrency"]
        assert "github.workflow" in concurrency["group"], path
        assert "github.event_name" in concurrency["group"], path
        assert concurrency["cancel-in-progress"] == "false", path

        jobs = value["jobs"]
        guard = jobs["reject-lifecycle-app"]
        assert guard["permissions"] == {}, path
        guard_text = str(guard)
        assert "github.actor" in guard_text, path
        assert "github.triggering_actor" in guard_text, path
        assert "openadapt-lifecycle[bot]" in guard_text, path
        for name, job in jobs.items():
            if name == "reject-lifecycle-app":
                continue
            needs = job.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            assert "reject-lifecycle-app" in needs, f"{path}:{name}"


def test_dispatch_workflow_inventory_is_complete() -> None:
    discovered = set()
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        content = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^  (?:workflow_dispatch|repository_dispatch):\s*$", content):
            discovered.add(str(path.relative_to(ROOT)))
    assert discovered == set(REJECT_LIFECYCLE_WORKFLOWS) | {
        ".github/workflows/production-lifecycle-projection.yml",
        ".github/workflows/sync.yml",
    }


def test_lifecycle_feed_source_is_app_only_and_dispatches_one_closed_json() -> None:
    content = read(".github/workflows/production-lifecycle-projection.yml")
    assert "github.actor == 'openadapt-lifecycle[bot]'" in content
    assert "github.triggering_actor == 'openadapt-lifecycle[bot]'" in content
    assert "github.actor_id == vars.OPENADAPT_LIFECYCLE_ACTOR_ID" in content
    assert "vars.OPENADAPT_LIFECYCLE_APP_ID" in content
    assert "vars.OPENADAPT_LIFECYCLE_INSTALLATION_ID" in content
    assert "secrets.OPENADAPT_LIFECYCLE_APP_PRIVATE_KEY" in content
    assert "environment: production-lifecycle-projection" in content
    assert "production_lifecycle_feed_updated" not in content
    assert "feed_update_json" in content
    assert "production-lifecycle-ref.yml" in content
    assert "--repo OpenAdaptAI/.github" in content
    assert "--ref main" in content
    assert "permission-actions: write" in content
    assert "permission-contents: write" in content
    assert "git push origin HEAD:main" not in content
    assert "gh pr create" not in content
    assert "cancel-in-progress: false" in content


def test_app_authored_pull_request_validation_does_not_deadlock() -> None:
    for path in (
        ".github/workflows/action-pin-sweep.yml",
        ".github/workflows/default-branch-sweep.yml",
        ".github/workflows/production-lifecycle-policy.yml",
        ".github/workflows/published-version-claims.yml",
        ".github/workflows/workspace-staleness-sweep.yml",
    ):
        value = workflow(path)
        guard = value["jobs"]["reject-lifecycle-app"]
        text = str(guard)
        assert "github.event_name" in text, path
        assert "pull_request" in text, path
        assert "openadapt-lifecycle[bot]" in text, path


def test_lifecycle_required_check_runs_on_every_pull_request() -> None:
    content = read(".github/workflows/production-lifecycle-policy.yml")
    pull_request = content.split("  pull_request:", 1)[1].split("  push:", 1)[0]
    assert "paths:" not in pull_request
    assert "paths-ignore:" not in pull_request


def test_backup_configuration_fails_before_credentials_or_tool_install() -> None:
    workflow = read(".github/workflows/db-backup.yml")
    preflight = workflow.index("Validate the protected environment configuration")
    environment_gate = workflow.index("Verify the exact GitHub environment gate")
    credentials = workflow.index("aws-actions/configure-aws-credentials")
    supabase = workflow.index("supabase/setup-cli")
    assert preflight < environment_gate < credentials < supabase
    assert "actions: read" in workflow
    assert "GITHUB_REF_PROTECTED" in workflow
    assert "group: production-backup" in workflow
    assert "labels: self-hosted" in workflow
    assert "RUNNER_BOUNDARY: ${{ runner.environment }}" in workflow
    assert "\"${RUNNER_BOUNDARY}\" != 'self-hosted'" in workflow
    assert "check_github_environment_gate.py" in workflow
    target = workflow.index("check_live_database_backup_target.sh")
    dump = workflow.index("supabase db dump")
    assert environment_gate < credentials < target < dump
    for name in (
        "AWS_BACKUP_ROLE_ARN",
        "AWS_BACKUP_BUCKET",
        "SUPABASE_DB_URL",
        "SUPABASE_PROJECT_REF",
    ):
        assert f"missing+=({name})" in workflow


def test_backup_uses_one_s3_validated_full_object_put() -> None:
    workflow = read(".github/workflows/db-backup.yml")
    prepare = workflow.index("prepare-single-put")
    put = workflow.index("aws s3api put-object")
    verify = workflow.index("verify-single-put")
    assert prepare < put < verify
    assert '--checksum-algorithm SHA256 --checksum-sha256 "$local_checksum"' in workflow
    assert '--content-length "$cipher_bytes"' in workflow
    assert 'aws s3 cp "$cipher"' not in workflow


def test_backup_monitor_cannot_download_or_change_ciphertext() -> None:
    template = read("ops/backup/aws-backup-target.yml")
    monitor = template.split("  BackupMonitorRole:", 1)[1].split(
        "  BackupRestoreRole:", 1
    )[0]
    assert "Action: s3:GetObject\n" in monitor
    assert "daily/*/artifact-manifest.json" in monitor
    assert "Action: s3:GetObjectAttributes" in monitor
    assert "daily/*/*.age" in monitor
    assert "s3:PutObject" not in monitor
    assert "s3:DeleteObject" not in monitor

    workflow = read(".github/workflows/db-backup-freshness.yml")
    assert "SUPABASE_DB_URL" not in workflow
    assert "age --decrypt" not in workflow
    assert "get-object-attributes" in workflow
    assert "steps.select.outputs.ciphertext_key" in workflow
    assert "check_live_database_backup_target.sh" in workflow
    assert "--expected-bucket-owner 992382684924" in workflow
    assert workflow.index("Verify the exact GitHub environment gate") < workflow.index(
        "aws-actions/configure-aws-credentials"
    )
    assert "actions: read" in workflow
    assert "GITHUB_REF_PROTECTED" in workflow
    assert "check_github_environment_gate.py" in workflow


def test_health_probe_uses_the_strict_contract_and_a_durable_issue() -> None:
    workflow = read(".github/workflows/prod-health-alert.yml")
    assert "python scripts/check_production_readiness.py" in workflow
    assert "human-decision delivery component" in workflow
    assert "issues: write" in workflow
    assert "Production health check is failing" in workflow


def test_backup_jobs_keep_distinct_failure_and_freshness_issues() -> None:
    backup = read(".github/workflows/db-backup.yml")
    freshness = read(".github/workflows/db-backup-freshness.yml")
    assert "Production database backup is not current" in backup
    assert "Production database recovery point is stale or unverified" in freshness
    assert "issues: write" in backup
    assert "issues: write" in freshness
