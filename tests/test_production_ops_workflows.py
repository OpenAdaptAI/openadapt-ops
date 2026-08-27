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
    ".github/workflows/db-backup-dispatch-reconciliation.yml",
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
        if path == ".github/workflows/db-backup.yml":
            assert concurrency["group"] == "production-db-backup"
        elif path == ".github/workflows/db-backup-dispatch-reconciliation.yml":
            assert concurrency["group"] == "production-backup-dispatch-authority"
        else:
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
    assert "permission-contents: write" not in content
    assert "permission-pull-requests: write" not in content
    assert "openadapt-evals" not in content
    assert "git push origin HEAD:main" not in content
    assert "gh pr create" not in content
    assert "cancel-in-progress: false" in content


def test_docs_sync_rejects_lifecycle_authority_before_pages_or_oidc() -> None:
    value = workflow(".github/workflows/sync.yml")
    guard = value["jobs"]["reject-lifecycle-app"]
    assert guard["permissions"] == {}
    assert "openadapt-lifecycle[bot]" in str(guard)
    deploy = value["jobs"]["sync-and-deploy"]
    assert deploy["needs"] == "reject-lifecycle-app"
    assert "github.actor" in deploy["if"]
    assert "github.triggering_actor" in deploy["if"]
    content = read(".github/workflows/sync.yml")
    assert "pages: write" in content
    assert "id-token: write" in content


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


def test_backup_dispatch_authority_retains_and_claims_before_any_effect() -> None:
    content = read(".github/workflows/db-backup-dispatch-authority.yml")
    value = workflow(".github/workflows/db-backup-dispatch-authority.yml")
    assert "workflow_call" in value["on"]
    assert set(value["on"]["workflow_call"]) == {"outputs"}
    assert "repository_dispatch" not in value["on"]
    job = value["jobs"]["claim"]
    assert job["environment"] == "production-backup-dispatch-ingress"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    assert value["concurrency"]["group"] == "production-backup-dispatch-authority"
    assert "persist-credentials: false" in content
    assert "AWS_BACKUP_DISPATCH_INGRESS_ROLE_ARN" in content
    assert "AWS_BACKUP_DISPATCH_RECONCILIATION_ROLE_ARN" not in content
    assert "aws kms sign" not in content
    assert "KMS_KEY_ARN" not in content
    assert "--if-none-match '*'" in content
    retain = content.index("retain-ingress")
    ledger = content.index("put-object", retain)
    locator = content.index("build-run-locator", ledger)
    status = content.index("assert-unresolved", locator)
    claim = content.index("build-claim", status)
    receipt = content.index("verify-claim-receipt", claim)
    assert retain < ledger < locator < status < claim < receipt
    assert "dispatch-run-locators/github/" in content
    assert "dispatch-attempt/claim" in content
    assert "github.workflow_ref" in content
    assert "OpenAdaptAI/openadapt-ops/.github/workflows/db-backup-activate.yml@refs/heads/main" in content
    assert "github.event.action" in content
    assert "toJSON(github.event.client_payload)" in content
    assert "inputs.dispatch_payload_json" not in content
    assert "inputs.event_name" not in content
    assert "activation_request_b64=" not in content
    assert "first-backup" not in content
    assert "restore" not in content


def test_backup_absence_authority_queries_inventory_and_kms_without_caller_proof() -> None:
    content = read(".github/workflows/db-backup-dispatch-reconciliation.yml")
    value = workflow(".github/workflows/db-backup-dispatch-reconciliation.yml")
    job = value["jobs"]["reconcile"]
    assert job["environment"] == "production-backup-dispatch-reconciliation"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    assert "OPENADAPT_BACKUP_DISPATCH_AUTHORITY_ENABLED" in content
    assert "AWS_BACKUP_DISPATCH_RECONCILIATION_ROLE_ARN" in content
    assert "AWS_BACKUP_DISPATCH_INGRESS_ROLE_ARN" not in content
    assert "OPS_BACKUP_DISPATCH_CLAIM_TOKEN" not in content
    assert "permission-actions: read" in content
    assert "permission-metadata: read" in content
    assert "persist-credentials: false" in content
    assert "prepare-not-received" in content
    assert "--s3-bucket \"${AWS_BACKUP_CONTROL_BUCKET}\"" in content
    assert "--s3-expected-owner \"${AWS_ACCOUNT_ID}\"" in content
    assert "--github-token-env BACKUP_CONTROL_GITHUB_TOKEN" in content
    assert "--github-runs" not in content
    assert "--if-none-match '*'" in content
    assert "aws kms sign" in content
    assert "ECDSA_SHA_256" in content
    assert "aws kms get-public-key" in content
    assert "ECC_NIST_P256" in content
    assert "SIGN_VERIFY" in content
    assert "alias/openadapt-production-backup-dispatch-resolution" in content
    assert "OPENADAPT_BACKUP_DISPATCH_RESOLUTION_PUBLIC_KEY_SHA256" in content
    assert "OPENADAPT_BACKUP_DISPATCH_RESOLUTION_REVOKED_KEY_IDS" in content
    assert "verify-reissue-receipt" in content
    assert "verify-resolution-status" in content
    assert "Idempotency-Key: ${resolution_id}" in content
    assert content.index("head-object", content.index("prepare-not-received")) < content.index(
        "aws kms sign"
    )


def test_backup_control_credentials_are_scoped_to_the_two_authority_workflows() -> None:
    references: dict[str, set[str]] = {
        "OPS_BACKUP_DISPATCH_CLAIM_TOKEN": set(),
        "OPS_BACKUP_DISPATCH_RESOLUTION_TOKEN": set(),
        "OPENADAPT_BACKUP_CONTROL_APP_PRIVATE_KEY": set(),
    }
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        content = path.read_text(encoding="utf-8")
        for name, paths in references.items():
            if name in content:
                paths.add(str(path.relative_to(ROOT)))
    assert references["OPS_BACKUP_DISPATCH_CLAIM_TOKEN"] == {
        ".github/workflows/db-backup-dispatch-authority.yml"
    }
    assert references["OPS_BACKUP_DISPATCH_RESOLUTION_TOKEN"] == {
        ".github/workflows/db-backup-dispatch-authority.yml",
        ".github/workflows/db-backup-dispatch-reconciliation.yml",
    }
    assert references["OPENADAPT_BACKUP_CONTROL_APP_PRIVATE_KEY"] == {
        ".github/workflows/db-backup-dispatch-reconciliation.yml"
    }


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
