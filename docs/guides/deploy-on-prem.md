# Deploy on-prem

OpenAdapt runs where the data lives. The deterministic replay path calls no
OpenAdapt-hosted model or control plane; it uses only the target application and
any configured system-of-record verifier. Optional model tiers run on your own
infrastructure. This guide covers the data-handling controls for a regulated
on-prem deployment and the pilot install runbook.

!!! note "This is the opposite lane from the hosted option"
    An on-prem deployment uses no OpenAdapt cloud account, telemetry, cloud model,
    or auto-update. Traffic to the target application and any configured
    system-of-record verifier still follows your deployment config. For the
    managed, non-regulated lane, see [the hosted option](hosted.md).

## The default is already local

A compiled bundle replays deterministically with no model calls and no OpenAdapt
cloud dependency. The default backend is a local headless browser. Application and
verifier traffic follows the endpoints in the deployment config; enforce its
boundary at the host and network layers.

## What runs on the clinic machine

One host (a server, or a workstation next to the Citrix client) runs the whole
stack locally:

- **The engine**: `openadapt flow` (`run` / `replay` / `resume` / `certify` /
  `lint` / `teach`): compile-time bundle → deterministic replay → identity gate →
  effect verification → halt. Deterministic, `$0`, no model calls by default.
- **A local runner / scheduler**: a directory-as-queue wrapper
  (`deploy/on-prem/bin/run-queue.sh` + a systemd `.path` unit). No broker, no
  daemon framework, no network.
- **Deployment wiring**: a single [`deployment.yaml`](../reference/deployment-config.md)
  (backend URL, system-of-record effect verifier, actuation, durable runtime,
  policy). An empty file = fully local, zero egress.
- **PHI scrubbing**: the optional `privacy` extra (Presidio-backed), fail-closed.
- **A local, append-only audit log**: hash-chained, PHI-free.
- **Durable state**: a halted run pauses durably and is resumable locally.
- **(Optional) an on-prem VLM appliance**: a LAN-only GPU box, off by default.

The runnable scaffold ships in the engine repo under
[`deploy/on-prem/`](https://github.com/OpenAdaptAI/openadapt-flow/tree/main/deploy/on-prem);
the compliance posture is in `deploy/on-prem/COMPLIANCE.md`.

## One config drives the deployment

A production run is defined by a single
[`deployment.yaml`](../reference/deployment-config.md) (backend URL, system of
record to verify writes against, optional API actuation tier, durable runtime,
safety policy), read by `certify`, `run`, and `resume`:

```yaml
backend:  { url: https://emr.internal.example.org }
effects:  { kind: fhir, base_url: https://emr.internal.example.org/apis/default/fhir }
runtime:  { durable: true, allow_model_grounding: false }   # zero model-service calls
policy:   { policy: clinical-write }
```

`runtime.allow_model_grounding` defaults to **false**, so the deterministic path
makes no model-service calls unless you opt in and point the runtime at an on-prem
appliance. See [Run a deployment](run-a-deployment.md).

## Install (summary)

```bash
pip install 'openadapt[privacy]'
python -m spacy download en_core_web_sm
export OPENADAPT_FLOW_SCRUB=on          # scrub REPORT.md + logs, fail closed
```

### The on-prem deployment package (systemd or containers)

The engine repo's `deploy/on-prem/` package wires versioned release activation,
the queue runner, air-gap checks, offline signed updates, and rollback. Full-disk
encryption and the offline wheelhouse remain deployment inputs:

```bash
cd deploy/on-prem
cp onprem.example.yaml onprem.yaml                 # edit storage_root, paths

# Build an offline wheelhouse OFF-SITE on a connected host, copy it in on media:
#   pip download 'openadapt-flow[privacy]' -d wheels

sudo ./install.sh --config onprem.yaml --wheelhouse ./wheels --systemd
sudo systemctl enable --now openadapt-flow-runner.path
OPENADAPT_FLOW_SCRUB=on ./bin/verify-airgap.sh --config onprem.yaml --probe
```

Containers instead of systemd: validate with
`docker compose -f docker-compose.yml config`, then `docker compose up -d runner`.

## "Nothing leaves your network": concrete and verifiable

The air-gap is enforced by your firewall; OpenAdapt's job is to (a) need no
OpenAdapt egress and (b) let an operator *prove* the boundary. Four
defence-in-depth layers:

1. **No OpenAdapt egress by default in the software.** With no VLM URL set, the
   deterministic path makes no OpenAdapt-hosted or model-service calls, and there
   is no telemetry, analytics, license check, or update ping in the run path. Keep
   the `deployment.yaml` target and verifier endpoints on the LAN.
2. **Structural egress denial.** The systemd unit sets `IPAddressDeny=any` (the
   kernel drops all IP traffic for the runner unless a LAN CIDR is explicitly
   allow-listed); the Docker Compose alternative puts the runner on an
   `internal: true` network with no gateway to the internet.
3. **Fail-closed PHI handling.** `OPENADAPT_FLOW_SCRUB=on` makes a missing
   scrubbing capability *abort* rather than write plaintext PHI.
4. **Attestation.** `verify-airgap.sh` scans your config and environment for any
   off-LAN URL or cloud key; with `--probe` it actively curls a public canary and
   **asserts the call fails**; with `--audit` it walks the audit-log hash chain.

```bash
OPENADAPT_FLOW_SCRUB=on ./deploy/on-prem/bin/verify-airgap.sh \
    --config onprem.yaml --probe --audit
# AIR-GAP ATTESTATION: PASS (no FAIL checks)
```

The firewall is the real control; the `internal:true` network, `IPAddressDeny=any`,
and `verify-airgap.sh` are defence-in-depth and attestation, not a replacement for
a correct network boundary.

## PHI scrubbing on the persist and log paths

The sanitizer processes `REPORT.md` and console logs. Missing dependencies,
unsupported configuration, and sanitizer errors fail closed, but detector false
negatives remain possible; review output before it crosses a boundary. The
compiled bundle and `report.json` keep literal identifiers on purpose: they are
the identity check and the audit trail, protected by a documented boundary rather
than by redaction. Production images must stage the allowlisted spaCy model
locally, not download one at runtime.

## Encryption at rest: setup and the honest caveat

Everything lives under `storage_root` (default `/srv/openadapt`), which you place
on a **full-disk-encrypted** volume (LUKS / BitLocker / FileVault; OpenAdapt never
holds the disk key). At-rest protection has three layers:

| Layer | Control | Real today? |
|---|---|---|
| The disk holding `storage_root` (bundles, runs, audit, frames) | **Operator full-disk encryption** (LUKS / BitLocker / FileVault) | REAL: the primary PHI-at-rest control. Operator-provisioned |
| The identity band inside `workflow.json` | **Salted-hash `identity_template`** (no plaintext name / DOB / MRN; optional external `OPENADAPT_FLOW_IDENTITY_SALT`) | REAL. A hash of a low-entropy identifier is brute-forceable by a holder of both bundle and salt, so it is **not** a cryptographic seal |
| The bundle `workflow.json` + durable checkpoints | **Opt-in AES-256-GCM sealing** via `OPENADAPT_BUNDLE_KEY` (`Workflow.save(encrypt=True)`; scrypt-derived key) | REAL (opt-in, shipped). A wrong/missing key or tampered ciphertext fails loud and safe |
| `templates/*.png` (recorded screen crops of identifiers) | Full-disk encryption + governance guards (kept out of git); opt-in Presidio image redaction | REAL for FDE + guard, but see the caveat |

Enable the per-bundle seal for cryptographic at-rest protection that does not
depend solely on the volume:

```bash
export OPENADAPT_BUNDLE_KEY=…            # seals workflow.json + checkpoints (AES-256-GCM)
```

!!! danger "Honest at-rest caveat: the identifier crops"
    The identity check needs a **rendered crop of the identifier** (an image of
    the MRN / name as it appeared on screen), stored as `templates/*.png`. These
    crops are **rendered pixels of PHI**, and they are **not yet sealed inside
    the per-bundle encrypted container**; they still rely on **operator full-disk
    encryption**. Enable `OPENADAPT_BUNDLE_KEY` for the JSON and checkpoints, but
    do **not** represent the whole bundle as cryptographically sealed. Full-disk
    encryption remains the baseline control for the template crops. Treat every
    bundle as PHI.

## The local audit log

`audit/audit.log` is a tamper-evident **index** over the runs: newline-delimited
JSON, append-only, **PHI-free by construction**. Each record carries a UTC
timestamp, an event (`queued` / `started` / `verified` / `halted` / `failed` /
`resumed`), an opaque job id, the bundle basename, the run-dir path, the process
exit code, the OS actor, an operator note, and `prev_sha`, a sha256 chain to the
previous line, so any silent edit or deletion breaks every subsequent hash and is
caught by `verify-airgap.sh --audit`. The per-step PHI detail stays beside each
run in `runs/<id>/report.json` under the encrypted volume; the audit log records
*that* a run happened and *how it ended*, never patient data.

Tamper-**evidence**, not tamper-**proof** (a local root can recompute the chain):
for stronger assurance make the file append-only at the OS layer (`chattr +a` on
Linux) or export it to a LAN WORM store.

## Offline updates (operator-pulled, signed, never phoned)

The clinic **never** auto-updates over the internet. Updates are prepared
out-of-band and pulled in by the operator:

1. An engineer builds a signed release on a connected host and produces a
   **detached signature**.
2. The operator copies the archive + signature onto the host on removable media,
   and points `onprem.yaml:updates` at them.
3. `install.sh --update` verifies the signature against the **pinned vendor
   public key** in `keys/`, installs into a fresh blue/green venv, runs the smoke
   test + `verify-airgap.sh`, flips the runner over, and records the applied
   version in the audit log.

The release manager also performs bounded archive extraction and serialized
atomic activation. The hermetic update test exercises success, refusal, migration,
data preservation, rollback/recovery, locking, and audit-chain serialization
without network access.

## Where the automation sits relative to Citrix

Where the EMR is delivered over Citrix, the automation process runs **on the
clinic host inside the clinic network**, reaching the application over the LAN via
the RDP/pixel or Windows backend, the same path a clinician's session uses. The
runner needs LAN reachability to the Citrix/RDP endpoint and to the local EMR's
system-of-record API (for effect verification), and **nothing beyond the LAN**. On
pure-pixel Citrix/RDP the identity ladder falls back from structured a11y/DOM text
to the pixel/OCR tiers; read the wrong-patient guarantees and their availability
cost on that substrate before relying on it.

## The on-prem VLM appliance

If you enable the optional model tiers (grounding, identity veto, state
verification), run them as an [on-prem VLM appliance](../concepts/vlm-appliance.md)
on your own hardware:

```bash
export OPENADAPT_FLOW_VLM_URL='http://your-appliance:8000'
```

The appliance is designed to make no external model calls and not persist
payloads. Enforce those properties with network policy, process configuration, and
retention tests. Identity crops and full frames are deliberately **not** scrubbed
before the appliance sees them, because the identity check needs the literal
identifier; the control there is the trusted local boundary and verified retention
behavior, not redaction. Unset the URL and no model tiers exist (the default
install pulls no model).

## What crosses which boundary

| Artifact | Contains identifiers? | Control |
|---|---|---|
| Compiled bundle (`workflow.json`) | Yes, on purpose | Documented boundary + salted-hash identity band + opt-in AES-256-GCM seal |
| `templates/*.png` (identifier crops) | Yes (rendered pixels) | Full-disk encryption + governance guards (not yet inside the per-bundle seal) |
| `report.json` | Yes, on purpose | Documented boundary; it is the audit trail |
| `REPORT.md`, console logs | Sanitizer applied when `OPENADAPT_FLOW_SCRUB=on` | Processing errors fail closed; review for detector misses before egress |
| `audit/audit.log` | No (PHI-free by construction) | Append-only, hash-chained |
| Identity crops to the appliance | Yes | Trusted local boundary; verify egress and retention controls |
| Deterministic replay path | n/a | No OpenAdapt-hosted dependency; target and verifier traffic remains |

## Compliance posture, stated honestly

**Not legal advice, and not a compliance guarantee.** OpenAdapt provides the
software substrate for running compiled automations on-premise. Whether a given
deployment satisfies PHIPA, PIPEDA, HIPAA, or another regime is a determination
for the deploying organization's privacy officer and counsel. We do **not** sign
a BAA, and no part of the software is a certification. What the software provides
(PHI processed locally, protected at rest by full-disk encryption plus in-bundle
identity hashing plus opt-in AES-256-GCM sealing, and a local append-only audit
trail) is the technical substrate those agreements attest to. The full boundary
list is in the engine repo's `deploy/on-prem/COMPLIANCE.md`.

For the strictest deployments: install with the `privacy` extra, run the
appliance locally (or not at all, keeping the deterministic path only), set
`OPENADAPT_FLOW_SCRUB=on`, keep bundles and reports inside your environment, and
restrict target, verifier, and optional local-model traffic to the destinations
the deployment policy permits.

Full-disk encryption is operator-provisioned and the container topology needs a
prebuilt offline wheelhouse. Each site still tests its own signing authority,
storage, service manager, backup, recovery, and maintenance procedure. See the
[security and deployment review](security-review.md).

Running on-prem does not change the engine's own safety limits: the wrong-patient
identity ladder, the unarmed-step gaps, the transactional-write caveats, and the
OCR ceilings all still apply. On-prem changes *where* the data lives, not *what
the replay can and cannot guarantee*.

For a managed alternative, see [the hosted option](hosted.md).
