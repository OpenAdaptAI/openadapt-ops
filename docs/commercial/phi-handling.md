# PHI handling in one page

How OpenAdapt handles protected health information (PHI) and other regulated
identifiers, end to end: what is scrubbed, what is deliberately retained and
where, what a human reviews before anything leaves your boundary, and why the
shareable receipt cannot carry PHI at all. Every mechanism below is inspectable
open source; the deeper dossier is
[Security and data handling](../guides/security-and-data-handling.md).

## 1. Scrubbing on the persist and log paths

PHI/PII scrubbing is provided by
[openadapt-privacy](https://github.com/OpenAdaptAI/openadapt-privacy)
(Presidio-backed named-entity recognition) through a single choke point in the
engine:

- The shareable `REPORT.md` passes every free-text field through the scrubber.
- Persisted step and heal frames are routed through image redaction.
- Drift-oracle console output is scrubbed before printing.
- A regulated deployment pins `OPENADAPT_FLOW_SCRUB=on` and **fails closed**: a
  missing scrubbing capability aborts the run instead of writing plaintext.
- There is no silent plaintext: in the default mode without the privacy extra,
  writing identity-like free text emits an explicit `PlaintextPHIWarning`.

**The identity boundary.** The recorded identity evidence and the identity audit
trail intentionally retain literal identifiers; scrubbing them would defeat
the wrong-record check they exist to power. Those artifacts are governed as
PHI-at-rest **inside your boundary** (filesystem controls, retention,
full-disk encryption, opt-in AES-256-GCM sealing), and the published privacy
map says so explicitly.

## 2. The local review gate before any upload

Nothing raw is uploaded. The only artifact lane to the hosted control plane is
the sanitized-derivative pipeline, and it puts a human decision between your
data and the wire:

1. `openadapt flow sanitize` builds a **derivative** with a file inventory and
   recorded transformations.
2. `openadapt flow review-sanitized` presents the derivative for **operator
   review** in a local viewer.
3. `openadapt flow approve-sanitized` records the explicit approval; only then
   can the derivative be pushed, and the control plane verifies the manifest,
   review state, and exact archive SHA-256 before accepting a byte.

Content the sanitizer cannot fully handle (databases, video, audio, nested
archives, symlinks, unknown binaries) refuses the **entire** derivative
rather than passing through. Sanitizer success is not treated as proof of
de-identification: the operator review is the gate.

## 3. The receipt is an allow-list

The shareable run receipt is generated **additively from a closed allow-list,
never redacted subtractively** from the rich operator report. Every field is a
closed enum, a bounded count, a digest, or a strictly validated version
string; an unknown key is refused rather than silently dropped.

Structurally unrepresentable in a receipt: screenshots, OCR text, typed
values, parameters, URLs, hostnames, coordinates, application name,
organization name, user name, workflow name, step intents, and halt free text.
The same principle governs the hosted attended-decision envelope (closed
enums, bounded integers, booleans; no string field, no image) and the hosted
break-report descriptor (hashed, coarse, no free text).

## Where each artifact can live

| Artifact | PHI posture | Boundary |
|---|---|---|
| Recording, bundle, `report.json`, identity evidence | Retains literal identifiers by design (audit + wrong-record check) | Stays inside your boundary; seal with AES-256-GCM for at-rest protection |
| `REPORT.md` | Scrubbed free text; redacted frames under the regulated pin | Your boundary; review before any sharing |
| Sanitized derivative | Operator-reviewed, transformation-manifested | May cross to the hosted control plane after explicit approval |
| Run receipt | Allow-list only; PHI structurally unrepresentable | Shareable |
| Hosted halt descriptor / decision envelope | Closed enums, counts, digests; no strings, no images | Hosted control plane |

## Related pages

- [Security packet](security-packet.md): the reviewer summary.
- [Subprocessors and hosted data retention](subprocessors.md)
- [Regulated execution](../concepts/regulated-execution.md)
- Engine [PRIVACY.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/PRIVACY.md):
  the complete path-by-path PHI map.
