"""Protect the credential, ciphertext, and durable-alert workflow boundaries."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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
    assert '"${RUNNER_BOUNDARY}" != \'self-hosted\'' in workflow
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
    assert "--content-length \"$cipher_bytes\"" in workflow
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
    assert "drills/database-only/*/*.json" in monitor
    assert "drills/database-only/*" in monitor
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
    backup_verify = workflow.index("check_database_backup_freshness.py verify")
    restore_select = workflow.index("check_database_backup_freshness.py select-restore")
    restore_get = workflow.index("steps.restore.outputs.receipt_key")
    restore_verify = workflow.index("check_database_backup_freshness.py verify-restore")
    assert backup_verify < restore_select < restore_get < restore_verify
    assert "--maximum-age-seconds 2592000" in workflow


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
    assert "The dump job did not get a runner." in backup
    assert '(.steps | length)' in backup
    assert "database-only restore receipt from the last 30 days" in freshness
