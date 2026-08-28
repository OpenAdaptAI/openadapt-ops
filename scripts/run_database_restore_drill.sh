#!/usr/bin/env bash
set -euo pipefail

# Restore one encrypted production backup to a separate scratch Supabase
# project. This stays on an operator-controlled machine so the age private key
# never enters GitHub. It never creates or deletes a project.

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

required=(
  AWS_BACKUP_BUCKET
  AWS_RESTORE_ROLE_ARN
  BACKUP_STAMP
  BACKUP_CIPHERTEXT_VERSION_ID
  BACKUP_MANIFEST_VERSION_ID
  PRODUCTION_PROJECT_REF
  SCRATCH_DB_URL
  SCRATCH_PROJECT_REF
  AGE_SECRET_KEY_FILE
)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "error: ${name} is required" >&2
    exit 2
  fi
done
if [[ ! "$BACKUP_STAMP" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
  echo 'error: BACKUP_STAMP is invalid' >&2
  exit 2
fi
if [[ "${CONFIRM_SCRATCH_PROJECT_REF:-}" != "$SCRATCH_PROJECT_REF" ]]; then
  echo 'error: repeat SCRATCH_PROJECT_REF in CONFIRM_SCRATCH_PROJECT_REF' >&2
  exit 2
fi
if [[ ! -f "$AGE_SECRET_KEY_FILE" ]]; then
  echo 'error: AGE_SECRET_KEY_FILE does not exist' >&2
  exit 2
fi
if [[ ! "$AWS_RESTORE_ROLE_ARN" =~ ^arn:aws:iam::992382684924:role/[A-Za-z0-9+=,.@_/-]+$ ]]; then
  echo 'error: AWS_RESTORE_ROLE_ARN is not an OpenAdapt account role' >&2
  exit 2
fi
if [[ "$(uname -s)" == 'Darwin' ]]; then
  key_mode=$(stat -f '%Lp' "$AGE_SECRET_KEY_FILE")
else
  key_mode=$(stat -c '%a' "$AGE_SECRET_KEY_FILE")
fi
if (( (8#$key_mode & 077) != 0 )); then
  echo 'error: AGE_SECRET_KEY_FILE must not be readable by group or other users' >&2
  exit 2
fi
private_recipient=$(age-keygen -y "$AGE_SECRET_KEY_FILE")
if ! grep -Fqx "$private_recipient" ops/backup/age-recipients.txt; then
  echo 'error: AGE_SECRET_KEY_FILE does not match a committed backup recipient' >&2
  exit 2
fi

root=$(mktemp -d "${TMPDIR:-/tmp}/openadapt-db-restore.XXXXXX")
chmod 700 "$root"
cleanup() {
  find "$root" -type f -exec chmod 600 {} + 2>/dev/null || true
  rm -rf "$root"
}
trap cleanup EXIT INT TERM

started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python scripts/database_backup_contract.py validate-restore-target \
  --source-project-ref "$PRODUCTION_PROJECT_REF" \
  --scratch-project-ref "$SCRATCH_PROJECT_REF" \
  --scratch-db-url "$SCRATCH_DB_URL"

if [[ "${RESTORE_ROLE_SESSION_READY:-false}" == 'true' ]]; then
  caller_arn=$(aws sts get-caller-identity --query Arn --output text)
  role_name=${AWS_RESTORE_ROLE_ARN##*/}
  if [[ ! "$caller_arn" =~ ^arn:aws:sts::992382684924:assumed-role/${role_name}/[A-Za-z0-9+=,.@_-]+$ ]]; then
    echo 'error: the ambient session is not the exact configured restore role' >&2
    exit 2
  fi
else
  read -r AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN < <(
    AWS_PROFILE="${AWS_PROFILE:-openadapt}" aws sts assume-role \
      --role-arn "$AWS_RESTORE_ROLE_ARN" \
      --role-session-name "openadapt-db-restore-${BACKUP_STAMP}" \
      --duration-seconds 3600 \
      --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
      --output text
  )
  export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
  unset AWS_PROFILE
fi

account=$(aws sts get-caller-identity --query Account --output text)
if [[ "$account" != '992382684924' ]]; then
  echo 'error: AWS_PROFILE does not resolve to OpenAdapt account 992382684924' >&2
  exit 2
fi
scripts/check_live_database_backup_target.sh "$AWS_BACKUP_BUCKET"

cipher="db-backup-${BACKUP_STAMP}.tar.gz.age"
plain="db-backup-${BACKUP_STAMP}.tar.gz"
prefix="daily/${BACKUP_STAMP}"
aws s3api get-object-attributes \
  --bucket "$AWS_BACKUP_BUCKET" \
  --key "${prefix}/artifact-manifest.json" \
  --version-id "$BACKUP_MANIFEST_VERSION_ID" \
  --object-attributes ObjectSize,StorageClass \
  --expected-bucket-owner 992382684924 \
  > "$root/manifest-attributes.json"
aws s3api get-object-attributes \
  --bucket "$AWS_BACKUP_BUCKET" --key "${prefix}/${cipher}" \
  --version-id "$BACKUP_CIPHERTEXT_VERSION_ID" \
  --object-attributes ObjectSize,StorageClass \
  --expected-bucket-owner 992382684924 \
  > "$root/ciphertext-attributes.json"
python scripts/database_backup_contract.py verify-storage-classes \
  --manifest-attributes "$root/manifest-attributes.json" \
  --ciphertext-attributes "$root/ciphertext-attributes.json"
aws s3api get-object --bucket "$AWS_BACKUP_BUCKET" \
  --key "${prefix}/${cipher}" \
  --version-id "$BACKUP_CIPHERTEXT_VERSION_ID" \
  --expected-bucket-owner 992382684924 "$root/$cipher" > /dev/null
aws s3api get-object --bucket "$AWS_BACKUP_BUCKET" \
  --key "${prefix}/artifact-manifest.json" \
  --version-id "$BACKUP_MANIFEST_VERSION_ID" \
  --expected-bucket-owner 992382684924 \
  "$root/artifact-manifest.json" > /dev/null

remote_sha=$(aws s3api head-object \
  --bucket "$AWS_BACKUP_BUCKET" --key "${prefix}/${cipher}" \
  --version-id "$BACKUP_CIPHERTEXT_VERSION_ID" \
  --expected-bucket-owner 992382684924 \
  --query 'Metadata.sha256' --output text)
local_sha=$(shasum -a 256 "$root/$cipher" | awk '{print $1}')
if [[ "$remote_sha" != "$local_sha" ]]; then
  echo 'error: downloaded ciphertext digest does not match S3 metadata' >&2
  exit 2
fi
python scripts/database_backup_contract.py verify-artifact \
  --manifest "$root/artifact-manifest.json" \
  --ciphertext-archive "$root/$cipher"

age -d -i "$AGE_SECRET_KEY_FILE" -o "$root/$plain" "$root/$cipher"
mkdir -m 700 "$root/recovered" "$root/redump"
python scripts/database_backup_contract.py extract-artifact \
  --plaintext-archive "$root/$plain" \
  --manifest "$root/artifact-manifest.json" \
  --output-dir "$root/recovered"

precheck_result=0
set +e
supabase db dump --db-url "$SCRATCH_DB_URL" -f "$root/redump/schema.sql" \
  || precheck_result=$?
if [[ "$precheck_result" -eq 0 ]]; then
  supabase db dump --db-url "$SCRATCH_DB_URL" -f "$root/redump/data.sql" \
    --use-copy --data-only \
    -x 'storage.buckets_vectors' -x 'storage.vector_indexes' \
    || precheck_result=$?
fi
if [[ "$precheck_result" -eq 0 ]]; then
  python scripts/database_backup_contract.py verify-restored-dumps \
    --source-dir "$root/recovered" --restored-dir "$root/redump" \
    > "$root/verification.json" || precheck_result=$?
fi
set -e

if [[ "$precheck_result" -eq 0 ]]; then
  echo 'The scratch database already matches the exact backup. Restore actuation is skipped.'
else
  rm -f "$root/redump/schema.sql" "$root/redump/data.sql" \
    "$root/verification.json"
  PGDATABASE="$SCRATCH_DB_URL" psql \
    --single-transaction --variable ON_ERROR_STOP=1 \
    --file "$root/recovered/roles.sql" \
    --file "$root/recovered/schema.sql" \
    --command 'SET session_replication_role = replica' \
    --file "$root/recovered/data.sql"
  supabase db dump --db-url "$SCRATCH_DB_URL" -f "$root/redump/schema.sql"
  supabase db dump --db-url "$SCRATCH_DB_URL" -f "$root/redump/data.sql" \
    --use-copy --data-only \
    -x 'storage.buckets_vectors' -x 'storage.vector_indexes'
  python scripts/database_backup_contract.py verify-restored-dumps \
    --source-dir "$root/recovered" --restored-dir "$root/redump" \
    > "$root/verification.json"
fi
completed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

output=${RESTORE_EVIDENCE_OUTPUT:-restore-evidence-${BACKUP_STAMP}.json}
python scripts/database_backup_contract.py record-restore \
  --manifest "$root/artifact-manifest.json" \
  --contract "$root/recovered/backup-contract.json" \
  --verification "$root/verification.json" \
  --source-project-ref "$PRODUCTION_PROJECT_REF" \
  --scratch-project-ref "$SCRATCH_PROJECT_REF" \
  --started-at "$started_at" --completed-at "$completed_at" \
  --aws-account-id 992382684924 --aws-region "${AWS_REGION:-us-east-1}" \
  --bucket-name "$AWS_BACKUP_BUCKET" \
  --ciphertext-key "${prefix}/${cipher}" \
  --ciphertext-version-id "$BACKUP_CIPHERTEXT_VERSION_ID" \
  --manifest-key "${prefix}/artifact-manifest.json" \
  --manifest-version-id "$BACKUP_MANIFEST_VERSION_ID" \
  --output "$output"
chmod 600 "$output"
aws s3 cp "$output" \
  "s3://${AWS_BACKUP_BUCKET}/drills/database-only/${BACKUP_STAMP}/$(basename "$output")" \
  --only-show-errors --sse AES256 --storage-class STANDARD \
  --content-type application/json \
  --checksum-algorithm SHA256 --expected-bucket-owner 992382684924
echo "Database-only restore evidence: $output"
echo 'Run the openadapt-cloud database-plus-Storage drill before recording the canonical retention receipt.'
