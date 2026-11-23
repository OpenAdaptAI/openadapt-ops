---
description: >-
  The receipt a verified run writes, the Seal OpenAdapt Cloud signs, the
  effect receipt for a write another executor made, and how to timestamp,
  countersign, and disclose them.
---

# Receipts, Seals, and countersigning

A run that ends `VERIFIED` writes a **signed execution receipt** (or **receipt**):
a portable summary of what was checked, with no screenshots, typed values, or
free text, safe to share with auditors, counterparties, or downstream systems.
OpenAdapt Cloud can add an Ed25519 countersignature (also called a **Seal**) to
that receipt. `verify-run` writes an **effect receipt** for a write that an
agent, a script, or a person made. `countersign` adds trusted timestamps, field
commitments you can reveal one at a time, and a dossier a third party can check
offline.

## Trust and receipt signing architecture

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 260" role="img" aria-labelledby="oa-trust-title oa-trust-desc">
  <title id="oa-trust-title">Trust boundary and Ed25519 receipt signing architecture</title>
  <desc id="oa-trust-desc">Inside the customer boundary sit the local runner (screenshots, inputs, credentials, system-of-record read-back) and local signing keys (local computer key and organization key). Only metadata with no screenshots, typed values, or free text crosses the dashed boundary to optional external services (OpenAdapt Cloud countersignature and public timestamp log), and any auditor can verify receipts offline using pinned public keys.</desc>
  <defs>
    <marker id="tr-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="tr-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
  </defs>

  <!-- Customer Boundary (encloses runner + local/org keys) -->
  <rect x="14" y="16" width="522" height="228" rx="12" class="oa-svg-panel-link"/>
  <text x="30" y="40" font-size="10" class="oa-svg-accent">INSIDE YOUR BOUNDARY · LOCAL / VPC</text>

  <!-- Runner column -->
  <rect x="30" y="54" width="234" height="174" rx="10" class="oa-svg-panel"/>
  <text x="44" y="77" font-size="13.5" class="oa-svg-title">Local runner</text>
  <text x="44" y="99" font-size="11.5" class="oa-svg-muted">• Screenshots and inputs</text>
  <text x="44" y="119" font-size="11.5" class="oa-svg-muted">• Optional AES-256-GCM</text>
  <text x="44" y="139" font-size="11.5" class="oa-svg-muted">• System-of-record read-back</text>
  <text x="44" y="169" font-size="10.5" class="oa-svg-mono">report.json · receipt.json</text>
  <text x="44" y="189" font-size="10.5" class="oa-svg-muted">Private openings stay local</text>

  <path d="M264,141 L292,141" class="oa-svg-line-accent" marker-end="url(#tr-arr)"/>

  <!-- Local & Org signers (inside boundary) -->
  <rect x="298" y="54" width="222" height="174" rx="10" class="oa-svg-panel"/>
  <text x="312" y="77" font-size="13.5" class="oa-svg-title">Customer signers</text>
  <text x="312" y="100" font-size="11.5" class="oa-svg-muted">• Local computer key</text>
  <text x="312" y="120" font-size="11.5" class="oa-svg-muted">• Organization key</text>
  <text x="312" y="148" font-size="10.5" class="oa-svg-muted">PEM file, OS keychain,</text>
  <text x="312" y="164" font-size="10.5" class="oa-svg-muted">or PKCS#11 HSM</text>
  <text x="312" y="196" font-size="10.5" class="oa-svg-mono">openadapt flow local-seal</text>

  <!-- Boundary divider -->
  <line x1="564" y1="16" x2="564" y2="244" class="oa-svg-line" stroke-dasharray="6 4"/>
  <path d="M536,141 L612,141" class="oa-svg-line-verified" marker-end="url(#tr-arr-v)"/>
  <text x="542" y="129" font-size="10" class="oa-svg-muted">digests only</text>

  <!-- External optional services & verification -->
  <rect x="618" y="20" width="348" height="106" rx="12" class="oa-svg-panel"/>
  <text x="634" y="44" font-size="10" class="oa-svg-accent">OUTSIDE YOUR BOUNDARY (OPTIONAL)</text>
  <text x="634" y="65" font-size="13.5" class="oa-svg-title">External countersigners</text>
  <text x="634" y="86" font-size="11.5" class="oa-svg-muted">• OpenAdapt Cloud countersignature (Seal)</text>
  <text x="634" y="105" font-size="11.5" class="oa-svg-muted">• Public log / RFC 3161 timestamp (Sigstore)</text>

  <rect x="618" y="140" width="348" height="102" rx="12" class="oa-svg-panel-verified"/>
  <text x="634" y="164" font-size="10" class="oa-svg-verified-txt">OFFLINE VERIFICATION</text>
  <text x="634" y="185" font-size="13.5" class="oa-svg-title">Auditor or counterparty</text>
  <text x="634" y="206" font-size="11.5" class="oa-svg-muted">Pin public keys once; verify offline</text>
  <text x="634" y="225" font-size="10.5" class="oa-svg-mono">openadapt seal verify report.json</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>What crosses the boundary:</strong> Recordings, inputs, and local keys stay inside your boundary; receipts hold counts, digests, and check tiers with no screenshots, typed values, or free text.</span>
  <span><a href="../../security/data-handling/">Data handling &rarr;</a></span>
</figcaption>
</figure>

### Signer roles

Every signed receipt identifies who signed it using an explicit signer role. An
unknown signer role or tampered payload is refused:

| Signer role | What it attests | Where the key lives |
|---|---|---|
| Local computer key | Signed on this machine (`openadapt flow local-seal`) | Local runner |
| Organization key | Signed by your organization's key | PEM file, OS keychain, or PKCS#11 HSM |
| OpenAdapt Cloud countersignature | Countersigned by OpenAdapt Cloud Execute (Seal) after an independent read | OpenAdapt Cloud (`app.openadapt.ai/api/public/seal-keys`) |
| Public log / timestamp | Anchored to a timestamp authority (`openadapt flow countersign`) | Sigstore or configured TSA |
| Demo key | Synthetic tutorial or demo check only; never valid for production | Bundled demo fixture |

## The run receipt

A `VERIFIED` run writes `receipt.json` (schema `openadapt.run-receipt/v2`)
and an image of it, `receipt.png`. From the quickstart:

```json
{
  "outcome": "VERIFIED",
  "transaction_outcome": "VERIFIED",
  "profile": "standard",
  "substrate": "web",
  "steps_ok": 6, "steps_total": 6,
  "identity_confirmed": 5, "identity_required": 5,
  "effects_confirmed": 2, "effects_required": 2,
  "effect_tier_reached": "independent_system",
  "model_calls": 0,
  "external_network_calls": "none",
  "bundle_digest": "d9b3102c…",
  "provenance": "synthetic-tutorial"
}
```

It holds counts, digests, closed values, and versions; no record values.
`effect_tier_reached` is the weakest read-back among the run's saves:
`independent_system`, `independent_session`, or
`persisted_state_reacquisition`. `effect_assurance` gives its grade,
`independent_readback` or `screen_readback`.
[How a save is checked](../explanation/verification.md#how-strong-a-read-back-is)
maps the two. A stopped run gets no receipt, only its local report.

## The Seal

A Seal is OpenAdapt Cloud's Ed25519 signature on the receipt of a run that
Cloud Execute tracked. A run gets one when it ends `VERIFIED` with a record
check that read the system of record, and it was started with
`--cloud-execution-id` and `OPENADAPT_EXECUTE_API_KEY` set:

```bash
export OPENADAPT_EXECUTE_API_KEY=...
openadapt flow run bundle --config deploy.yaml --cloud-execution-id EXECUTION_ID
```

Flow then fetches the signed receipt into `report.json` as
`execute_receipt`. `openadapt flow attach-seal RUN_DIR --execution-id ID`
does the same for a finished run.

The Seal names the execution, the exact workflow version and digest, the
qualification, the environment and runner, the outcome, the check level that
confirmed the save, whether delivery was uncertain, and a digest of the
evidence.

| Check level | Source | Can back a Seal? |
|---|---|---|
| 0 | The screen or OCR | No |
| 1 | A second session's view of the application | No |
| 2 | The system of record, such as its API or database | Yes |
| 3 | A counterparty artifact, such as a payer status or a legal export | Yes |

### Check a Seal offline

Pin Cloud's public keys once, comparing the printed fingerprint with the one
OpenAdapt publishes, then check:

```bash
openadapt seal keys pin
openadapt seal verify runs/<run>/report.json
```

`keys pin` downloads the keys from
`https://app.openadapt.ai/api/public/seal-keys` (or `--url`) and writes
`~/.openadapt/seal-keys.json` (or `--path`). `seal verify` also accepts a
receipt file or a webhook body, and `--json` prints the result as JSON. It
never fetches keys while it checks. To check one in a browser instead, see
[Check a Seal online](../cloud/verify-a-seal.md).

`openadapt flow seal` is a different command: it encrypts a bundle for
deployment and doesn't issue a Seal.

## Check a write that something else made

`verify-run` reads the system of record and decides whether a write an
agent, a script, or a person reported actually landed. It uses the same
record checks as `run` and makes no model calls. It's a preview: the effect
receipt format follows a draft specification and may change.

```bash
# Before the agent starts: read the store, so new rows can be told from old ones.
openadapt flow verify-run --verify verify.yaml --params task.json \
  --capture-baseline before.json

# After it finishes:
openadapt flow verify-run --verify verify.yaml --params task.json \
  --run-record agent-run.json --authorization-ref TICKET-1234 \
  --baseline before.json --out share/
```

`verify.yaml` is the file `qualify` reads; `verify-run` uses its `verifier`
and `effects` (or `record`) and ignores the rest. See the
[`verify.yaml` reference](../how-to/certify-and-qualify.md#verifyyaml-reference).
`max_execution_window_s` (default 3600) is read only by `verify-run`.

The inputs come from different people on purpose:

- `--params` holds the values the task named, such as which patient, from
  whoever assigned the task. The executor can't choose what it's checked
  against.
- `--run-record` is what the executor reports. It must name `executor_kind`:
  `agent`, `script`, `human`, `flow_replay`, or `unknown`.
- `--baseline` is the read taken before the executor started. Without it, a
  check that counts new records is `INDETERMINATE`. A baseline works once,
  and one older than `max_execution_window_s` counts as none.

`--approver FILE` names who approved the write; an executor that approved its
own write gets `rejected_policy`. `--remediates RECEIPT_ID` links a receipt
to an earlier one it fixes, and `--correlation-id ID` carries your own ticket
or trace id.

| What the store shows | `effect_verdict` | `outcome` |
|---|---|---|
| The declared record, exactly once, through a system-of-record read | `CONFIRMED` | `verified` |
| The same, but the executor approved its own write | `CONFIRMED` | `rejected_policy` |
| Nothing that matches | `REFUTED` | `halted_before_effect` |
| A duplicate, a wrong value, or only some of the effects | `REFUTED` | `reconciliation_required` |
| The store couldn't be read, no baseline, or a separate-session read | `INDETERMINATE` or `CONFIRMED` | `reconciliation_required` |

Only a system-of-record read produces `verified`; `onscreen` is refused
before anything runs. `share/effect-receipt.json` (schema
`openadapt.effect-receipt/v1`) holds no record values, URLs, or the
executor's text. Every digest whose input could hold customer data is keyed
with a salt drawn for the run, which stays in the baseline file or
`share/effect-run.private.json`. Those files are written with mode 0600;
delete them when you no longer need them.

The effect receipt is unsigned. To check a signed one against keys you
pinned:

```bash
openadapt flow verify-run --check signed.json --keys seal-keys.json
```

It exits 0 only for a genuine signature on a `verified` outcome.
`--accept-outcome OUTCOME` accepts another outcome.

## Timestamps and countersigning

`countersign` adds three things to a sealed receipt, beside it in the same
document:

- **Trusted timestamps** (RFC 3161) over the receipt's hash. A Seal with one
  is a Timestamped Seal.
- **Salted field commitments**, so you can later reveal chosen fields, such
  as one patient's record number, and keep the others hidden.
- **A countersignature** by a second issuer. A Seal with one is a
  Countersigned Seal. A local key countersigns, for tests and self-hosted
  trials.

Neither is a notarial act, a government certification, or an eIDAS
qualified seal or time stamp.

Install the extra first:

```bash
pip install 'openadapt-flow[countersign]'
```

```bash
# 1. Before the executor runs: timestamp the baseline read for this run.
openadapt flow countersign timestamp-baseline --baseline baseline.json \
  --read-at 2026-10-17T04:58:00Z --nonce "$RUN_NONCE" --out baseline-ts.json

# 2. After the receipt exists: commit fields, timestamp, and countersign.
openadapt flow countersign add receipt.json --out countersigned.json \
  --fields-file fields.json --baseline-timestamp baseline-ts.json

# 3. Check it.
openadapt flow countersign verify countersigned.json

# 4. In a dispute: reveal one field, then export a dossier.
openadapt flow countersign disclose countersigned.json --field f-1a2b3c4d --out mrn.disclosure.json
openadapt flow countersign dossier countersigned.json --disclosure mrn.disclosure.json \
  --out dossier.html
```

`fields.json` maps field names to values, such as `{"mrn": "004217"}`.
Values never go on the command line, where shell history would keep them.
Delete the file once the vault has its copy.

### The timestamp service

`countersign add` and `timestamp-baseline` are the only `countersign`
commands that connect to the network. By default they use Sigstore's public
timestamp service, `https://timestamp.sigstore.dev/api/v1/timestamp`, which
receives only a 32-byte digest and a nonce. It's free and has no service
level agreement, so for high volume use your own RFC 3161 service:

| Flag | Effect |
|---|---|
| `--tsa-url URL` | Use another RFC 3161 timestamp service |
| `--tsa-cert PEM` | Pin that service's certificate or a CA above it. Without it, the bundled Sigstore root is pinned. |
| `--no-timestamp` | Request no timestamp. `timestamp-baseline` refuses it. |
| `--tsa-local DIR` | A test-only timestamp service on this computer. Its time is this computer's clock. |

Each new token is checked against the pinned certificate before anything is
written. A service that can't be reached, refuses, or returns a token that
doesn't verify leaves no output file.

### What `countersign verify` shows

`verify` prints the executor first (a Flow replay, or another executor such
as a computer-use agent), then the verification tier, the effect verdict, the
outcome, and the result of each check: the Seal signature, the evidence
manifest, each timestamp with the service's name and time, the
countersignature, the field commitments, and each disclosure. `--json` prints
the same report as data.

It exits 0 only for a genuine Seal on a `verified` or `rolled_back_verified`
outcome, with every part present checked and passed. It exits 1 for a Seal
on a `REFUTED` or `INDETERMINATE` outcome, for any failed check, for a
timestamp with no pinned certificate, and for an effect receipt from anything
but a Flow replay unless you pass `--accept-non-flow`. It warns, without
changing the exit code, when the timestamp's time and the receipt's issue
time are more than 300 seconds apart.

Seal keys come from `--keys`, `OPENADAPT_SEAL_KEYS_PATH`,
`OPENADAPT_SEAL_KEYS_JSON`, or `~/.openadapt/seal-keys.json`. Nothing is
fetched.

### Field commitments and the vault

Each field gets its own random salt, and its commitment names no field. A
disclosure gives one field's name, value, and salt, and anyone can recompute
the commitment. A disclosure counts only when a verified timestamp or
countersignature binds the commitments.

`countersign add` keeps the salts and values in a vault:
`$OPENADAPT_COUNTERSIGN_VAULT/<receipt_sha256>/` (default
`~/.openadapt/countersign-vault`), mode 0600. The vault holds patient data:
back it up and encrypt it like the system of record. Losing it loses the
ability to disclose; it never weakens the commitments.

### The exception queue

`countersign add --keys FILE` queues an exception for each genuine Seal on a
`REFUTED` or `INDETERMINATE` outcome. An entry starts `open` and ends one of
two ways:

- **Resolved by a Seal.** `countersign resolve ENTRY --with fix.json` takes a
  later receipt with a genuine Seal on a verified outcome that links to the
  failed run and has the same workflow, contract, and committed inputs.
- **Closed by attestation.** `countersign close` takes a signed disposition
  from a person: a closed `--code` and `--method`, a role, and a ticket id
  kept only as a keyed digest. The key that sealed the failed run, or that
  run's executor, can't close it.

No flag marks an entry resolved or closed on someone's word. Closed entries
are kept for 6 years (`--retention-days` or
`OPENADAPT_EXCEPTION_RETENTION_DAYS`, at least 183 days).
`countersign purge --export FILE` writes expired entries to `FILE` before
deleting them; open entries are never purged. `countersign exceptions` lists
entries.

### The dossier

`countersign dossier` writes one HTML page, or with `--format zip` the page
plus the raw token files. When opened, the page checks the receipt hash, the
Seal signature, the evidence digest, and each disclosed field in the browser.
Timestamps need `openadapt flow countersign verify dossier.html` or
`openssl ts -verify`. The dossier lists every exception in the vault and how
each ended.

It holds no patient data unless you pass a disclosure, and then only that
field. `--screenshot` adds screenshots after automatic redaction, which can
miss text, so review a dossier before you send it.

### What a timestamp proves

A verified token shows that the timestamp service signed this exact hash at
its stated time. If the service's key and clock were sound, the receipt, its
evidence digest, and its commitments existed by then and haven't changed.

It doesn't prove that the write happened (the read-back and the Seal carry
that), when the write happened, that the baseline came before the executor,
or who asked for the timestamp. Revocation isn't checked offline.
