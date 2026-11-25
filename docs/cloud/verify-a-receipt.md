---
description: >-
  Check an OpenAdapt receipt on the public verification page or its API, or
  offline with the openadapt command.
---

# Check a receipt online

A receipt is a signed, itemized record of one run: what it changed, how each
change was checked, and who signed it. It doesn't grade the run. Anyone who
holds a receipt can check it: an auditor, a payer, or the system that asked
for the run.

## On the verification page

The page checks OpenAdapt Cloud's countersignature, the "Countersigned by
OpenAdapt Cloud" line. To check every signer on a receipt, use
[`openadapt verify`](#offline).

Open [app.openadapt.ai/seals/verify](https://app.openadapt.ai/seals/verify).
It needs no account. Paste or upload any of these:

- an Execute receipt (`openadapt.execute-evidence-receipt/v1`);
- a run's `report.json`, which holds it as `execute_receipt`;
- an Execute webhook body, which holds it as `receipt`.

The page shows one of these results:

| Result | Meaning |
|---|---|
| Verified | Cloud signed this receipt with a published key, the receipt is unchanged, and it records a verified outcome |
| The signature is genuine, but the outcome it records is not verified | Cloud signed it, and the run ended some other way, for example `halted_before_effect` |
| Not verified | No signature, a changed receipt, an unknown or revoked key, or a signature that doesn't match |

It also shows the execution ID, the outcome, the signing key, and the
receipt's SHA-256.

## Through the API

```bash
curl -s https://app.openadapt.ai/api/public/seals/verify \
  -H 'content-type: application/json' \
  --data @runs/<run>/report.json
```

The request body is at most 16 KB. A checked receipt returns
`{"verified": true, "key_id": ..., "receipt_sha256": ..., "execution_id": ...,
"outcome": ..., "verified_outcome": ...}`. A refusal returns
`{"verified": false, "reason": ...}`, where `reason` is one of `unsigned`,
`malformed`, `receipt_mismatch`, `unknown_key`, `revoked_key`, or
`bad_signature`. Cloud keeps no record of what you send; the result depends
only on the receipt and the published keys.

## Offline

The page and the API ask Cloud. `openadapt verify` checks on your own
computer and verifies every signer on the receipt. It prints one line per
signer and stops with an error on any unknown key; see
[Who signed it](../reference/receipts.md#who-signed-it). To trust Cloud's
countersignature, pin Cloud's public keys once:

```bash
pip install openadapt
openadapt receipt keys pin       # compare the fingerprint before you confirm
openadapt verify runs/<run>
```

The keys are published at
[app.openadapt.ai/api/public/seal-keys](https://app.openadapt.ai/api/public/seal-keys).
`openadapt verify` never fetches keys while it checks a file or folder. See
[Receipts](../reference/receipts.md).
