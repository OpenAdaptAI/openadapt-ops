---
description: >-
  Choose where workflows run: on a computer you control, fully offline, with
  an optional on-site model server, or connected to OpenAdapt Cloud.
---

# Deploy

OpenAdapt runs as one Verified Execution Plane across three execution modes.
The engine runs where the application is, and every mode enforces the same
commit-boundary checks and signed Ed25519 receipts.

| Execution mode | Where the runner lives | Use it when |
|---|---|---|
| **Local + 4B sidecar** | Your laptop, workstation, or offline VPC (`openadapt wrap` + optional [`Veto-4B-r6`](https://huggingface.co/OpenAdapt/openadapt-veto-4b-r6) ~3.15 GB VRAM sidecar) | Building workflows, local agent wrapping, or regulated / air-gapped data |
| **OpenAdapt Hosted & BYOC Connector** | Self-serve cloud web runner (`$0.05/verified run` PAYG, `$79/mo` Builder, `$499/mo` self-managed dedicated runner, no PHI) or `openadapt connect` / `openadapt-flow connector` on your own machine | Shared workspaces, fleet receipts, phone approvals, and non-regulated web runs |
| **Bring Your Own Sandbox** | Browserbase, E2B, Daytona, or Browser Use connected via `--cdp-url` + `OPENADAPT_CLOUD_KEY` | You already run cloud browser sandboxes and want commit-boundary verification + receipts |

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

Stop alerts, the online receipt check, repair review, and the hosted run queue
are described in [OpenAdapt Cloud](../cloud/index.md). Open Source local runs
are `$0` under MIT. Cloud Self-Serve starts at `$0.05/verified run` PAYG
(first 100/mo free), `$79/mo` Builder, and `$499/mo` for a self-managed
dedicated runner (non-regulated web workflows only, no PHI). Managed
Production starts at `$2,000/mo` (beginning with a `$5,000` 30-day pilot
credited to Year 1) for zero-egress local or VPC software, a 48-hr UI-drift
SLA, and a BAA. See [openadapt.ai/pricing](https://openadapt.ai/pricing).

## Bring your own sandbox

If your agents already run inside **Browserbase**, **E2B**, **Daytona**, or
**Browser Use**, you don't need to migrate infrastructure. Attach OpenAdapt's
verification layer over Chrome DevTools Protocol (`--cdp-url`) and set
`OPENADAPT_CLOUD_KEY` so every run streams signed Ed25519 receipts and human
approval gates to `app.openadapt.ai`:

```bash
export OPENADAPT_CLOUD_KEY="oa_live_..."
openadapt wrap --cdp-url "wss://connect.browserbase.com?apiKey=..." -- <your-agent-command>
```

- **Zero agent rewrite:** Your agent keeps driving its existing Browserbase,
  E2B, Daytona, or Browser Use session.
- **Same commit boundary:** Before a state-changing click or submit, OpenAdapt
  checks target identity, enforces approval gates, and signs the resulting
  receipt (`agent_used`, `verifier_adapter`, SHA-256 digests).
- **Shareable verification:** Each completed run publishes its public receipt
  link to `https://app.openadapt.ai/r/<id>` without uploading screenshots or
  clear field values. For provider-specific examples, see
  [Verify agents in cloud sandboxes and private VPCs](verify-cloud-sandboxes.md).
