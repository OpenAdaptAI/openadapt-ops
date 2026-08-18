# Production database backup and restore drill

This runbook owns the daily off-provider logical database backup in
`.github/workflows/db-backup.yml`. It complements the complete database and
private-Storage restore drill in `openadapt-cloud/docs/RUNBOOK_DATA_SAFETY.md`.

## Current state

The design target is:

- one logical database backup each day;
- client-side `age` encryption before network transfer;
- a private S3 bucket in OpenAdapt AWS account `992382684924`;
- a maximum recovery-point objective (RPO) of 24 hours when consecutive jobs
  succeed;
- 90-day S3 retention;
- a local restore to a separate Supabase scratch project;
- measured database-only RPO and recovery-time objective (RTO) evidence; and
- the separate Cloud drill before any complete recovery claim.

This is not yet a proven recovery path. A read-only check on 2026-08-18 used
AWS account `992382684924` and confirmed that the
`openadapt-production-db-backup` CloudFormation stack does not exist. GitHub
issue [#126](https://github.com/OpenAdaptAI/openadapt-ops/issues/126) records
the matching protected-environment configuration failure. As of that check:

- no daily backup has completed;
- no scratch restore has completed;
- no measured RTO exists;
- provider PITR is not enabled;
- the AWS stack is not deployed;
- `main` has no repository ruleset or branch protection;
- the `production-backup` GitHub environment has none of its four required
  settings and has no deployment-branch restriction;
- the `production-backup-monitor` GitHub environment is not configured;
- no scratch Supabase project is configured; and
- one local private `age` key exists, but its required second vault or offline
  copy is not confirmed.

Do not describe the database as recoverable until one scheduled backup and one
isolated restore drill pass.

## Security boundary

This repository is public. Production database bytes must never enter a
GitHub artifact, workflow log, pull-request attachment, or public release.

The workflow writes only these objects to a private S3 bucket:

- `daily/<UTC-stamp>/db-backup-<UTC-stamp>.tar.gz.age`, which is `age`
  ciphertext; and
- `daily/<UTC-stamp>/artifact-manifest.json`, which contains sizes, digests,
  the source commit, and the workflow run ID. It contains no project name,
  database URL, table data, or credential.

S3 also encrypts each object with SSE-S3. This server-side layer does not
replace `age`. The private `age` key stays on a trusted operator device and in
a separate vault or offline copy. It does not enter GitHub.

The logical database backup does not contain private Supabase Storage objects.
It also uses the maintained Supabase roles, schema, and data commands, which
take separate logical snapshots. Do not run it during a schema migration. The
complete Cloud drill pauses writes, exports and rechecks Storage, restores both
boundaries, and produces the canonical retention receipt.

## GitHub trust gate before AWS setup

Create the external GitHub gates before the CloudFormation stack creates an
OIDC role. The OIDC subject binds a role to an environment. The environment's
deployment policy is the exact branch gate.

1. Protect `main` with a repository ruleset. Require a pull request and the
   applicable status checks. Add required code-owner review only when a second
   authorized maintainer can approve the founder's pull request.
2. Create the `production-backup` GitHub environment.
3. Give it one custom deployment branch policy: the exact `main` branch. Do not
   select every protected branch. Do not add a tag or wildcard policy.
4. Create the `production-backup-monitor` GitHub environment.
5. Give it the same single custom `main` branch policy.
6. Do not require a manual environment approval. An approval wait would prevent
   the scheduled jobs.

Verify that `main` reports as protected. Verify that each environment reports
`custom_branch_policies: true`, `protected_branches: false`, and one policy with
the exact name `main`. Both workflows repeat this check after the environment
admits the job and before they request AWS credentials. The job has read-only
Actions permission for this API check. Do not deploy the AWS stack until this
gate passes.

## One-time AWS setup

The CloudFormation template creates:

- a private, versioned S3 bucket;
- public-access blocking and a TLS-only bucket policy;
- 90-day retention for daily backups;
- 365-day retention for database-only drill evidence;
- a GitHub OIDC writer role bound to the exact `production-backup`
  environment;
- a read-only GitHub OIDC monitor role bound to the exact
  `production-backup-monitor` environment; and
- a local restore role bound to one exact AWS operator principal.

The expected S3 Standard storage price is approximately USD 0.023 per GB each
month, plus small request charges. For example, retaining 90 daily 100 MB
backups is approximately 9 GB, or USD 0.21 each month before requests. The
template does not create a paid KMS key and does not enable Supabase PITR.

The backup workflow uses one S3 `PutObject` with a caller-supplied full-object
SHA-256. S3 validates that checksum before it accepts the object. This launch
path refuses an encrypted archive above 5 GiB before upload. Build and qualify a
multipart contract before a production database can exceed that limit.

An AWS principal with CloudFormation, IAM, and S3 administration rights must
run:

```sh
export AWS_PROFILE=openadapt
aws sts get-caller-identity --query Account --output text
# Must print 992382684924.

aws cloudformation deploy \
  --stack-name openadapt-production-db-backup \
  --template-file ops/backup/aws-backup-target.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags owner=OpenAdapt environment=production purpose=database-backup
```

The current `claude-ops` principal cannot create this stack because it does
not have `cloudformation:CreateChangeSet`. Do not bypass the template with
manual S3 or IAM changes. Use an authorized administration principal, then
record these outputs:

```sh
aws cloudformation describe-stacks \
  --stack-name openadapt-production-db-backup \
  --query 'Stacks[0].Outputs'
```

## Complete the GitHub settings after AWS setup

The branch and environment gates already exist. Add the AWS outputs and the
database identity only after the stack passes validation:

1. Set `production-backup` environment variables from the CloudFormation
   outputs:
   - `AWS_BACKUP_BUCKET`
   - `AWS_BACKUP_ROLE_ARN`
2. Set `production-backup` environment secrets:
   - `SUPABASE_DB_URL`: the production direct or session-pooler PostgreSQL URL
   - `SUPABASE_PROJECT_REF`: the exact production project reference
3. Set `production-backup-monitor` environment variables from the
   CloudFormation outputs:
   - `AWS_BACKUP_BUCKET`
   - `AWS_BACKUP_MONITOR_ROLE_ARN`

The monitor environment has no secret. Its AWS role can list and inspect only
the `daily/` objects. It cannot create, replace, delete, download, or decrypt a
database backup.

The workflow validates that the URL belongs to the declared Supabase project.
It also checks AWS account `992382684924`, complete S3 public-access blocking,
and the committed `age` recipient before it reads the database.

The public recipient is in `ops/backup/age-recipients.txt`. Store its private
key with mode `0600` on an encrypted trusted device. Make a second copy in a
team vault or an offline medium before the first backup. Without a second copy,
one device loss makes all retained backups unreadable.

## Run and verify the first backup

After the AWS and GitHub setup, dispatch the workflow once. Do not wait for the
next schedule.

```sh
gh workflow run db-backup.yml --repo OpenAdaptAI/openadapt-ops --ref main
gh run list --repo OpenAdaptAI/openadapt-ops \
  --workflow db-backup.yml --limit 5
gh workflow run db-backup-freshness.yml \
  --repo OpenAdaptAI/openadapt-ops --ref main
gh run list --repo OpenAdaptAI/openadapt-ops \
  --workflow db-backup-freshness.yml --limit 5
```

Require all of these results:

- the workflow succeeds on the exact `main` commit;
- S3 contains one ciphertext object and one redacted manifest below the same
  UTC stamp;
- the stored SHA-256 checksum equals the local upload checksum;
- S3 reports the exact caller-supplied full-object SHA-256 for the ciphertext;
- the encrypted archive is no more than the enforced 5 GiB launch limit;
- no GitHub Actions artifact exists for the run.
- the separate read-only freshness workflow selects the same recovery point,
  validates the redacted manifest digest, matches the S3 object size and remote
  checksum, and reports an age of less than 24 hours.

A successful upload proves backup creation and storage. It does not prove that
the backup can restore.

## Run the database-only scratch restore

Create a new disposable Supabase project in the required region. Never use the
production project, an existing customer project, or a shared development
project. The script never creates or deletes a project.

Install `aws`, `age`, `psql`, and Supabase CLI 2.75.0 on the trusted operator
device. Then set:

```sh
export AWS_PROFILE=openadapt
export AWS_BACKUP_BUCKET='<CloudFormation BackupBucketName>'
export AWS_RESTORE_ROLE_ARN='<CloudFormation BackupRestoreRoleArn>'
export BACKUP_STAMP='<YYYYMMDDTHHMMSSZ from S3>'
export PRODUCTION_PROJECT_REF='<exact production project ref>'
export SCRATCH_PROJECT_REF='<new scratch project ref>'
export CONFIRM_SCRATCH_PROJECT_REF="$SCRATCH_PROJECT_REF"
export SCRATCH_DB_URL='<new scratch PostgreSQL URL>'
export AGE_SECRET_KEY_FILE='<absolute path to the private age key>'

scripts/run_database_restore_drill.sh
```

The script:

1. validates that the scratch URL belongs to the repeated scratch project;
2. assumes the least-privilege restore role in AWS account `992382684924`;
3. checks S3 public-access blocking;
4. downloads the exact timestamped ciphertext and manifest;
5. verifies the S3 metadata digest and the artifact contract;
6. decrypts into a private temporary directory;
7. extracts only four exact regular files and rejects unsafe archive members;
8. restores with `ON_ERROR_STOP` in one transaction;
9. dumps the scratch schema and data again and compares their digests;
10. writes a new database-only evidence file without overwriting old evidence;
11. uploads that metadata-only evidence below `drills/database-only/`; and
12. removes all temporary plaintext.

RTO starts before AWS role assumption and download. It ends after the scratch
database redump and validation. RPO is measured from the backup recovery point
to the same start time.

The script does not delete the scratch project. Review the evidence first.
Then decommission the project through its authorized owner process.

## Complete recovery evidence

Database-only evidence has:

```json
{
  "database_restored": true,
  "storage_restored": false
}
```

It cannot unlock destructive hosted retention and is not the canonical Cloud
restore receipt. After the database-only drill, run the database and private
Storage procedure in `openadapt-cloud/docs/RUNBOOK_DATA_SAFETY.md`:

1. `drill-storage-export`
2. `drill-prepare`
3. the exact roles, schema, and data dumps
4. `drill-storage-check-source`
5. scratch database restore
6. `drill-storage-restore`
7. `drill-verify` without `--record`
8. review the result
9. repeat `drill-verify` with `--record`

Only that result proves the complete declared database and Storage boundary.

## Recovery cost options

Prices can change. Verify the provider price before purchase.

| Option | Approximate monthly cost | Recovery point | Boundary |
|---|---:|---|---|
| This daily logical backup | S3 bytes and requests only; approximately USD 0.023/GB-month | Up to 24 hours when consecutive jobs pass | Database only |
| Supabase Pro | USD 25 base plan | Daily provider backup with seven-day history | Database only |
| Supabase PITR | About USD 100 for seven days, plus the required paid plan and minimum compute | Minutes, based on retained WAL | Database only |

References:

- <https://supabase.com/pricing>
- <https://supabase.com/docs/guides/platform/backups>
- <https://supabase.com/docs/guides/platform/point-in-time-recovery>
- <https://aws.amazon.com/s3/pricing/>

Do not enable PITR without a recorded cost decision. A logical backup and a
successful complete scratch drill are still required because provider database
recovery does not cover private Storage objects.

## Key rotation

For routine rotation:

1. Generate a new private key on a trusted device.
2. store it on the device and in the second vault or offline location;
3. replace the committed public recipient;
4. merge the change through code owner review;
5. confirm the next backup uses only the new recipient; and
6. keep the old private key until every old S3 object expires after 90 days.

If a private key is compromised, remove its public recipient immediately.
Rotate the production database credential because retained backups contain the
complete logical database. Treat all backups encrypted to the compromised key
as exposed. Do not keep encrypting new backups to both old and new recipients.

## Alerts and scheduled-workflow limits

A failed backup job stays red and opens or updates one durable GitHub issue.
The hourly `Production DB backup freshness` workflow uses a separate read-only
AWS role. It opens or updates one durable issue when the newest complete pair
is absent, stale, or inconsistent. A successful run closes its matching issue.

The two checks use different workflows and different AWS roles. They still use
the same GitHub scheduler. Configure one external monitor to alert when either
workflow stops running. The external monitor can inspect the workflow age or
assume a separate read-only role and inspect the newest S3 recovery point. Do
not give the external monitor the backup writer role.

GitHub can disable schedules after 60 days without repository activity. The
daily documentation sync currently keeps this repository active. Verify the
backup workflow enabled state during each quarterly drill. A schedule status
is not backup evidence; check the newest S3 recovery point and drill receipt.
