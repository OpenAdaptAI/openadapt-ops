# Production DB backup: keypair, restore drill, and paid-vs-free tradeoff

Companion to `.github/workflows/db-backup.yml` (daily encrypted logical backup)
and `.github/workflows/prod-health-alert.yml` (30-minute health pager).
Authoritative context: `openadapt-cloud` `AUDIT.md` finding (b) and
`docs/RUNBOOK_DATA_SAFETY.md` (the provider reported `pitr_enabled=false` and
zero physical backups on 2026-07-25).

**Threat model note — this repo is PUBLIC.** Workflow artifacts on a public
repo are downloadable by any logged-in GitHub user. The backup artifact is
therefore ciphertext only (`age`), encrypted to the public key committed in
`ops/backup/age-recipients.txt`. The private key exists only offline with the
founder. If the private key is ever exposed, rotate (section 5) and treat all
retained artifacts as exposed.

## 1. One-time founder setup: generate the age keypair

On a trusted machine (not CI):

```sh
brew install age   # or: apt-get install age
umask 077
age-keygen -o ~/openadapt-db-backup.agekey
```

`age-keygen` prints one line `# public key: age1...`.

1. Store `~/openadapt-db-backup.agekey` (the PRIVATE key) in the team vault
   (e.g. 1Password) AND on an offline copy. It never goes into this repo,
   GitHub secrets, or any CI log. Without it, every backup artifact is
   permanently unreadable.
2. Commit ONLY the public key: append the `age1...` line (just the key, no
   `# public key:` prefix) to `ops/backup/age-recipients.txt` on a branch and
   open a PR.
3. Set the database secret (value: the production Postgres connection string,
   Supabase dashboard -> Project Settings -> Database -> Connection string,
   direct or session-pooler URI):

```sh
gh secret set SUPABASE_DB_URL --repo OpenAdaptAI/openadapt-ops
```

The backup workflow fails loudly until both steps are done. That is
intentional: a red daily run is the reminder that production still has no
recovery point.

## 2. What each daily artifact contains

Artifact `db-backup-<UTC-stamp>` (retention 90 days):

- `db-backup-<stamp>.tar.gz.age` — age-encrypted tarball of the runbook
  triple: `roles.sql`, `schema.sql`, `data.sql` (`--use-copy --data-only`,
  excluding `storage.buckets_vectors` / `storage.vector_indexes`).
- `manifest.txt` — timestamps, run URL, plaintext and ciphertext SHA-256.

Storage buckets (bundles/reports/recordings) are NOT in this backup; database
PITR would not cover them either. Bucket export/restore stays with the cloud
runbook's `retention` drill tooling.

## 3. Restore drill (run on a scratch database, never prod)

Quarterly, or before any risky migration. Mirrors `RUNBOOK_DATA_SAFETY.md`
section 2 steps 6-8; the scratch project must be new, disposable, and in the
same regional/data-handling boundary as production.

```sh
umask 077
mkdir -p /secure/offline/openadapt-restore && cd /secure/offline/openadapt-restore

# 1. Download the newest artifact (list runs, then download by run id):
gh run list --repo OpenAdaptAI/openadapt-ops --workflow db-backup.yml --limit 5
gh run download <run-id> --repo OpenAdaptAI/openadapt-ops

# 2. Verify + decrypt with the founder-held private key:
cd db-backup-<stamp>
sha256sum db-backup-<stamp>.tar.gz.age   # must equal ciphertext_sha256 in manifest.txt
age -d -i ~/openadapt-db-backup.agekey \
  -o db-backup-<stamp>.tar.gz db-backup-<stamp>.tar.gz.age
sha256sum db-backup-<stamp>.tar.gz       # must equal plaintext_tar_sha256 in manifest.txt
tar -xzf db-backup-<stamp>.tar.gz        # -> roles.sql schema.sql data.sql

# 3. Create a brand-new scratch Supabase project (dashboard). Then restore
#    in one transaction, same order and flags as the cloud runbook:
psql --single-transaction --variable ON_ERROR_STOP=1 \
  --file roles.sql \
  --file schema.sql \
  --command 'SET session_replication_role = replica' \
  --file data.sql \
  --dbname "$SCRATCH_DB_URL"

# 4. Validate: row counts on runs/orgs/usage vs production expectations;
#    spot-check one recent run row. Record the wall-clock restore time (RTO).

# 5. Decommission the scratch project and delete the local plaintext:
rm -f roles.sql schema.sql data.sql db-backup-<stamp>.tar.gz
```

Restore caveats (same as PITR): after any real restore, reconcile Stripe by
replaying webhooks from the Stripe dashboard (`stripe_events` is idempotent),
and expect up to 24h of lost writes (see RPO below).

## 4. Can we get to a recovery point for $0 — and what does paying buy?

**Yes.** Once section 1 is done, this workflow gives a daily, encrypted,
off-provider logical recovery point at $0 (public repo: Actions minutes and
artifact storage are free; the Supabase Free plan itself includes no backups).

| Option | Monthly cost (Supabase public pricing, checked 2026-08-02) | RPO | Restore | Covers |
|---|---|---|---|---|
| This workflow (`pg_dump` daily, encrypted artifact, 90d retention) | $0 | up to 24h | manual, logical (`psql`), drill above; hours | DB only (roles+schema+data) |
| Supabase Pro (daily physical backups, 7-day retention) | $25 | up to 24h | dashboard-driven physical restore; also unlocks restore-to-new-project | DB only |
| Supabase Pro + PITR add-on | $25 + $100 per 7 days of PITR retention (+ compute add-on if the project is below the required tier, ~$10-15 net of Pro's $10 compute credit) | minutes | dashboard PITR to timestamp | DB only (WAL) |

**Recommendation:** buy Supabase Pro ($25/mo) now — it is the cheapest change
that adds provider-side physical backups and makes `provider-status
--require-recovery` pass, and hosted retention/deletion gating in
openadapt-cloud wants provider recovery evidence. Defer the PITR add-on
(~$110-140/mo all-in) until there is at least one paying pilot; at N=0
customers, a 24h RPO with a drilled restore path is a defensible posture, and
this workflow keeps an independent, off-provider copy either way. Revisit the
moment real customer billing/usage state is at stake.

## 5. Key rotation / compromise

1. Generate a new keypair (section 1); commit the new public key line.
2. Keep the old private key in the vault until every artifact encrypted to it
   has aged out (90 days), then destroy it.
3. If the private key was exposed: rotate immediately AND rotate the database
   credentials in `SUPABASE_DB_URL` (the artifacts contain full table data).

## 6. Alerting caveats (prod-health-alert.yml)

- GitHub emails the actor who last modified the workflow file when a scheduled
  run fails. Keep that account monitored.
- GitHub auto-disables scheduled workflows after 60 days with no repo
  activity. `sync.yml` commits docs daily, which keeps schedules alive; if the
  doc sync ever stops, both schedules here die silently ~60 days later —
  check Actions -> enabled state during any quarterly drill.
- Optional Telegram page: set the crier bot's `TELEGRAM_BOT_TOKEN` and
  `TELEGRAM_OWNER_ID` as repo secrets (commands in the workflow log) and the
  failure step will also message the founder directly.
