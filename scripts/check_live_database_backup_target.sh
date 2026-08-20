#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  echo 'error: one backup bucket name is required' >&2
  exit 2
fi

bucket=$1
expected_account=992382684924
account=$(aws sts get-caller-identity --query Account --output text)
if [[ "$account" != "$expected_account" ]]; then
  echo "error: AWS credentials do not resolve to account ${expected_account}" >&2
  exit 2
fi

root=$(mktemp -d "${TMPDIR:-/tmp}/openadapt-db-backup-target.XXXXXX")
chmod 700 "$root"
cleanup() {
  find "$root" -type f -delete 2>/dev/null || true
  rmdir "$root" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

aws s3api get-public-access-block --bucket "$bucket" \
  --expected-bucket-owner "$expected_account" > "$root/public-access.json"
aws s3api get-bucket-encryption --bucket "$bucket" \
  --expected-bucket-owner "$expected_account" > "$root/encryption.json"
aws s3api get-bucket-versioning --bucket "$bucket" \
  --expected-bucket-owner "$expected_account" > "$root/versioning.json"
aws s3api get-bucket-ownership-controls --bucket "$bucket" \
  --expected-bucket-owner "$expected_account" > "$root/ownership.json"
aws s3api get-bucket-location --bucket "$bucket" \
  --expected-bucket-owner "$expected_account" > "$root/location.json"
aws s3api get-bucket-lifecycle-configuration --bucket "$bucket" \
  --expected-bucket-owner "$expected_account" > "$root/lifecycle.json"
aws s3api get-bucket-policy --bucket "$bucket" \
  --expected-bucket-owner "$expected_account" > "$root/policy.json"

python scripts/check_database_backup_target.py \
  --bucket "$bucket" \
  --public-access-block "$root/public-access.json" \
  --encryption "$root/encryption.json" \
  --versioning "$root/versioning.json" \
  --ownership "$root/ownership.json" \
  --location "$root/location.json" \
  --lifecycle "$root/lifecycle.json" \
  --policy "$root/policy.json"
