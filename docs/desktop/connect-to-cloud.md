# Connect the desktop app to a cloud workspace

The local loop — record, compile, replay, teach — works entirely offline and
needs no account. Connecting to a **cloud workspace** (`app.openadapt.ai`) adds an
org-wide dashboard where pushed workflows are visible and runs that need attention
are triaged. This page walks the whole path: sign in → mint an ingest token →
connect the desktop app → push your first recording → see it in the dashboard.

!!! note "Which lane are you in?"
    The cloud workspace is the **self-serve, non-PHI lane** — browser/web
    automation that does not carry regulated data. If you handle **PHI or other
    regulated data**, do **not** push to the cloud; use the
    [on-prem deployment](../guides/deploy-on-prem.md) instead, where recordings
    and teaching never leave your network. See
    [the hosted option](../guides/hosted.md).

!!! info "Hosted subscription"
    OpenAdapt Hosted is available as a public $500/month subscription for
    approved browser workflows. Start at
    [openadapt.ai](https://openadapt.ai/#pricing), then use the same workspace
    and ingest-token mechanism described below.

## 1. Create or sign in to your workspace

Sign in at [app.openadapt.ai](https://app.openadapt.ai) (Google or magic-link).
Your account resolves to exactly one **organization** — every token and workflow
belongs to that org.

## 2. Mint an ingest token

The desktop app authenticates to the cloud with a per-user **ingest token**
(`oai_ingest_…`). To mint one:

1. In the dashboard, open **Settings → Ingest tokens**
   (`app.openadapt.ai/dashboard/settings/ingest`).
2. Click **Create token** and give it a name (e.g. your machine name).
3. **Copy the token now.** It is shown **once** and stored server-side only as a
   hash — if you lose it, revoke it and mint a new one.

The token is presented as `Authorization: Bearer <token>` on every call and
resolves to your org. Revoke it any time from the same page.

## 3. Connect the desktop app

!!! note "Two first-class paths"
    The login flow below describes the desktop cockpit. The
    [CLI commands](install.md) shown alongside each step are the same mechanism,
    so you can use either surface interchangeably.

In the desktop app, open **Login** and either:

- **Click Login** — opens `app.openadapt.ai` in your system browser and completes
  sign-in there (Google / magic-link "just work"), or
- **Paste a token** — paste the `oai_ingest_…` token from step 2.

Either way the credential is stored in your OS secure store (macOS Keychain /
Windows Credential Manager / Linux Secret Service), not in a plaintext file.

Prefer the CLI? There are two ways to connect from a terminal.

**One-click pairing (recommended).** In the dashboard, click **Connect local
OpenAdapt** on the ingest settings page. Cloud shows a one-time pairing code and
the exact command:

```bash
openadapt connect --pairing oap_… --host https://app.openadapt.ai
```

The pairing code expires after five minutes and is single-use. The resulting
workspace credential is stored in your OS secure store and can be revoked in
Cloud settings.

!!! warning "`openadapt connect` requires OpenAdapt 1.7+"
    `connect` ships in the `openadapt` launcher from **1.7 onward**. On an older
    build (commonly an Anaconda-installed 1.5.x) it fails with
    `No such command 'connect'`. Run `pip install --upgrade openadapt` (≥1.7.1),
    then retry with a **fresh** pairing code (the old one will have expired). See
    [troubleshooting](../guides/troubleshooting.md#connect-no-such-command).

**Reusable token login.** For a scripted install or a second machine, mint a
token in step 2 and log in with it instead:

```bash
openadapt flow login --token oai_ingest_…      # validates + remembers the host
```

`login` resolves the token from `--token`, then the `OPENADAPT_INGEST_TOKEN`
environment variable, then `~/.openadapt/config.toml`. See the
[CLI reference](../reference/cli.md#login).

## 4. Push your first recording

Record a workflow (see [Record your own app](../guides/record-your-app.md)), then
push it. From the desktop app, use **Push to cloud** on the recording (where your
build includes it). From the CLI:

```bash
openadapt flow push ./my-recording --name "Triage"
#   → zips the recording, POSTs it to /api/ingest,
#     compiles it in the cloud, and prints a workflow id + dashboard URL
```

A recording directory is zipped before upload (the server ingests a `.zip`; the
engine emits a directory). You can also push an already-compiled bundle with
`--kind bundle`. See [`push`](../reference/cli.md#push).

!!! warning "Push scrubs, but the cloud lane is for non-PHI work"
    A pre-push scrub runs fail-closed and the server re-scans on ingest, but the
    cloud lane is **not** the PHI lane. Keep regulated recordings local and use
    [on-prem](../guides/deploy-on-prem.md).

## 5. See it in the dashboard

Open the dashboard URL that `push` printed (or go to
`app.openadapt.ai/dashboard/workflows`). The pushed workflow appears there,
compiled and runnable, and any run that halts and needs attention surfaces under
**Needs attention** for triage.

## Reporting a halt back to the workspace

When a governed run halts locally, you can send a **PHI-free** break descriptor to
the workspace so the halt is visible centrally, without the recording ever leaving
the machine:

```bash
openadapt flow report-break runs/replay-… \
    --workflow-id <id> --deployment-kind byoc
```

`report-break` reads the halt from the run's `report.json`, scrubs it fail-closed,
and posts only a descriptor. See [`report-break`](../reference/cli.md#report-break)
and [the halt-learn loop](../concepts/halt-learn-loop.md) for how a halt becomes a
taught correction.
