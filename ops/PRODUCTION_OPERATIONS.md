# Production operations contract

This runbook defines the minimum operating control for the hosted browser lane.
It does not make every OpenAdapt workflow or execution surface production
ready. The exact workflow, application, environment, verifier, and deployment
must pass qualification.

## Automated checks

| Check | Schedule | Proof | Durable signal |
|---|---:|---|---|
| Production health | Every 30 minutes | HTTP 200, `no-store`, fresh `checked_at`, live mode, active encrypted writer, and every required component | One GitHub issue and optional Telegram alert |
| Database backup | Daily | An encrypted archive no larger than 5 GiB, one S3 PutObject, a redacted manifest, and a matching S3-validated full-object SHA-256 | One GitHub issue |
| Database backup freshness | Hourly | A complete S3 pair from the last 24 hours, a valid manifest digest, a matching object size, and the same full-object SHA-256 | One GitHub issue |
| Database restore gate | The hourly monitor checks it; run the drill every 30 days | A redacted receipt for an isolated database restore, with exact backup digests and measured RPO and RTO | The backup-freshness issue stays open when the receipt is absent or stale |
| Default branch sweep | Daily | The newest applicable run for every owned repository | One GitHub issue |
| Published version claims | Daily | Documentation claims against current package indexes | One GitHub issue |

These checks use GitHub Actions. GitHub can delay a schedule or disable it after
60 days without repository activity. Use one external monitor for the health
workflow and the backup-freshness workflow. A successful old run is not current
proof.

## Deployment gate

Complete these checks before a production promotion:

1. Protect `main`. Give each backup environment one exact custom `main` branch
   policy before an AWS OIDC role exists.
2. Bind the deployment to the reviewed source commit and artifact digests.
3. Run the complete local and hosted release gates for that exact commit.
4. Fetch the public readiness endpoint without a cache.
5. Run `scripts/check_production_readiness.py` against the response headers and
   body.
6. Complete an authenticated synthetic transaction through submission,
   idempotency, dispatch, callback, independent effect verification, receipt,
   and webhook delivery.
7. Test a duplicate request and an uncertain dispatch. Do not dispatch the
   action again during reconciliation.
8. Test one human halt, notification, answer, fresh-state revalidation, and
   resume.
9. Confirm a current database recovery point and a complete isolated recovery
   drill for the database and private Storage boundary.

The readiness endpoint proves configured dependencies. It does not prove a
customer workflow, a recovery drill, an alert delivery, or an SLA.

## Human halt support

A production workflow needs an assigned primary operator, a secondary operator,
and declared support hours. The operator must have access to the local evidence
boundary for protected detail. The hosted queue carries only the closed,
privacy-safe decision contract.

Test these cases before activation:

- the primary operator receives one real notification;
- an expired decision cannot resume the run;
- two answers cannot resume one pause;
- the runner rechecks the live record, target, state, and effect after an
  answer;
- a wrong operator answer causes a second halt;
- uncertain delivery selects reconciliation and does not dispatch again; and
- an unanswered halt reaches the secondary operator under the declared support
  policy.

Record the time to acknowledge, the time to resolve, and the final terminal
state. Do not count an accepted operator answer as a verified execution.

## False-success report

Report each qualification and production period with a named task, environment,
run count, and oracle. Include these separate counts:

- `VERIFIED`;
- `HALTED` before an effect;
- `HALTED` after a possible effect;
- an uncertain delivery;
- a silent incorrect success;
- an over-halt on a healthy task;
- a wrong-record, duplicate, or collateral effect;
- a model call; and
- a human halt that exceeded the support target.

Keep the denominator. A report with zero recorded runs does not prove a zero
failure rate. A screen success message does not replace the independent effect
oracle.

## Recovery

Use [`backup/RESTORE_DRILL.md`](backup/RESTORE_DRILL.md) for the off-provider
database recovery point. That backup does not contain private Storage objects.
Use the Cloud data-safety runbook for the complete database and Storage drill.

Do not report a recovery-time objective until an isolated restore measures it.
Do not report a 24-hour recovery-point objective while the freshness monitor is
red or absent.

## Founder configuration

The code cannot supply these values or operating decisions. Complete them in
this order:

1. Protect `main` with a pull request and the applicable status checks.
2. Create `production-backup` and `production-backup-monitor`. Give each
   environment one exact custom `main` branch policy and no other deployment
   policy.
3. Create the workflow-restricted `production-backup` runner group and an
   ephemeral runner inside the production data boundary. Put the runner only in
   that group. Permit only the exact backup workflow on `refs/heads/main`.
4. Deploy the reviewed backup CloudFormation stack in AWS account
   `992382684924`.
5. Configure the four settings in the `production-backup` GitHub environment.
6. Configure the two variables in the `production-backup-monitor` environment.
7. Store a second copy of the private `age` key in a team vault or offline
   medium.
8. Create an isolated scratch Supabase project and complete the first recovery
   drill.
9. Select the primary operator, the secondary operator, the support hours, and
   the response targets for human halts.
10. Configure an external monitor for the production health and backup freshness
   schedules.
11. Complete the first genuine customer transaction when an authorized customer
   is available. Do not create a founder self-charge as evidence.
