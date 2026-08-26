# Production database backup and restore drill

This runbook owns the off-provider logical database backup in
`.github/workflows/db-backup.yml`. It complements the complete database and
private-Storage restore drill in `openadapt-cloud/docs/RUNBOOK_DATA_SAFETY.md`.

## Current state

The design target is:

- one logical database backup every 12 hours after paid-customer activation;
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

- no scheduled backup has completed;
- no scratch restore has completed;
- no measured RTO exists;
- provider PITR is not enabled;
- the AWS stack is not deployed;
- `main` has no repository ruleset or branch protection;
- no workflow-restricted production backup runner group or runner is confirmed;
- the `production-backup` GitHub environment has none of its four required
  settings and has no deployment-branch restriction;
- the `production-backup-monitor` GitHub environment is not configured;
- no scratch Supabase project is configured; and
- one local private `age` key exists, but its required second vault or offline
  copy is not confirmed.

Do not describe the database as recoverable until one scheduled backup and one
isolated restore drill pass.

The empty bucket, OIDC provider, and IAM roles have no fixed storage charge.
The backup and freshness jobs stay inactive until Ops verifies a paid-customer
recovery admission. They don't request AWS credentials or open a stale-backup
issue before that admission exists. S3 starts billing only after the first
encrypted backup enters the bucket.

## Security boundary

This repository is public. Production database bytes must never enter a
GitHub artifact, workflow log, pull-request attachment, or public release.

The workflow writes only these objects to a private S3 bucket:

- `daily/<UTC-stamp>/db-backup-<UTC-stamp>.tar.gz.age`, which is `age`
  ciphertext stored directly in S3 Glacier Instant Retrieval; and
- `daily/<UTC-stamp>/artifact-manifest.json`, which contains sizes, digests,
  the source commit, and the workflow run ID. The manifest stays in S3
  Standard. It contains no project name, database URL, table data, or
  credential.

Both writes use `If-None-Match: *`. A repeated timestamp can't replace either
object. The workflow retains and verifies each returned S3 `VersionId`, so a
restore reads the exact pair that passed upload verification.

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
6. Create the `production-backup-activation` GitHub environment. Give it the
   same single custom `main` branch policy.
7. Create an organization runner group named `production-backup`. Permit only
   this repository. Restrict it to
   `OpenAdaptAI/openadapt-ops/.github/workflows/db-backup.yml@refs/heads/main`.
   Do not put the runner in the default group and do not permit another
   workflow to use the group.
8. Create a second group named `production-backup-activation`. Restrict it to
   `OpenAdaptAI/openadapt-ops/.github/workflows/db-backup-activate.yml@refs/heads/main`.
   This runner has the encrypted local `age` key, the `openadapt` AWS profile,
   and access to the isolated scratch database. Don't add an OIDC subject for
   this workflow. The restore script assumes the existing exact restore role.
9. Register an ephemeral Linux runner inside the declared OpenAdapt production
   boundary and put it only in the `production-backup` group. Use a clean
   encrypted work volume for each job and remove the runner after the job.
   Permit network access only to GitHub Actions, the exact production Supabase
   database endpoints, and the private AWS backup target.
10. Register a separate encrypted activation runner in the activation group.
    It needs `aws`, `age`, `psql`, `jq`, and Supabase CLI 2.75.0. Keep the
    private key outside the GitHub checkout and GitHub secrets.
11. Do not require a manual environment approval. An approval wait would prevent
   the scheduled jobs.

Verify that `main` reports as protected. Verify that each environment reports
`custom_branch_policies: true`, `protected_branches: false`, and one policy with
the exact name `main`. Both workflows repeat this check after the environment
admits the job and before they request AWS credentials. The job has read-only
Actions permission for this API check. Do not deploy the AWS stack until this
gate passes. Also verify that the runner group is restricted to the exact
workflow and that the selected runner reports `self-hosted`. A self-hosted
runner attached to this public repository without the exact workflow
restriction is unsafe because pull-request code can target it.

## One-time AWS setup

The CloudFormation template creates:

- a private, versioned S3 bucket;
- public-access blocking and a TLS-only bucket policy;
- direct S3 Glacier Instant Retrieval storage for encrypted archives;
- S3 Standard storage for redacted manifests;
- 90-day retention for twice-daily backups;
- 365-day retention for database-only drill evidence;
- a GitHub OIDC writer role bound to the exact `production-backup`
  environment;
- a read-only GitHub OIDC monitor role bound to the exact
  `production-backup-monitor` environment; and
- a local restore role bound to one exact AWS operator principal.

S3 Glacier Instant Retrieval in `us-east-1` costs approximately USD 0.004 per
GB-month as of 2026-08-26. The steady-state ciphertext estimate is:

`encrypted archive GiB x 2 backups/day x 90 days x USD 0.004`

At 0.1 GiB per encrypted archive, that is about USD 0.07 each month. A 0.5 GiB
archive is about USD 0.36, and a 1 GiB archive is about USD 0.72. S3 also bills
small request and restore-read charges. The workflow records the exact archive
bytes and GiB in its run summary so the estimate can use measured data.
Redacted manifests stay in S3 Standard and add a negligible amount at this
scale. Signed activation-stage JSON stays in Standard for 365 days and is also
negligible. The template does not create a paid KMS key or enable Supabase PITR.
It also doesn't enable paid S3 metrics, CloudTrail data events, Storage Lens,
CloudWatch alarms, or custom monitoring. The hourly GitHub monitor uses the
read-only role and standard S3 API calls only after activation.

Glacier Instant Retrieval has a 128 KiB minimum billable object size and a
90-day minimum storage duration. The encrypted archives exceed that size in
normal operation, and the 90-day lifecycle matches the minimum duration. The
manifest remains in Standard so the hourly monitor can read it without an
archive retrieval charge.

The backup workflow uses one S3 `PutObject` with a caller-supplied full-object
SHA-256. S3 validates that checksum before it accepts the object. This launch
path refuses an encrypted archive above 5 GiB before upload. Build and qualify a
multipart contract before a production database can exceed that limit.

The bucket policy refuses a daily ciphertext upload unless its storage class is
`GLACIER_IR`. It also refuses a daily manifest upload unless its storage class
is `STANDARD`. The writer, monitor, and restore paths read the live bucket controls before
they use an object. They require AWS account `992382684924`, region
`us-east-1`, complete public-access blocking, SSE-S3, versioning,
bucket-owner-enforced ownership, the exact 90-day and 365-day lifecycle rules,
TLS-only transport, and the exact encryption policy. A drifted target stops the
operation before database access or recovery-point selection.

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
   - `PAYMENT_SIGNAL_HMAC_KEY`: verifies the bounded first-payment request
   - `READINESS_RECEIPT_HMAC_KEY`: signs the database recovery receipt
   - `CLOUD_ACTIVATION_ACK_HMAC_KEY`: verifies Cloud's activation acknowledgment
   - `OPS_ACTIVATION_STATE_HMAC_KEY`: signs immutable activation-stage records
3. Keep these repository variables unset before the first paid customer:
   - `DATABASE_BACKUP_SCHEDULE_ENABLED`
   - `DATABASE_BACKUP_SCHEDULE_ADMISSION_B64`
4. Set `production-backup-monitor` environment variables from the
   CloudFormation outputs:
   - `AWS_BACKUP_BUCKET`
   - `AWS_BACKUP_MONITOR_ROLE_ARN`
5. Set `production-backup-activation` environment variables:
   - `AWS_BACKUP_BUCKET`
   - `AWS_RESTORE_ROLE_ARN`
   - `AGE_SECRET_KEY_FILE`: an absolute path on the encrypted activation runner
   - `CLOUD_BACKUP_READINESS_URL`
   - `CLOUD_BACKUP_READINESS_STATUS_URL`
6. Set `production-backup-activation` environment secrets:
   - `PAYMENT_SIGNAL_HMAC_KEY`
   - `READINESS_RECEIPT_HMAC_KEY`
   - `CLOUD_ACTIVATION_ACK_HMAC_KEY`
   - `OPS_ACTIVATION_STATE_HMAC_KEY`
   - `CLOUD_BACKUP_READINESS_TOKEN`
   - `SUPABASE_PROJECT_REF`
   - `SCRATCH_PROJECT_REF`
   - `SCRATCH_DB_URL`

The monitor environment has no secret. Its AWS role can list and inspect only
the `daily/` objects. It cannot create, replace, delete, download, or decrypt a
database backup.

The workflow validates that the URL belongs to the declared Supabase project.
It also checks AWS account `992382684924`, complete S3 public-access blocking,
and the committed `age` recipient before it reads the database.

The dump job does not use a GitHub-hosted runner. The complete database exists
in plaintext on the isolated backup runner until local `age` encryption. The
cleanup trap removes the plaintext before the runner is destroyed. The
freshness monitor can use a GitHub-hosted runner because it reads only the
redacted manifest and S3 object metadata. It cannot read the ciphertext.

The public recipient is in `ops/backup/age-recipients.txt`. Store its private
key with mode `0600` on an encrypted trusted device. Make a second copy in a
team vault or an offline medium before the first backup. Without a second copy,
one device loss makes all retained backups unreadable.

## Paid-customer activation contract

Don't dispatch a database backup before a paid customer exists. The workflow
has no manual write trigger. Its reusable interface accepts a base64-encoded,
signed first-payment request and a deterministic UTC recovery-point stamp. A
normal scheduled run requires both `DATABASE_BACKUP_SCHEDULE_ENABLED=true` and
a currently valid signed schedule admission.

The first-payment request binds the organization and payment-event digests,
the managed-browser offer, USD 500.00, paid status, verification time, a
15-minute validity window, and a deterministic activation ID. Payment code can
send that signed request. It doesn't get an AWS role or AWS credentials.

Keep the organization in `PENDING_RECOVERY` while Ops does this work:

1. validate the signed first-payment request;
2. create and verify one encrypted database backup;
3. restore the exact ciphertext and manifest S3 versions to the isolated
   scratch project;
4. issue the deterministic signed database-readiness receipt;
5. send that receipt to Cloud with the activation ID as the idempotency key;
6. if delivery is uncertain, query Cloud for that idempotency key instead of
   sending a blind second activation request;
7. accept only a signed Cloud acknowledgment that binds the exact
   organization, activation ID, receipt digest, and `PENDING_RECOVERY` to
   `ACTIVE` transition; and
8. store the combined signed admission, then set
   `DATABASE_BACKUP_SCHEDULE_ENABLED=true`.

The state machine accepts a byte-identical retry at each completed stage and
refuses a conflicting retry. Each completed stage has a signed, create-exclusive
record below `activation/<activation-id>/`. A retry loads and verifies the
highest stage. It doesn't repeat a completed backup, restore, receipt, or Cloud
callback. A failed backup, restore, receipt check, or Cloud acknowledgment
leaves the organization pending. It doesn't enable scheduled writes.

The Ops repository now defines and tests these request, state, receipt,
acknowledgment, and schedule-admission contracts in
`scripts/database_backup_activation.py`. Cloud still needs to implement the
exact payment-signal caller, pending-organization write gate, activation
endpoint, status query, and signed acknowledgment. Until that integration and
the protected environments and runners exist, leave both schedule variables
unset.

For the first backup, require all of these results:

- the workflow succeeds on the exact `main` commit;
- S3 contains one ciphertext object and one redacted manifest below the same
  UTC stamp;
- the stored SHA-256 checksum equals the local upload checksum;
- S3 reports the exact caller-supplied full-object SHA-256 for the ciphertext;
- the workflow binds the exact ciphertext and manifest `VersionId` values;
- the encrypted archive is no more than the enforced 5 GiB launch limit;
- no GitHub Actions artifact exists for the run; and
- the separate read-only freshness workflow selects the same recovery point,
  validates the redacted manifest digest, matches the S3 object size and remote
  checksum, proves `GLACIER_IR` ciphertext plus a `STANDARD` manifest, and
  reports an age of less than 24 hours.

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
export BACKUP_CIPHERTEXT_VERSION_ID='<verified ciphertext VersionId>'
export BACKUP_MANIFEST_VERSION_ID='<verified manifest VersionId>'
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
4. downloads the exact verified ciphertext and manifest versions;
5. verifies the S3 metadata digest and the artifact contract;
6. decrypts into a private temporary directory;
7. extracts only four exact regular files and rejects unsafe archive members;
8. restores with `ON_ERROR_STOP` in one transaction;
9. dumps the scratch schema and data again, normalizes only the matched random
   PostgreSQL restriction guard outside `COPY` data, and compares their
   digests;
10. writes a new database-only evidence file without overwriting old evidence;
11. uploads that metadata-only evidence below `drills/database-only/`; and
12. removes all temporary plaintext.

RTO starts before AWS role assumption and download. It ends after the scratch
database redump and validation. RPO is measured from the backup recovery point
to the same start time.

Patched PostgreSQL clients create a new `\restrict` key for each plain-text
dump. Supabase CLI comments that key, so two correct dumps have different raw
digests. The verifier keeps the raw source digests in the evidence and uses a
second comparison digest that replaces only one matched `restrict` and
`unrestrict` pair outside `COPY` blocks. A guard-shaped database value remains
data and a changed value still fails the drill.

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
| This logical backup every 12 hours | Ciphertext storage is approximately USD 0.004/GiB-month in Glacier Instant Retrieval, plus requests and restore reads | Up to 24 hours when consecutive jobs pass | Database only |
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

A failed admitted backup job stays red and opens or updates one durable GitHub
issue. Before activation, the backup and freshness jobs are inactive. They
don't report an empty bucket as a success or a failure.

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

## Zero-customer shutdown

Don't stop the backup or freshness monitor when one customer cancels. Keep
both active while any paid or pending customer data remains, while retention or
deletion work is incomplete, or while the final encrypted backup remains in
its 90-day retention window.

Cloud can request shutdown only with the signed deactivation contract in
`scripts/database_backup_activation.py`. It must prove all of these facts:

- paid customer count is zero;
- pending customer count is zero;
- no customer data remains;
- required retention and deletion work is complete;
- the final backup retention time has expired; and
- the request binds the active schedule admission and the complete
  `openadapt.zero-customer-backup-shutdown-proof/v1` record.

The proof record binds Cloud's entitlement-ledger revision, Cloud revision,
retention receipt, deletion receipt, customer counts, data-presence result,
final-backup expiry, and observation time. Its `proof_revision_sha256` is the
SHA-256 digest of the canonical inner proof object. Canonical JSON uses sorted
keys, no extra whitespace, and UTF-8 encoding.

The request has a 15-minute validity window and a direction-specific signing
key. Protected Ops issues one deterministic signed deactivation authorization
for an exact request. A byte-identical retry returns the same authorization. A
conflicting retry or any incomplete proof is refused. Only a protected Ops
settings workflow can apply that authorization and record the resulting
disabled schedule and monitor state. It must retain the empty S3, IAM, and OIDC
control stack. Don't delete that stack as part of customer cancellation.
