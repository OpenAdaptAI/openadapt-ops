---
description: >-
  Pair OpenAdapt Desktop or the CLI with an OpenAdapt Cloud workspace, approve
  local artifacts, and publish an attested workflow for governed operation.
---

# Connect the desktop app to a cloud workspace

OpenAdapt Desktop supplies the local record, compile, replay, and teach loop.
It works offline and needs no account.

A **cloud workspace** (`app.openadapt.ai`) adds an org-wide dashboard:
pushed workflows are visible and runs needing attention are triaged. This page
covers the path: sign in → mint an ingest token → connect the desktop app → push
a recording → see it in the dashboard.

!!! note "Which lane are you in?"
    The cloud workspace is the **self-serve, non-PHI/PII lane**: browser/web
    automation with no regulated data. For **PHI/PII or other regulated data**, do
    **not** push to the cloud; use the
    [on-prem deployment](../guides/deploy-on-prem.md) instead, where recordings
    and teaching never leave your network. See
    [the hosted option](../guides/hosted.md).

!!! info "Hosted subscription"
    OpenAdapt Hosted is a public $500/month subscription for approved browser
    workflows. Start at the
    [Cloud plan](https://openadapt.ai/pricing#cloud-preview), then use the same
    workspace and ingest-token mechanism below.

## 1. Create or sign in to your workspace

Sign in at [app.openadapt.ai](https://app.openadapt.ai) (Google or magic-link).
Each workspace action is scoped to exactly one active **organization**; every
token and workflow belongs to that organization.

The dashboard account menu shows the signed-in email and active organization.
It also provides **Security & 2FA**, organization switching when the account
belongs to multiple workspaces, and **Sign out**. See
[Account security and privileged access](../guides/account-security.md) for
authenticator setup and protected-session behavior.

## 2. Mint an ingest token

The desktop app authenticates with a per-user **ingest token** (`oai_ingest_…`).
To mint one:

1. In the dashboard, open **Settings → Ingest tokens**
   (`app.openadapt.ai/dashboard/settings/ingest`).
2. Click **Create token** and give it a name (e.g. your machine name).
3. **Copy the token now.** It is shown **once** and stored server-side only as a
   hash. If you lose it, revoke it and mint a new one.

The token is sent as `Authorization: Bearer <token>` on every call and resolves
to your org. Revoke it any time from the same page.

## 3. Connect the desktop app

!!! note "Two first-class paths"
    The flow below describes the desktop cockpit; the [CLI commands](install.md)
    shown alongside are the same mechanism, so either surface works.

In the desktop app, open **Login** and either:

- **Click Login**: opens `app.openadapt.ai` in your system browser and completes
  sign-in there (Google / magic-link "just work"), or
- **Paste a token**: paste the `oai_ingest_…` token from step 2.

Either way the credential is stored in your OS secure store (macOS Keychain /
Windows Credential Manager / Linux Secret Service), not a plaintext file.

Prefer the CLI? Two ways to connect from a terminal.

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
token in step 2 and log in with it:

```bash
openadapt flow login --token oai_ingest_…      # validates + remembers the host
```

`login` resolves the token from `--token`, then the `OPENADAPT_INGEST_TOKEN`
environment variable, then `~/.openadapt/config.toml`. See the
[CLI reference](../reference/cli.md#login).

## 4. Register the recording, then publish the governed bundle

Record a workflow (see [Record your own app](../guides/record-your-app.md)), then
create, review, approve, and register its sanitized derivative. From the desktop
app, use **Push to cloud** on the approved recording. Or use the CLI:

```bash
openadapt flow push ./my-recording --name "Triage"
#   → prepares the local derivative and opens review when approval is needed
```

Recording registration preserves the exact approved source and returns its next
validation step; it does not turn a recording into a runnable workflow. Compile
the approved derivative locally, run strict lint, certification, and a governed
replay, then sanitize and approve the bundle, run `validate-hosted`, and push the
exact attested bundle. The complete copy-and-paste sequence is in
[OpenAdapt Hosted](../guides/hosted.md#exact-local-to-hosted-sequence) and the
[`push` reference](../reference/cli.md#push).

!!! warning "Push scrubs, but the cloud lane is for non-PHI/PII work"
    A pre-push scrub runs fail-closed and the server re-scans on ingest, but the
    cloud lane is **not** the PHI/PII lane. Keep regulated recordings local and use
    [on-prem](../guides/deploy-on-prem.md).

## 5. See the governed workflow in the dashboard

After the attested bundle is accepted, open the dashboard URL that `push`
printed (or go to `app.openadapt.ai/dashboard/workflows`). The governed workflow
and its active bundle appear together; any run that halts surfaces under
**Needs attention** for triage.

## Reporting a halt back to the workspace

Cloud signs and delivers a task to the registered runner. The runner remains
the execution authority: it reads the local application, enforces the workflow
policy, and returns its result. Cloud does not execute the local application.

When a governed run halts locally, send a **PHI/PII-free** break descriptor to the
workspace so the halt is visible centrally, without the recording ever leaving
the machine:

```bash
openadapt flow report-break runs/replay-… \
    --workflow-id <id> --deployment-kind byoc
```

`report-break` reads the halt from the run's `report.json`, scrubs it fail-closed,
and posts only a descriptor. See [`report-break`](../reference/cli.md#report-break)
and [the halt-learn loop](../concepts/halt-learn-loop.md) for how a halt becomes a
taught correction.
