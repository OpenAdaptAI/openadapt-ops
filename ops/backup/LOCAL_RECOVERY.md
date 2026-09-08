# Local database recovery point

Use `scripts/local_database_backup.py` to take an encrypted database backup on
an operator-controlled device. It uses the same Supabase 2.75.0 dump commands
and archive contract as the daily workflow. It doesn't need an AWS account or
a GitHub runner.

The command creates an archive only after it decrypts the ciphertext with the
retained key and verifies every recovered SQL file. That check proves the
archive can be decrypted. A separate database restore must still pass.

## Current limits

The local command doesn't repair the scheduled workflow or its freshness
monitor. Those jobs still require their protected environments, restricted
runner, and AWS target. Don't close their alerts because a local backup exists.

The production PostgreSQL password is an explicit input. The Supabase
Management API token isn't a database password. Do not reset the production
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

The proposed destination is an encrypted release asset in the existing private
`OpenAdaptAI/openadapt-internal` repository. It is a separate operation from
capture. Verify the repository is private immediately before upload. Upload
only `database.tar.gz.age` and `artifact-manifest.json`; keep the private key
off GitHub. Use a new timestamped tag and never replace a prior recovery point.

GitHub permits release assets below 2 GiB and documents no total release size
or bandwidth limit. The local command enforces the per-asset limit before it
claims a complete archive. This path uses neither Actions artifact storage nor
Git LFS. See [GitHub's release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).

After upload, require the remote asset size and SHA-256 to match the local
manifest. Download both assets into a new private directory and repeat the
artifact and decryption checks. Retain the resulting receipt separately.
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
