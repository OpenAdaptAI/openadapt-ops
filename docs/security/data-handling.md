---
description: >-
  Where each kind of data lives, how patient data and other identifiers are
  scrubbed, what a person reviews before anything leaves, and what the
  shareable receipt can hold.
---

# Data handling

OpenAdapt handles screens, typed values, and record identifiers from the
applications it drives. In a healthcare deployment these include protected
health information. This page says where each kind of data lives and what
can leave your network.

## Where each artifact lives

| Artifact | Holds identifiers? | Where it stays |
|---|---|---|
| Recording, bundle, `report.json` | Yes, on purpose: the right-record check and the audit trail need the literal identifiers | Inside your boundary. Encrypt with `OPENADAPT_BUNDLE_KEY` and an encrypted disk. |
| `REPORT.md` | Free text is scrubbed; screenshots are redacted when scrubbing is on | Inside your boundary. Review before sharing. |
| Sanitized copy | Reviewed and approved by a person | May go to OpenAdapt Cloud after approval |
| Receipt | No. Only counts, digests, closed values, and versions | Safe to share |
| Halt report or decision task sent to Cloud | No. Closed values, counts, and digests; no free text or images | OpenAdapt Cloud |

Treat recordings, bundles, and run folders as protected data. Limit who can
read them, and keep them on an encrypted disk.

## Scrubbing

Scrubbing uses the `openadapt-privacy` package,
which finds personal and health data with named-entity recognition, through
one path in the engine:

- `REPORT.md` passes every free-text field through the scrubber.
- Saved step screenshots go through image redaction when scrubbing is on.
- `OPENADAPT_FLOW_SCRUB=on` fails closed: if the scrubber isn't installed,
  the run stops instead of writing plain text. The on-premises queue refuses
  to start without it.
- Without the `privacy` extra, writing text that looks like an identifier
  prints a warning instead of failing silently.

The right-record check's evidence keeps literal identifiers, because
scrubbing them would make the check impossible. That evidence stays inside
your boundary.

## Nothing raw is uploaded

The only way an artifact reaches OpenAdapt Cloud is a sanitized copy that a
person approved:

1. `openadapt flow sanitize` writes a redacted copy and a list of every file
   and change. The original is never modified.
2. `openadapt flow review-sanitized` shows the original and the copy side by
   side in a viewer that listens only on this computer. The reviewer can add
   redactions; any change cancels an earlier approval.
3. `openadapt flow approve-sanitized` freezes the exact reviewed bytes as an
   archive and records who approved it.
4. `openadapt flow push` sends exactly those bytes. Cloud checks the
   manifest, the review state, and the archive's SHA-256 before accepting it.

Files the sanitizer can't handle, such as databases, video, audio, nested
archives, and symlinks, refuse the whole copy instead of passing through.
The sanitizer's success isn't proof of de-identification; the person's review
is the gate.

## What can leave your network

| Traffic | When | What it carries |
|---|---|---|
| None | A local or on-premises run with default settings | |
| Model requests | Only with model grounding turned on | Screenshots. Under patient-data mode, only to hosts on `phi_grounding_allowlist`. |
| A model server on your network | When `OPENADAPT_FLOW_VLM_URL` is set | Crops and screenshots, within your network. Identity crops sent to it aren't scrubbed. |
| Cloud reports | With `--report`, `report-break`, or a Cloud connector | Counts, digests, and closed values. See [Subprocessors](subprocessors.md#what-runs-send-to-openadapt). |
| Cloud uploads | `push` of an approved sanitized copy | The approved bytes only |

## Encryption

- **At rest:** optional AES-256-GCM for the bundle, target crops, and
  checkpoints with `OPENADAPT_BUNDLE_KEY`, on top of your disk encryption.
  Regulated runs refuse an unencrypted bundle. You own key management:
  storage, rotation, and escrow.
- **In transit:** Cloud APIs use HTTPS. Flow refuses plain `http://` to the
  Windows agent server on any host other than `localhost`, because
  screenshots can show patient data.
