---
description: >-
  Choose where workflows run: on a computer you control, fully offline, with
  an optional on-site model server, or connected to OpenAdapt Cloud.
---

# Deploy

The engine always runs where the application is: on a computer that can open
the app. What changes between deployments is what that computer may talk to.

| Deployment | What talks to what | Use it when |
|---|---|---|
| Local | Nothing leaves the computer | Building and testing workflows |
| On-premises, offline | Nothing leaves your network; a firewall denies outbound traffic | Patient data or other regulated data |
| On-premises with a model server | Runners call a GPU server on your own network | You need model help for hard screens and can't send screens outside |
| Connected to OpenAdapt Cloud | The computer calls `app.openadapt.ai` over outgoing HTTPS | Shared workspaces, managed browser runs, fleet reports |

A run makes no outbound calls by default. Model grounding is off unless the
deployment file sets `runtime.allow_model_grounding: true` or you pass
`--allow-model-grounding`.

## On-premises, offline

The offline package is in
[`packages/flow/deploy/on-prem`](https://github.com/OpenAdaptAI/OpenAdapt/tree/main/packages/flow/deploy/on-prem).
It installs a versioned release from a local folder of wheels, sets up a
storage layout, a file-based job queue, a hash-chained audit log, and
systemd units:

```bash
cp onprem.example.yaml onprem.yaml      # set storage_root and the rest
sudo ./install.sh --config onprem.yaml --wheelhouse ./wheels --systemd
sudo systemctl enable --now openadapt-flow-runner.path
```

To run a job, drop a descriptor in the inbox. It names the bundle and its
inputs and holds no patient data:

```bash
cat > /srv/openadapt/jobs/inbox/triage-0001.job <<'EOF'
bundle=/srv/openadapt/bundles/vitals-triage
params=patient_ref=PT-INTERNAL-42;note=Reviewed
EOF
```

The runner runs it, adds a record to `audit/audit.log`, and files the job
under `jobs/done` or `jobs/failed`. To check that nothing can leave:

```bash
OPENADAPT_FLOW_SCRUB=on ./bin/verify-airgap.sh --config onprem.yaml --probe --audit
```

`verify-airgap.sh` scans the configuration for any address outside your
network or any cloud key. With `--probe` it checks that a public address
can't be reached, and with `--audit` it checks the audit log's hash chain.
The firewall is the real control; this script checks the software side.
`install.sh --update` and `install.sh --rollback` replace a release
atomically. Put `storage_root` on an encrypted disk; OpenAdapt doesn't manage
the disk key.

A Docker Compose file is included as an alternative to systemd. It puts the
runner on a network with no route to the internet.

## Add a model server on your network

A single GPU server can serve several runners that have no GPU. It answers
three questions: whether two crops show the same record (it can only say no,
never yes), where a described target is, and whether an expected state holds.
Its answer about a target is only a proposal: the deterministic right-record
check still decides before any click. If the server is down, the run stops.

The server is the `openadapt-flow-vlm-service` command, installed with the
`service` extra of `openadapt-flow`. On each runner, set
`OPENADAPT_FLOW_VLM_URL` to the server's address and turn on model grounding
in the deployment file. Details are in
[On-prem VLM inference service](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/deployment/ON_PREM_VLM.md).

## OpenAdapt Cloud

OpenAdapt Cloud at `app.openadapt.ai` is an optional workspace for teams. It
runs browser workflows on a managed runner. Desktop, RDP, and Citrix
workflows still run on your own computers; Cloud delivers tasks to them and
collects their reports. Each Cloud action belongs to exactly one active
**organization**, and so does every token and workflow. Sign-in and
two-factor settings are in [Account security](../security/account-security.md).

Connect a computer with a five-minute, one-use pairing code from Cloud
settings:

```bash
openadapt connect --pairing <code>
```

The credential is saved in the operating system keychain. The command can't
run terminal commands or give the browser access to the shell.

To send a recording or bundle to Cloud, sanitize it first. Sanitizing writes
a redacted copy and never changes the original. A person reviews the copy
locally and approves it, and `push` sends exactly the approved bytes:

```bash
openadapt flow sanitize rec --kind recording --out rec.sanitized
openadapt flow review-sanitized rec.sanitized --original rec
openadapt flow approve-sanitized rec.sanitized --original rec --reviewer you@example.com
openadapt flow push rec.sanitized --kind recording
```

A bundle also needs `validate-hosted`, which binds the exact recording,
bundle, policy, run report, and target to a one-time Cloud challenge before
`push --kind bundle` accepts it. A run reports to Cloud only with `--report`,
and that report has no screens, text, or field values.

Stop alerts, the online Seal check, repair review, and the hosted run queue
are described in [OpenAdapt Cloud](../cloud/index.md). For prices, see
[openadapt.ai/pricing](https://openadapt.ai/pricing).
