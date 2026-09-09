# Local database recovery point

Use `scripts/local_database_backup.py` to take an encrypted database backup on
an operator-controlled device. It uses the same Supabase 2.75.0 dump commands
and archive contract as the daily workflow. It doesn't need an AWS account or
a GitHub runner.

The command creates an archive only after it decrypts the ciphertext with the
retained key and verifies every recovered SQL file. That check proves the
archive can be decrypted. A separate database restore must still pass.

## Current limits

The local path can replace the unavailable runner and S3 path with a pinned
macOS job, private GitHub release assets, and a separate hosted freshness
check. Keep the existing alerts open until the first real capture, isolated
restore, remote readback, and replacement schedules pass.

The manual capture command accepts the production PostgreSQL password as an
explicit input. The scheduled command uses an existing task-owned temporary
read-only login through the documented Supabase Management API. The API token
isn't a database password. Do not reset the production
password to obtain a backup, and do not use a table-by-table API export as a
replacement for a database dump.

The command uses one exported read-only PostgreSQL snapshot for both schema
and data. It holds the exporting transaction open until both dumps complete.
It also compares roles before and after capture and refuses a changed role
set. It doesn't export private Storage objects or
provide a provider-independent snapshot of Supabase's managed services. Use
the complete Cloud recovery drill before a database-plus-Storage recovery
claim.

## Prepare the device and the credential

Use an encrypted local volume. Install Supabase CLI 2.75.0, native PostgreSQL17
tools, and `age`. This command doesn't start Docker. Keep the decryption key in a `0600` file and in a separate
vault or offline copy. A second file on the same device doesn't protect against
device loss.

Create a private backup directory, then enter the direct or session-pooler
PostgreSQL URL at the hidden prompt. The URL must belong to the exact project.
It must include the current password and use TLS. Don't put the URL in a shell
command, chat, issue, or pull request.

```sh
umask 077
mkdir -m 700 -p "$HOME/.config/openadapt/database-backup"
python scripts/local_database_backup.py configure \
  --project-ref '<production project reference>' \
  --output "$HOME/.config/openadapt/database-backup/source.json"
```

The prompt writes only that private file. It doesn't connect to the database.
It refuses an existing output file.

## Capture and verify

Run from the reviewed, clean source commit. The script captures subprocess
output privately because a client error can contain a connection string. A
failure returns a nonzero status and claims no new recovery point.

```sh
python scripts/local_database_backup.py capture \
  --source-config "$HOME/.config/openadapt/database-backup/source.json" \
  --backup-root "$HOME/.config/openadapt/database-backup/archives" \
  --identity "$HOME/.config/openadapt/keys/production-db-backup.agekey" \
  --recipients ops/backup/age-recipients.txt \
  --postgres-bin '<absolute PostgreSQL17 bin directory>' \
  --source-commit "$(git rev-parse HEAD)"
```

The native client receives a passwordless connection and a temporary `0600`
libpq password file. The script removes inherited PostgreSQL overrides and
requires TLS at the actual `pg_dump` connection. It generates the maintained
Supabase dump script with a fixed synthetic URL and removes exactly its five
connection exports before execution. No production password enters process
arguments or generated shell text. The source sessions are read-only.

Each UTC directory contains exactly these files:

- `database.tar.gz.age`: the encrypted roles, schema, data, and backup contract;
- `artifact-manifest.json`: sizes, hashes, source commit, and local execution identity;
- `local-verification.json`: the encryption round-trip result and explicit
  false values for database restore, Storage restore, and off-device verification.

The script removes its temporary plaintext on normal completion and handled
failure. A process kill or device crash can leave a private `.capture-*` or
`.backup-*` directory. Inspect it before removal. These directories contain
plaintext and must remain inside the encrypted device boundary.

## Off-device copy without a new cloud resource

The destination is an encrypted release asset in the existing private
`OpenAdaptAI/openadapt-internal` repository. It is a separate operation from
capture. Verify the repository is private immediately before upload. Upload
only `database.tar.gz.age` and `artifact-manifest.json`; keep the private key
off GitHub. Use a new timestamped tag and never replace a prior recovery point.

GitHub permits release assets below 2 GiB and documents no total release size
or bandwidth limit. The local command enforces the per-asset limit before it
claims a complete archive. This path uses neither Actions artifact storage nor
Git LFS. See [GitHub's release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).

Publish with the reviewed transport:

```sh
python scripts/private_database_backup_release.py \
  --archive '<absolute UTC archive directory>' \
  --source-commit '<exact commit in the private internal repository>'
```

The helper stages only the ciphertext and strict redacted manifest. It checks
private visibility before each upload, compares remote asset IDs, sizes, and
SHA-256 values, and downloads both assets for a byte comparison before it
publishes the release. It writes `github-release-receipt.json` only after the
published release and tag pass. Repeat the decryption check on the downloaded
ciphertext for the first off-device recovery proof. A failed attempt preserves
the local archive and remote draft. A failure after publication can leave a
published release without a local receipt; inspect that exact release before
another attempt.
An upload response alone isn't off-device recovery evidence. Do not install a
daily schedule until the first real backup and isolated restore both pass.

## Unpack for a scratch restore

Unpack only into a new private directory on the encrypted device:

```sh
python scripts/local_database_backup.py unpack \
  --archive '<absolute UTC archive directory>' \
  --identity "$HOME/.config/openadapt/keys/production-db-backup.agekey" \
  --output '<absolute new private directory>'
```

The command verifies the ciphertext and plaintext hashes, checks the exact
four-file archive allowlist, and checks each SQL component. It never connects
to a restore target. Restore into a new isolated Supabase target with the same
PostgreSQL major and required managed schemas. Use `psql -X`,
`ON_ERROR_STOP=1`, and one transaction for roles, schema, and data. Re-dump the
scratch schema and data with the same Supabase CLI version, then run:

```sh
python scripts/database_backup_contract.py verify-restored-dumps \
  --source-dir '<unpacked directory>' \
  --restored-dir '<scratch re-dump directory>'
```

The comparison permits only the documented random PostgreSQL restriction
guard. It must reject a changed schema or row. Record the exact backup,
target, start time, completion time, and result. Preserve all source backups
until the restore evidence passes. The [full restore runbook](RESTORE_DRILL.md)
defines the database-only receipt and the separate private-Storage drill.

## Isolated synthetic verification

The integration test initializes two new PostgreSQL clusters. They use local
connections and contain synthetic rows only. The source also binds a random
loopback port for the TLS refusal probe. It encrypts a real dump,
decrypts it, restores into the second cluster, compares complete schema/data
re-dumps, and checks an independent row count and sum. It then deletes one
synthetic row and requires the comparison to fail. Both servers stop in the
test cleanup. With PostgreSQL17, it also runs the actual native dump path,
changes the source schema and rows between the two dumps, and proves that the
restored snapshot retains the original schema and values. A plaintext control
can connect to the synthetic server; the TLS-required backup client refuses
that same server because it has no TLS certificate.

```sh
OPENADAPT_TEST_POSTGRES_BIN='<absolute PostgreSQL bin directory>' \
  python -m pytest tests/test_local_database_backup.py \
  tests/test_database_backup_contract.py -q
```

This test proves the local archive and comparison mechanics. It doesn't prove
that the production Supabase database restores.

## Daily capture and independent freshness

`scripts/local_database_backup_schedule.py` runs the reviewed temporary-login
capture and release transport under one local lock. It checks the exact Git
commit and each executed module before every run. It doesn't fetch new code or
accept jobs from a public repository.

The capture configuration is a private `0600` JSON file with exactly four
fields: `project_ref`, `management_token`, `owned_role_oid`, and `pooler_host`.
Obtain the token from the deployment configuration that already owns this
project. The role OID must come from the operator's recorded temporary-role
creation. The command refuses to adopt an unknown or already active role.

Each capture requests `read_only: true`, bounds the returned credential to ten
minutes, verifies the effective role and RLS bypass, and uses the shared
read-only snapshot. Cleanup disables login, expires the credential, terminates
only this operation's identified sessions, and verifies that none remain. The
provider role record stays because its creator can withhold the ADMIN grant
needed for an exact DROP. The command never uses the provider-wide role DELETE
endpoint. A cleanup failure prevents publication.

The schedule configuration is another private JSON file with these exact keys:

- `expected_backup_commit`: the reviewed Ops commit;
- `capture_config`: the absolute temporary-login configuration path;
- `backup_root`: the absolute private archive directory;
- `identity`: the existing age private key path;
- `recipients`: the reviewed public recipient file path;
- `postgres_bin`: the native PostgreSQL17 binary directory;
- `internal_commit`: the exact private repository commit for new release tags.

After a real restore and remote readback pass for the same archive, prepare the
04:00 local-time launchd job:

```sh
python scripts/local_database_backup_schedule.py setup \
  --config '<absolute private schedule configuration>' \
  --verified-archive '<absolute archive with matching restore and release receipts>' \
  --output '<absolute private review plist>'
```

Setup writes only a review file. It requires `restore-receipt.json` and
`github-release-receipt.json` to bind the same verified production archive.
Install the reviewed plist only after the end-to-end operation passes. Keep
the checkout pinned; update its source and configuration together after review.

Run `scripts/private_database_backup_freshness.py` from the independent private
repository's hosted workflow with a read-only `GITHUB_TOKEN`. The daily check
uses the manifest's capture time and fails above 26 hours. Drafts, release edits,
failed capture, and incomplete uploads cannot advance that time. At 13:00 UTC,
the check runs four to five hours after the local 04:00 Toronto capture. It can
report a missed backup while the Mac is offline.

The private check is expected to use about one standard Linux minute per
scheduled run, or up to31 scheduled minutes per month. This estimate is not a
billing cap. It can use the organization's included minutes, but it is not a
guarantee of zero future cost when other jobs consume that allowance. Keep its
one-minute timeout, read-only token, and no-install/no-cache/no-artifact design.
No Azure resource or unrestricted self-hosted GitHub runner is required.
