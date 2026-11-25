---
description: >-
  What a receipt is, who can sign one, how to check, view, publish, and claim
  it, and how to timestamp, countersign, and disclose its fields.
---

# Receipts

A receipt is a signed, itemized record of one run: what it changed, how each
change was checked, and who signed it. It doesn't grade the run.

Every run gets one, including a run that stopped or couldn't tell whether a
save landed. The receipt copies the run's outcome and never upgrades it. A
`STOPPED` run with a valid signature is still a stopped run.

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 245" role="img" aria-labelledby="oa-rcpt-title oa-rcpt-desc">
  <title id="oa-rcpt-title">Ed25519 receipt signing and trust boundary</title>
  <desc id="oa-rcpt-desc">Inside the customer boundary, the runner writes salted commitments and signs receipt.json with the local computer key and optional organization key while keeping receipt.private.json local (mode 0600). Across the boundary, only digests and public fields flow to OpenAdapt Cloud for optional countersignature, Sigstore Rekor transparency logging, and online verification at app.openadapt.ai/r/id.</desc>
  <defs>
    <marker id="rcpt-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="rcpt-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
  </defs>

  <!-- Customer Boundary -->
  <rect x="14" y="14" width="540" height="216" rx="12" class="oa-svg-panel-verified"/>
  <text x="30" y="34" font-size="9.5" class="oa-svg-verified-txt">CUSTOMER BOUNDARY · RAW VALUES &amp; SALTS STAY LOCAL</text>

  <g class="oa-svg-node">
    <rect x="30" y="48" width="226" height="72" rx="8" class="oa-svg-panel"/>
    <text x="44" y="69" font-size="12.5" class="oa-svg-title">Run &amp; record check</text>
    <text x="44" y="86" font-size="10" class="oa-svg-muted">Outcome, agent_used, verifier</text>
    <text x="44" y="102" font-size="9.5" class="oa-svg-mono">SHA-256 digests only</text>
  </g>
  <path d="M256,84 L302,84" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#rcpt-arr)"/>

  <g class="oa-svg-node">
    <rect x="308" y="48" width="230" height="72" rx="8" class="oa-svg-panel"/>
    <circle cx="522" cy="62" r="3.5" class="oa-svg-gate-dot oa-svg-dot-verified"/>
    <text x="322" y="69" font-size="12.5" class="oa-svg-title">Ed25519 signing</text>
    <text x="322" y="86" font-size="10" class="oa-svg-muted">Computer key + optional org key</text>
    <text x="322" y="102" font-size="9.5" class="oa-svg-mono">receipt.json · receipt.card.json</text>
  </g>

  <g class="oa-svg-node">
    <rect x="30" y="138" width="508" height="76" rx="8" class="oa-svg-panel-warn"/>
    <text x="44" y="159" font-size="10" class="oa-svg-warn-txt">NEVER UPLOADED (MODE 0600)</text>
    <text x="44" y="178" font-size="12.5" class="oa-svg-title">receipt.private.json</text>
    <text x="44" y="196" font-size="10.5" class="oa-svg-muted">Salts and clear field values for selective disclosure; screenshots stay in the local run folder.</text>
  </g>

  <!-- Boundary crossing arrow -->
  <path d="M554,84 L622,84" class="oa-svg-line-verified oa-svg-flow" marker-end="url(#rcpt-arr-v)"/>
  <text x="588" y="74" text-anchor="middle" font-size="9" class="oa-svg-verified-txt">digests</text>

  <!-- External Verification & Countersigning -->
  <rect x="628" y="14" width="338" height="216" rx="12" class="oa-svg-panel-link"/>
  <text x="644" y="34" font-size="9.5" class="oa-svg-accent">OPTIONAL COUNTERSIGNING &amp; VERIFICATION</text>

  <g class="oa-svg-node">
    <rect x="644" y="48" width="306" height="50" rx="8" class="oa-svg-panel"/>
    <text x="658" y="69" font-size="12" class="oa-svg-title">OpenAdapt Cloud countersignature</text>
    <text x="658" y="85" font-size="10" class="oa-svg-muted">Checks runner signature &amp; system-of-record read</text>
  </g>

  <g class="oa-svg-node">
    <rect x="644" y="108" width="306" height="50" rx="8" class="oa-svg-panel"/>
    <text x="658" y="129" font-size="12" class="oa-svg-title">Sigstore Rekor &amp; RFC 3161 TSA</text>
    <text x="658" y="145" font-size="10" class="oa-svg-muted">Public transparency log over 32-byte digest</text>
  </g>

  <g class="oa-svg-node">
    <rect x="644" y="168" width="306" height="46" rx="8" class="oa-svg-panel-verified"/>
    <text x="658" y="188" font-size="12" class="oa-svg-title">Offline CLI or app.openadapt.ai/r/&lt;id&gt;</text>
    <text x="658" y="204" font-size="10" class="oa-svg-mono">openadapt verify · pinned key registry</text>
  </g>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Cryptographic proof without data leakage:</strong> Receipts carry SHA-256 commitments, never screenshots or clear values.</span>
  <span><a href="../../cloud/verify-a-receipt/">Verify a receipt online &rarr;</a></span>
</figcaption>
</figure>

## Who signed it

A receipt can carry several signatures over the same record. Each signature
names a key, and the pinned key registry maps that key to a role. The role
comes only from the registry, never from the receipt. The verifier prints one
line per role, in this order:

| Line | What it means |
|---|---|
| Signed by this computer | The computer that ran the program signed its own account of the run. |
| Signed by `<org>`'s key | Your organization's own key signed it, from a file, the keychain, or a PKCS#11 token. |
| Countersigned by OpenAdapt Cloud | Cloud checked the runner's signed result and its own read-back of the record, then added its signature. |
| Logged publicly | The receipt's digest is in a public transparency log (Sigstore Rekor), so it existed at that time and hasn't changed since. |
| Demo key: checks only in this demo | An example signed with a demo key. It is never evidence. |

**An unknown signer stops and refuses.** A signature from a key that isn't in the
registry makes the result "Not verified: unknown signer", even when the other
signatures are genuine. The verifier doesn't skip that signature and report
the rest. The other refusals work the same way:

- A demo key beside any other signer: "Not verified: a demo key signed
  alongside a real one".
- A registry that names a role the verifier doesn't know: the whole registry
  is refused.
- A schema the verifier doesn't know, a changed receipt, a bad or revoked
  signature, or no signature: "Not verified".

## What a receipt holds

A run folder holds three receipt files:

| File | What it is |
|---|---|
| `receipt.json` | The signed receipt |
| `receipt.private.json` | The salts and values behind its commitments. Mode 0600, never uploaded. |
| `receipt.card.json` | The public receipt: the same signed record, with only the fields on the public list revealed |

The receipt holds:

- The program and the digest of the exact version that ran.
- Provenance metadata identifying `agent_used` (the calling agent or replay runtime) and `verifier_adapter` (which verifier checked the write).
- The hour the run started.
- The outcome and a reason code.
- One line per write: what kind of record it targeted, the operation, the
  result of the record check, how strong that check was, and what it didn't
  check.
- Check counts, and digests of the run report and the evidence bundle.
- A shareable verification link (`https://app.openadapt.ai/r/<id>`) when published to OpenAdapt Cloud.

A receipt never holds screenshots, typed values, URLs, or page text. Evidence
files appear only as SHA-256 digests, and a receipt that embeds an image, a
link, or long text is refused. Record values never appear in clear. Each one is a salted commitment, and the
salts stay in a private file beside the receipt, so you can reveal one field
later and keep the others hidden. How strong a check is, from a screen read
to a read of the system of record, is in
[How a save is checked](../explanation/verification.md#how-strong-a-read-back-is).

A public receipt is the same record with every field that isn't on the public
list replaced by its commitment. The public list is the program name, the
Flow version, and the GitHub login. The same signatures verify the public
receipt, and nothing re-signs it, so it can't say anything the full one
doesn't.

## Check a receipt

```bash
openadapt verify runs/<run>
```

`openadapt verify` takes a receipt file, a run folder (or a folder of them,
such as the quickstart's), or a receipt link. It prints the outcome, each
line, and the signer lines, and exits 0 only when every signature checks and
every signer is known. `openadapt receipt verify` is the same command.

It never fetches keys while it checks a file or folder. To trust OpenAdapt
Cloud's countersignature, pin Cloud's public keys once and compare the
printed fingerprint with the one OpenAdapt publishes:

```bash
openadapt receipt keys pin
```

The keys come from
[app.openadapt.ai/api/public/seal-keys](https://app.openadapt.ai/api/public/seal-keys)
and are written to `~/.openadapt/seal-keys.json`. To check a receipt in a
browser instead, see [Check a receipt online](../cloud/verify-a-receipt.md).

## View, publish, and claim a receipt

| Command | What it does |
|---|---|
| `openadapt receipt view RUN_DIR` | Writes the run's receipt as one offline page in the run folder and opens it. The page checks the signatures in the browser and makes no network requests. |
| `openadapt receipt publish [RUN_DIR]` | Uploads the public receipt (counts, outcomes, and digests only) after you confirm, and prints its link. |
| `openadapt receipt unpublish RUN_DIR` | Takes a published receipt down. |
| `openadapt receipt claim [RUN_DIR...]` | Adds the receipts you published from this computer to your OpenAdapt Cloud workspace. `openadapt login` does this for you after you sign in. |

The `openadapt seal` commands still work and do the same thing:
`openadapt seal verify`, `view`, `publish`, `unpublish`, `claim`, and
`keys pin`.

## Older files

Older Seal files still verify. `openadapt verify` reads every earlier format
and labels the result "older format":

| File | Schema |
|---|---|
| `seal.json` | `local-seal/v1` |
| `public-seal.json` | `public-seal/v1` |
| `receipt.json` from an older release, now written as `run-summary.json` | `openadapt.run-receipt/v2` |
| Cloud's signature in `report.json` (`execute_receipt`) | `seal-signature/v1` and `openadapt.execute-evidence-receipt/v1` |
| Write and transaction receipts | `write-receipt/v1`, `tx-receipt/v1` to `v3` |

Links to published Seals keep working and lead to the same receipt.

<span id="the-seal"></span>

## Cloud's countersignature

OpenAdapt Cloud countersigns the receipt of a run that Cloud Execute tracked.
A run gets Cloud's countersignature when it ends `VERIFIED` with a record
check that read the system of record, and it was started with
`--cloud-execution-id` and `OPENADAPT_EXECUTE_API_KEY` set:

```bash
export OPENADAPT_EXECUTE_API_KEY=...
openadapt flow run bundle --config deploy.yaml --cloud-execution-id EXECUTION_ID
```

`openadapt flow attach-seal RUN_DIR --execution-id ID` adds Cloud's
countersignature to a run that has already finished.

| Check level | Source | Can Cloud countersign? |
|---|---|---|
| 0 | The screen or OCR | No |
| 1 | A second session's view of the application | No |
| 2 | The system of record, such as its API or database | Yes |
| 3 | A counterparty artifact, such as a payer status or a legal export | Yes |

## Check a write that something else made

`verify-run` reads the system of record and decides whether a write that an
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

`verify-run`'s effect receipt is a local check summary rather than a signed
`record/run/v1` receipt. To check a signed receipt against keys you pinned:

```bash
openadapt flow verify-run --check signed.json --keys seal-keys.json
```

It exits 0 only for a genuine signature on a `verified` outcome.
`--accept-outcome OUTCOME` accepts another outcome.

## Timestamps and countersigning

`countersign` adds three things to a signed receipt, beside it in the same
document:

- **Trusted timestamps** (RFC 3161) over the receipt's hash.
- **Salted field commitments**, so you can later reveal chosen fields, such
  as one patient's record number, and keep the others hidden.
- **A countersignature** by a second issuer. A local key countersigns, for
  tests and self-hosted trials.

None of these is a notarial act, a government certification, or an eIDAS
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
outcome, and the result of each check: Cloud's signature, the evidence
manifest, each timestamp with the service's name and time, the
countersignature, the field commitments, and each disclosure. `--json` prints
the same report as data.

It exits 0 only for a genuine Cloud signature on a `verified` or
`rolled_back_verified` outcome, with every part present checked and passed.
It exits 1 for a signature on a `REFUTED` or `INDETERMINATE` outcome, for any
failed check, for a timestamp with no pinned certificate, and for an effect
receipt from anything but a Flow replay unless you pass `--accept-non-flow`.
It warns, without changing the exit code, when the timestamp's time and the
receipt's issue time are more than 300 seconds apart.

Cloud's keys come from `--keys`, `OPENADAPT_SEAL_KEYS_PATH`,
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

`countersign add --keys FILE` queues an exception for each receipt that Cloud
signed on a `REFUTED` or `INDETERMINATE` outcome. An entry starts `open` and
ends one of two ways:

- **Resolved by a later receipt.** `countersign resolve ENTRY --with fix.json`
  takes a later receipt that Cloud signed on a verified outcome, that links to
  the failed run, and that has the same workflow, contract, and committed
  inputs.
- **Closed by attestation.** `countersign close` takes a signed disposition
  from a person: a closed `--code` and `--method`, a role, and a ticket id
  kept only as a keyed digest. The key that signed the failed run's receipt,
  or that run's executor, can't close it.

No flag marks an entry resolved or closed on someone's word. Closed entries
are kept for 6 years (`--retention-days` or
`OPENADAPT_EXCEPTION_RETENTION_DAYS`, at least 183 days).
`countersign purge --export FILE` writes expired entries to `FILE` before
deleting them; open entries are never purged. `countersign exceptions` lists
entries.

### The dossier

`countersign dossier` writes one HTML page, or with `--format zip` the page
plus the raw token files. When opened, the page checks the receipt hash,
Cloud's signature, the evidence digest, and each disclosed field in the
browser. Timestamps need `openadapt flow countersign verify dossier.html` or
`openssl ts -verify`. The dossier lists every exception in the vault and how
each ended.

It holds no patient data unless you pass a disclosure, and then only that
field. `--screenshot` adds screenshots after automatic redaction, which can
miss text, so review a dossier before you send it.

### What a timestamp proves

A verified token shows that the timestamp service signed this exact hash at
its stated time. If the service's key and clock were sound, the receipt, its
evidence digest, and its commitments existed by then and haven't changed.

It doesn't prove that the write happened (the record check and Cloud's
countersignature carry that), when the write happened, that the baseline came
before the executor, or who asked for the timestamp. Revocation isn't checked
offline.

## Encrypting a bundle is a different command

`openadapt flow encrypt bundle -o bundle-encrypted` writes an encrypted copy
of a bundle with `OPENADAPT_BUNDLE_KEY`. It doesn't sign anything or write a
receipt. `openadapt flow seal` is the older name for the same command and
still works.
