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
  a browser. Teach the specific case, or use a surface with structure where
  the app offers one. Don't lower the check.
- **First runs of a new recording.** Expect `lint` warnings and
  `clinical-write` refusals until record checks and right-record checks are
  complete.
- **Screens that change between finding a target and acting**, such as a
  late notification. The step stops rather than click a stale target.

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
