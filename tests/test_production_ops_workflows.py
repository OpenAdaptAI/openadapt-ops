"""Protect the credential, ciphertext, and durable-alert workflow boundaries."""

from __future__ import annotations

import json
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
        if path == ".github/workflows/db-backup.yml":
            assert concurrency["group"] == "production-db-backup"
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
    assert discovered == (
        set(REJECT_LIFECYCLE_WORKFLOWS)
        - {
            ".github/workflows/db-backup.yml",
        }
    ) | {
        ".github/workflows/db-backup-activate.yml",
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
    assert (
        "OpenAdaptAI/openadapt-ops/.github/workflows/db-backup-activate.yml@refs/heads/main"
        in content
    )
    assert "github.event.action" in content
    assert "toJSON(github.event.client_payload)" in content
    assert "inputs.dispatch_payload_json" not in content
    assert "inputs.event_name" not in content
    assert "activation_request_b64=" not in content
    assert "first-backup" not in content
    assert "restore" not in content


def test_backup_control_credentials_are_scoped_to_the_ingress_authority() -> None:
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
    }
    assert references["OPENADAPT_BACKUP_CONTROL_APP_PRIVATE_KEY"] == set()


def test_backup_dispatch_authority_policy_separates_ingress_from_signing() -> None:
    policy = json.loads(read("ops/backup/dispatch-authority-policy.json"))
    assert set(policy) == {
        "schema_version",
        "repository",
        "repository_id",
        "aws_account_id",
        "aws_region",
        "ingress",
        "reconciliation",
    }
    assert policy["schema_version"] == (
        "openadapt.production-backup-dispatch-authority-policy/v1"
    )
    ingress = policy["ingress"]
    reconciliation = policy["reconciliation"]
    assert ingress["environment"] == "production-backup-dispatch-ingress"
    assert ingress["oidc_subject"] == (
        "repo:OpenAdaptAI/openadapt-ops:environment:production-backup-dispatch-ingress"
    )
    assert ingress["role_variable"] == "AWS_BACKUP_DISPATCH_INGRESS_ROLE_ARN"
    assert ingress["denied_aws_actions"] == ["kms:Sign"]
    assert "kms:Sign" not in ingress["allowed_aws_actions"]
    assert ingress["cloud_bearer_secrets"] == [
        "OPS_BACKUP_DISPATCH_CLAIM_TOKEN",
        "OPS_BACKUP_DISPATCH_RESOLUTION_TOKEN",
    ]
    assert reconciliation["environment"] == (
        "production-backup-dispatch-reconciliation"
    )
    assert reconciliation["oidc_subject"] == (
        "repo:OpenAdaptAI/openadapt-ops:environment:production-backup-dispatch-reconciliation"
    )
    assert reconciliation["role_variable"] == (
        "AWS_BACKUP_DISPATCH_RECONCILIATION_ROLE_ARN"
    )
    assert reconciliation["cloud_bearer_secrets"] == [
        "OPS_BACKUP_DISPATCH_RESOLUTION_TOKEN"
    ]
    assert reconciliation["forbidden_secrets"] == ["OPS_BACKUP_DISPATCH_CLAIM_TOKEN"]
    assert reconciliation["kms"] == {
        "account_id": "992382684924",
        "region": "us-east-1",
        "alias": "alias/openadapt-production-backup-dispatch-resolution",
        "key_spec": "ECC_NIST_P256",
        "key_usage": "SIGN_VERIFY",
        "signing_algorithm": "ECDSA_SHA_256",
        "message_type": "RAW",
    }


def test_backup_uses_one_s3_validated_full_object_put() -> None:
    workflow = read(".github/workflows/db-backup.yml")
    prepare = workflow.index("prepare-single-put")
    put = workflow.index("aws s3api put-object", prepare)
    verify = workflow.index("verify-uploaded-pair", prepare)
    assert prepare < put < verify
    assert '--checksum-algorithm SHA256 --checksum-sha256 "$local_checksum"' in workflow
    assert '--content-length "$cipher_bytes"' in workflow
    assert 'aws s3 cp "$cipher"' not in workflow


def test_backup_write_path_accepts_only_the_claimed_initial_payment_call() -> None:
    content = read(".github/workflows/db-backup.yml")
    value = workflow(".github/workflows/db-backup.yml")
    assert value["on"] == {
        "workflow_call": {
            "inputs": {
                "activation_request_b64": {
                    "description": "Signed first-payment activation request.",
                    "required": "true",
                    "type": "string",
                },
                "dispatch_claim_sha256": {
                    "description": "Exact successful dispatch-authority claim digest.",
                    "required": "true",
                    "type": "string",
                },
                "recovery_point_stamp": {
                    "description": (
                        "Deterministic UTC stamp for the first paid-customer backup."
                    ),
                    "required": "true",
                    "type": "string",
                },
            }
        }
    }
    assert "workflow_dispatch:" not in content
    assert "schedule:" not in content
    gate = content.index("Verify the claimed paid activation request")
    credentials = content.index("aws-actions/configure-aws-credentials")
    put = content.index("aws s3api put-object")
    assert gate < credentials < put
    assert "database_backup_activation.py verify-claimed-request" in content
    assert '--authority-claim-sha256 "${DISPATCH_CLAIM_SHA256}"' in content
    assert '[[ "${DISPATCH_CLAIM_SHA256}" =~ ^[0-9a-f]{64}$ ]]' in content
    assert content.index("verify-claimed-request") < credentials
    retained_state_load = content.index(
        "for stage in ready restore backup pending-backup"
    )
    begin = content.index("database_backup_activation.py begin")
    assert credentials < retained_state_load < begin
    assert "database_backup_activation.py resume" in content
    assert "database_backup_activation.py sign-state" in content
    assert '"activation/${activation_id}"' in content
    assert "steps.activation.outputs.needs_backup == 'true'" in content
    assert "needs.dump.result != 'skipped'" in content
    assert "verify-lease" not in content
    assert "SCHEDULE_LEASE" not in content
    assert "RENEWAL" not in content
    assert "CONTINUATION" not in content

    freshness = read(".github/workflows/db-backup-freshness.yml")
    assert "vars.DATABASE_BACKUP_SCHEDULE_ENABLED == 'true'" in freshness
    assert "needs.verify.result != 'skipped'" in freshness


def test_paid_activation_caller_is_protected_and_fail_closed() -> None:
    content = read(".github/workflows/db-backup-activate.yml")
    value = workflow(".github/workflows/db-backup-activate.yml")
    assert value["on"] == {
        "repository_dispatch": {
            "types": ["verified_first_payment", "database_backup_renewal"]
        }
    }
    assert value["permissions"] == {}
    assert "workflow_dispatch:" not in content
    assert "schedule:" not in content
    jobs = value["jobs"]
    assert next(iter(jobs)) == "claim-dispatch"
    authority = jobs["claim-dispatch"]
    assert authority["uses"] == "./.github/workflows/db-backup-dispatch-authority.yml"
    assert "with" not in authority
    assert authority["secrets"] == "inherit"
    assert authority["permissions"] == {"contents": "read", "id-token": "write"}
    for name, job in jobs.items():
        if name == "claim-dispatch":
            continue
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "claim-dispatch" in needs, name
    assert "needs.claim-dispatch.outputs.claim_sha256" in content
    assert (
        "dispatch_claim_sha256: "
        "${{ needs.claim-dispatch.outputs.claim_sha256 }}" in content
    )
    assert '--authority-claim-sha256 "${CLAIM_SHA256}"' in content
    assert "needs.claim-dispatch.outputs.claim_receipt_sha256" in content
    assert "needs.claim-dispatch.outputs.dispatch_attempt_id_sha256" in content
    assert "PAYLOAD_DISPATCH_ATTEMPT_ID_SHA256" in content
    assert "environment: production-backup-activation" in content
    assert "check_github_environment_gate.py" in content
    assert "database_backup_activation.py verify-claimed-request" in content
    assert "uses: ./.github/workflows/db-backup.yml" in content
    assert "database_backup_activation.py record-backup" in read(
        ".github/workflows/db-backup.yml"
    )
    assert "scripts/run_database_restore_drill.sh" in content
    assert "database_backup_activation.py record-restore" in content
    assert "database_backup_activation.py issue-receipt" in content
    assert "database_backup_activation.py verify-readiness-ack" in content
    assert "database_backup_activation.py create-admission" not in content
    assert content.index("db-backup-dispatch-authority.yml") < content.index(
        "database_backup_activation.py verify-claimed-request"
    )
    assert content.index(
        "database_backup_activation.py verify-claimed-request"
    ) < content.index("uses: ./.github/workflows/db-backup.yml")
    assert content.index("uses: ./.github/workflows/db-backup.yml") < content.index(
        "scripts/run_database_restore_drill.sh"
    )
    assert content.index("scripts/run_database_restore_drill.sh") < content.index(
        "--request POST"
    )
    assert content.count("--request POST") == 1
    assert (
        "https://cloud.openadapt.ai/api/internal/database-backup/readiness/status"
        in content
    )
    assert (
        "https://cloud.openadapt.ai/api/internal/database-backup/readiness" in content
    )
    assert '--get "${CLOUD_BACKUP_READINESS_STATUS_URL}"' in content
    assert content.index(
        '--get "${CLOUD_BACKUP_READINESS_STATUS_URL}"'
    ) < content.index("--request POST")
    assert "put_exact_activation_object" in content
    assert '"${prefix}/restore-state.json"' in content
    assert '"${prefix}/ready-state.json"' in content
    assert '"${prefix}/readiness-receipt.json"' in content
    canonicalize = content.index("jq -cS . /tmp/database-backup-readiness-receipt.json")
    retain_receipt = content.index('"${prefix}/readiness-receipt.json"')
    encode_receipt = content.index(
        "base64 < /tmp/database-backup-readiness-receipt.json"
    )
    assert canonicalize < retain_receipt < encode_receipt
    assert "DATABASE_BACKUP_SCHEDULE_ENABLED" not in content
    assert "DATABASE_BACKUP_SCHEDULE_ADMISSION_B64" not in content
    preflight = content.split("  validate-initial-payment:", 1)[1].split(
        "  first-backup:", 1
    )[0]
    callback = content.split("  send-readiness:", 1)[1]
    assert "id-token: write" not in preflight
    assert "id-token: write" not in callback
    assert "aws-actions/configure-aws-credentials" not in content
    assert "AWS_BACKUP_DISPATCH_RECONCILIATION_ROLE_ARN" not in content
    assert "aws kms sign" not in content
    assert "PENDING_SCHEDULE" in content
    assert "Customer use and checkout stay disabled" in content
    assert "BACKUP_ACTIVE" not in content


def test_readiness_delivery_reconciles_uncertainty_without_a_second_post() -> None:
    content = read(".github/workflows/db-backup-activate.yml")
    callback = content.split("  send-readiness:", 1)[1]
    assert callback.count("--request POST") == 1
    assert callback.count('--get "${CLOUD_BACKUP_READINESS_STATUS_URL}"') == 2
    post = callback.index("--request POST")
    recovery_status = callback.index(
        '--get "${CLOUD_BACKUP_READINESS_STATUS_URL}"', post
    )
    refusal = callback.index("Reconciliation is required", recovery_status)
    verification = callback.index("verify-readiness-ack", refusal)
    assert post < recovery_status < refusal < verification
    assert "status_result" in callback
    assert '[[ ! "${status}" =~ ^2[0-9][0-9]$ ]]' in callback
    assert "Cloud has no exact retained acknowledgment" in callback


def test_claimed_renewal_stays_fail_closed_before_the_frozen_effect_contract() -> None:
    content = read(".github/workflows/db-backup-activate.yml")
    value = workflow(".github/workflows/db-backup-activate.yml")
    renewal = value["jobs"]["refuse-unbound-renewal"]
    assert renewal["needs"] == "claim-dispatch"
    assert renewal["if"] == "github.event.action == 'database_backup_renewal'"
    assert renewal["permissions"] == {}
    text = str(renewal)
    assert "claim_sha256" in text
    assert "claim_receipt_sha256" in text
    assert "dispatch_attempt_id_sha256" in text
    assert "exit 1" in text
    assert "No renewal effect ran" in text
    renewal_start = content.index("  refuse-unbound-renewal:")
    initial_start = content.index("  validate-initial-payment:")
    renewal_content = content[renewal_start:initial_start]
    for forbidden in (
        "aws ",
        "curl ",
        "database_backup_activation.py",
        "run_database_restore_drill.sh",
        "db-backup.yml",
    ):
        assert forbidden not in renewal_content


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
    assert "s3:GetObjectVersionAttributes" in writer
    assert "s3:GetObjectVersion" in writer
    assert "s3:GetObjectVersionAttributes" in restore
    assert "s3:GetObjectVersion" in restore
    assert "AWS::IAM::OIDCProvider" in template
    assert "AWS::S3::Bucket" in template


def test_scheduled_effect_stays_absent_until_the_asymmetric_lease_exists() -> None:
    backup = read(".github/workflows/db-backup.yml")
    monitor = read(".github/workflows/db-backup-freshness.yml")
    assert "schedule:" not in backup
    assert "cron:" not in backup
    assert "A later change will add the 12-hour schedule" in backup
    assert "asymmetric lease and prior-lease store" in backup
    assert "--maximum-rpo-seconds 86400" in backup
    assert "--maximum-age-seconds 86400" in monitor
    assert "cron: '43 * * * *'" in monitor
    assert 'created_at="${stamp:0:4}-${stamp:4:2}-${stamp:6:2}' in backup


def test_activation_resume_reconciles_s3_objects_and_refuses_unknown_reads() -> None:
    backup = read(".github/workflows/db-backup.yml")
    activation = read(".github/workflows/db-backup-activate.yml")
    assert "recover-single-put" in backup
    assert "artifact-manifest-base64" in backup
    assert "steps.reconcile.outputs.recovered != 'true'" in backup
    assert "The interrupted first-backup upload was reconciled" in backup
    for workflow in (backup, activation):
        assert "S3 did not prove whether activation state exists" in workflow
        assert "(NoSuchKey|NotFound|404)" in workflow


def test_backup_removes_signed_runner_material_on_every_terminal_path() -> None:
    backup = read(".github/workflows/db-backup.yml")
    cleanup = backup.split("      - name: Remove transient backup material", 1)[1]
    assert "if: always()" in cleanup
    for sensitive in (
        "/tmp/database-backup-activation-request.json",
        "/tmp/database-backup-activation-state.json",
        "/tmp/database-backup-pending-signed-state.json",
        "/tmp/database-backup-resume-request.json",
        "/tmp/database-backup-resumed-state.json",
        "/tmp/database-backup-after-backup-signed-state.json",
        "/tmp/database-backup-retained-backup-state.json",
    ):
        assert sensitive in cleanup


def test_database_backup_has_one_claimed_caller() -> None:
    callers = []
    needle = "uses: ./.github/workflows/db-backup.yml"
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        if needle in path.read_text(encoding="utf-8"):
            callers.append(path.name)
    assert callers == ["db-backup-activate.yml"]


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
    assert restore.index("precheck_result=0") < restore.index(
        'PGDATABASE="$SCRATCH_DB_URL" psql'
    )
    assert "already matches the exact backup" in restore


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
