"""Protect the credential, ciphertext, and durable-alert workflow boundaries."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

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


def test_health_cadence_claims_say_github_schedules_are_best_effort() -> None:
    # GitHub starts scheduled runs on a best-effort basis. On 2026-10-09 the
    # health check's last 100 scheduled runs were a median of 285 minutes
    # apart, not the 30 minutes the cron asks for. A bare cadence promise
    # tells operators that an outage is noticed far sooner than it is.
    cadence = re.compile(r"every \d+ minutes", re.IGNORECASE)
    # A table row or a prose paragraph is one claim; the qualifier must sit
    # in the same claim as the cadence.
    claims = []
    for block in read("ops/PRODUCTION_OPERATIONS.md").split("\n\n"):
        if block.lstrip().startswith("|"):
            claims.extend(block.splitlines())
        else:
            claims.append(" ".join(block.split()))
    cadence_claims = [claim for claim in claims if cadence.search(claim)]
    assert cadence_claims
    for claim in cadence_claims:
        assert "best-effort" in claim, claim

    header = read(".github/workflows/prod-health-alert.yml").split("\non:", 1)[0]
    claim = header.split("# Cadence:", 1)[1].split("\n#\n", 1)[0]
    assert cadence.search(claim)
    assert "best-effort" in claim
    assert "not a real-time pager" in claim
    assert "bounds detection latency" not in header


def test_a_passing_health_probe_pings_the_external_monitor() -> None:
    steps = yaml.safe_load(read(".github/workflows/prod-health-alert.yml"))["jobs"][
        "probe"
    ]["steps"]
    probe = next(
        i
        for i, step in enumerate(steps)
        if "check_production_readiness.py" in step.get("run", "")
    )
    ping = next(
        i
        for i, step in enumerate(steps)
        if "PROD_HEALTH_PING_URL" in step.get("env", {})
    )
    assert probe < ping
    # Default success() condition: a failed or skipped probe sends no ping,
    # so the external monitor alerts after its grace period.
    assert "if" not in steps[ping]
    assert steps[ping]["env"]["PROD_HEALTH_PING_URL"] == (
        "${{ secrets.PROD_HEALTH_PING_URL }}"
    )
    # A ping outage must not fail the probe job, or the durable issue would
    # report a healthy service as failing.
    assert "|| echo" in steps[ping]["run"]
    assert "PROD_HEALTH_PING_URL" in read("ops/PRODUCTION_OPERATIONS.md")


def test_backup_jobs_keep_distinct_failure_and_freshness_issues() -> None:
    backup = read(".github/workflows/db-backup.yml")
    freshness = read(".github/workflows/db-backup-freshness.yml")
    assert "Production database backup is not current" in backup
    assert "Production database recovery point is stale or unverified" in freshness
    assert "issues: write" in backup
    assert "issues: write" in freshness
