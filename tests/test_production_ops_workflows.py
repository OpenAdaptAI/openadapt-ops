"""Protect the credential, ciphertext, and durable-alert workflow boundaries."""

from __future__ import annotations

import re
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
    put = workflow.index("aws s3api put-object", prepare)
    verify = workflow.index("verify-uploaded-pair")
    assert prepare < put < verify
    assert '--checksum-algorithm SHA256 --checksum-sha256 "$local_checksum"' in workflow
    assert '--content-length "$cipher_bytes"' in workflow
    assert "--storage-class GLACIER_IR" in workflow
    assert "--storage-class STANDARD" in workflow
    assert workflow.count("--if-none-match '*'") >= 4
    assert '--version-id "$cipher_version"' in workflow
    assert '--version-id "$manifest_version"' in workflow
    assert "--object-attributes Checksum,ObjectSize,StorageClass" in workflow
    assert "encrypted_archive_gib" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow
    assert 'aws s3 cp "$cipher"' not in workflow


def test_backup_write_paths_require_payment_or_signed_active_admission() -> None:
    workflow = read(".github/workflows/db-backup.yml")
    assert "workflow_dispatch:" not in workflow
    assert "vars.DATABASE_BACKUP_SCHEDULE_ENABLED == 'true'" in workflow
    gate = workflow.index("Verify the paid activation or active schedule admission")
    credentials = workflow.index("aws-actions/configure-aws-credentials")
    put = workflow.index("aws s3api put-object")
    assert gate < credentials < put
    assert "database_backup_activation.py begin" in workflow
    assert "database_backup_activation.py verify-admission" in workflow
    assert "database_backup_activation.py resume" in workflow
    assert "database_backup_activation.py sign-state" in workflow
    assert '"activation/${activation_id}"' in workflow
    assert "steps.activation.outputs.needs_backup == 'true'" in workflow
    assert "needs.dump.result != 'skipped'" in workflow

    freshness = read(".github/workflows/db-backup-freshness.yml")
    assert "if: vars.DATABASE_BACKUP_SCHEDULE_ENABLED == 'true'" in freshness
    assert "needs.verify.result != 'skipped'" in freshness


def test_paid_activation_caller_is_protected_and_fail_closed() -> None:
    workflow = read(".github/workflows/db-backup-activate.yml")
    assert "types: [verified_first_payment]" in workflow
    assert "workflow_dispatch:" not in workflow
    assert "schedule:" not in workflow
    assert "environment: production-backup-activation" in workflow
    assert "check_github_environment_gate.py" in workflow
    assert "database_backup_activation.py begin" in workflow
    assert "uses: ./.github/workflows/db-backup.yml" in workflow
    assert "database_backup_activation.py record-backup" in read(
        ".github/workflows/db-backup.yml"
    )
    assert "scripts/run_database_restore_drill.sh" in workflow
    assert "database_backup_activation.py record-restore" in workflow
    assert "database_backup_activation.py issue-receipt" in workflow
    assert "database_backup_activation.py create-admission" in workflow
    assert workflow.index("database_backup_activation.py begin") < workflow.index(
        "uses: ./.github/workflows/db-backup.yml"
    )
    assert workflow.index("uses: ./.github/workflows/db-backup.yml") < workflow.index(
        "scripts/run_database_restore_drill.sh"
    )
    assert workflow.index("scripts/run_database_restore_drill.sh") < workflow.index(
        "--request POST"
    )
    assert workflow.count("--request POST") == 1
    assert '--get "${CLOUD_BACKUP_READINESS_STATUS_URL}"' in workflow
    assert workflow.index(
        '--get "${CLOUD_BACKUP_READINESS_STATUS_URL}"'
    ) < workflow.index("--request POST")
    assert "put_exact_activation_object" in workflow
    assert '"${prefix}/restore-state.json"' in workflow
    assert '"${prefix}/ready-state.json"' in workflow
    assert '"${prefix}/readiness-receipt.json"' in workflow
    assert "DATABASE_BACKUP_SCHEDULE_ENABLED" not in workflow
    assert "DATABASE_BACKUP_SCHEDULE_ADMISSION_B64" not in workflow
    preflight = workflow.split("  verify-payment-signal:", 1)[1].split(
        "  first-backup:", 1
    )[0]
    callback = workflow.split("  send-readiness:", 1)[1]
    assert "id-token: write" not in preflight
    assert "id-token: write" not in callback
    assert "aws-actions/configure-aws-credentials" not in workflow


def test_pre_revenue_backup_stack_has_no_fixed_cost_addons() -> None:
    template = read("ops/backup/aws-backup-target.yml")
    for paid_addon in (
        "AWS::KMS::Key",
        "AWS::CloudTrail::Trail",
        "AWS::CloudWatch::Alarm",
        "AWS::S3::StorageLens",
        "MetricsConfigurations",
    ):
        assert paid_addon not in template
    writer = template.split("  BackupWriterRole:", 1)[1].split(
        "  BackupMonitorRole:", 1
    )[0]
    restore = template.split("  BackupRestoreRole:", 1)[1].split("Outputs:", 1)[0]
    for policy in (writer, restore):
        assert "s3:GetObject" in policy
        assert "s3:PutObject" in policy
        assert "activation/*" in policy
    assert "AWS::IAM::OIDCProvider" in template
    assert "AWS::S3::Bucket" in template


def test_backup_cadence_keeps_one_attempt_inside_the_24_hour_rpo() -> None:
    backup = read(".github/workflows/db-backup.yml")
    monitor = read(".github/workflows/db-backup-freshness.yml")
    schedule = re.search(r"cron: '23 ([0-9,]+) \* \* \*'", backup)
    assert schedule is not None
    hours = [int(value) for value in schedule.group(1).split(",")]
    gaps = [
        (hours[(index + 1) % len(hours)] - hour) % 24
        for index, hour in enumerate(hours)
    ]
    assert hours == [7, 19]
    assert gaps == [12, 12]
    assert "--maximum-rpo-seconds 86400" in backup
    assert "--maximum-age-seconds 86400" in monitor
    assert "cron: '43 * * * *'" in monitor


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


def test_restore_refuses_wrong_storage_classes_before_download() -> None:
    restore = read("scripts/run_database_restore_drill.sh")
    gate = restore.index("verify-storage-classes")
    first_download = restore.index("aws s3api get-object --bucket")
    assert gate < first_download
    assert '--key "${prefix}/artifact-manifest.json"' in restore
    assert '--key "${prefix}/${cipher}"' in restore
    assert "--object-attributes ObjectSize,StorageClass" in restore
    assert restore.count('--version-id "$BACKUP_CIPHERTEXT_VERSION_ID"') >= 3
    assert restore.count('--version-id "$BACKUP_MANIFEST_VERSION_ID"') >= 2
    assert "RESTORE_ROLE_SESSION_READY" in restore
    assert "assumed-role/${role_name}" in restore


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
