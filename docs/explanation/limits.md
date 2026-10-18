---
description: >-
  What OpenAdapt doesn't do, where it stops more often, and what its results
  don't prove.
---

# Limits

## What a result proves

- `VERIFIED` means each save was confirmed by a record check that was
  configured for that save. A field the check doesn't compare can still be
  wrong, and a value that was wrong in the source document is entered as
  given.
- A qualification pass covers the environment it ran in: the application
  version, browser, screen size, and system of record it was tested against.
  A new application version or a changed screen needs a new qualification.
- Zero model calls doesn't mean zero network traffic. The application, the
  record check, and a Cloud connection can still use the network.
- Deterministic means the program fixes the steps, inputs, targets, and
  checks. It doesn't mean the application returns the same screens every
  time, or that a step is safe to repeat.

## What it doesn't cover

- **Steps without a right-record check.** A compiled program arms that
  check on a subset of its clicks; one OpenEMR program armed 4 to 7 of 12.
  A click that isn't armed has no right-record check. `lint` and every run
  report list which steps are armed.
- **Saves without a record check.** Without one, a run can't end
  `VERIFIED`, and Standard and Regulated refuse the save. Record checks are usually
  written per deployment, against the app's system of record.
- **Redesigned workflows.** Re-finding a moved or restyled control is in
  scope. A changed sequence of screens or changed business rules needs a new
  demonstration or a taught fix.
- **Unattended clinical judgment.** OpenAdapt enters what it's given. It
  doesn't decide what belongs in the record.

## Where it stops more often

- **RDP and Citrix.** With only pixels, identifiers with confusable
  characters can't always be read with confidence, so runs stop more than in
  a browser. On pixel-only screens the right-record check stops whenever the
  right patient's own record number has look-alike characters, such as `O`
  and `0`. On our test corpora that was 47 to 61 in 100 correct-patient
  checks, re-measured 17 October 2026
  ([identity evidence](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/validation/IDENTITY_EVIDENCE.md)). Those are
  extra stops, not wrong entries. A confirmed export of the system's record
  numbers (`runtime.known_ids`, openadapt-flow 2.2.0) lifts a stop when
  exactly one listed number fits; on a rendered record list, stops on the
  right row fell from 176 to 3 in 280 clicks whose neighboring row wasn't a
  look-alike twin ([results](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/known_ids/KNOWN_IDS.md)). Teach the specific case, or use a surface with structure where the
  app offers one. Don't lower the check.
- **First runs of a new recording.** Expect `lint` warnings and
  `clinical-write` refusals until record checks and right-record checks are
  complete.
- **Screens that change between finding a target and acting**, such as a
  late notification. The step stops rather than click a stale target.

## Limits by surface

Each row is what's on record for that surface and what that evidence doesn't
show. A given application on a given surface still needs its own
qualification.

| Surface | On record | What it doesn't show |
|---|---|---|
| Browser | OpenEMR referral entry, 14 to 15 Oct 2026: of 63 new-patient referrals, 62 saved and read back 12 of 12 fields; 9 of 9 possible duplicates with no new chart, 0 model calls ([run data](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/openemr_referral_timing/README.md)) | One workflow on a local test copy with synthetic patients. The read-back was our test setup's, so the engine labeled the runs finished, not checked. No commercial EMR tested. |
| Windows | 3 of 3 saves in our WinForms app confirmed in SQLite; 3 of 3 refusals each for stale and ambiguous targets; 0 model calls ([report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/windows_uia/results.json)) | Our own app on one Windows 11 ARM VM snapshot. RDP and Citrix recordings don't use local UI Automation. |
| macOS | 3 of 3 TextEdit saves matched byte for byte; refused an ambiguous two-window target without changing either file ([adjudication](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json)) | One macOS 15.7.3 host and one app. The original report reads failed because of cleanup warnings; the adjudication accepts the saves and the refusal. |
| Linux (X11) | In required CI on Ubuntu 24.04: a GTK3 app, 3 confirmed saves, 3 ambiguous-target and 3 stale-target refusals | Our own app on Xvfb. No Wayland, no third-party apps. |
| RDP | Windows 11 VM over Aardwolf: 3 of 3 file writes confirmed by a separate guest check ([report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/rdp/results_82a658a_20260718.sanitized.json)). Record, compile and replay over FreeRDP: 3 of 3 saves, 3 of 3 stops under drift ([report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/rdp_ladder/results.json)) | The FreeRDP run used a synthetic Linux app, not a Windows app, and drift wasn't captured over a WAN. Pixel-only, so the false-stop rate above applies. |
| Citrix | 3 confirmed saves and 3 stops under severe drift on a stand-in window with no DOM; 0 model calls ([report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/citrix_workspace/results.json)) | No run over a real Citrix ICA/HDX connection is on record. Each Citrix deployment is qualified in its own environment. Pixel-only, so the false-stop rate above applies. |

The full failure inventory, with evidence for each entry, is in
[`packages/flow/docs/LIMITS.md`](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/LIMITS.md).

## Surfaces and lanes still being proven

- Citrix has no counted run over real ICA/HDX on record yet.
- Agent-driven recording on native Windows, RDP, and Citrix is tested
  against mocks only.
- Qualification's fault staging works in the browser only. On other
  surfaces, `qualify` refuses targets other than `web`.
- `problems_only` approval isn't available to customers yet.
- The managed Cloud runner runs browser workflows only. It isn't a lane for
  patient data.

## What OpenAdapt doesn't configure for you

In an on-premises deployment, your team owns the firewall, disk encryption
and key management, storage, identity provider, backups, retention, incident
response, and compliance program. OpenAdapt supplies the run gates, egress
checks, and audit log that sit inside them.
