---
description: >-
  OpenAdapt's security posture for security, vendor-risk, and procurement
  reviewers: architecture, controls, attestations, and where to find detail.
---

# Security and procurement

This section is for security reviewers, vendor-risk teams, and procurement.
Nothing here is a compliance determination. For anything a contract or
questionnaire must cite, ask for the current signed artifact.

## The architecture in one paragraph

OpenAdapt runs on a computer inside your network that can already open the
application. It replays a compiled program with no model calls on a healthy
run. Before each consequential action it checks that the right record is
open, and after each consequential change it checks the target state on a
four-level ladder: through the application's API, database, or file export
(`system_of_record`), a separate read-only session (`separate_session`), an
idempotent reload or reopen (`reopened`), or a bounded check on the settled
screen (`same_screen` under `Standard`; `Regulated` requires at least
`separate_session` or `system_of_record`). Every report and receipt records
`checked_how`, and any check that fails
or can't tell stops the run. Every run writes a report; on-premises
deployments add an append-only, hash-chained audit log. The engine is
open source under the MIT license, so these controls can be read in the
source.

## Core controls

| Control | What it does |
|---|---|
| Local execution | A local or on-premises run sends nothing outside your network by default. `verify-airgap.sh` checks the software side and probes that a public address can't be reached. |
| Right-record check | Before an armed action, the screen must show the record the inputs name. |
| Record check | After a consequential change, a graded check confirms the target state and stamps `checked_how`. `refuted` and `indeterminate` both stop the run. |
| Governed run gate | Under Standard and Regulated, `run` refuses to start without certification, identity coverage, record checks, and a production admission. Regulated also refuses unencrypted bundles. |
| Encryption at rest | Optional AES-256-GCM for bundles, crops, and checkpoints with `OPENADAPT_BUNDLE_KEY`, on top of your disk encryption. Key management stays yours. |
| Single-use authorization | Each governed run's authorization is bound to the bundle digest, input digest, policy, and record-check digests. |
| Secrets | Runtime secret inputs come from the environment or OS keychain. Protect recordings and run artifacts inside the deployment boundary. See [Data handling](data-handling.md). |
| Model calls | Off by default. Turning them on is an explicit setting, and patient-data mode limits model endpoints to an allowlist. |
| Changes to a program | A repaired program passes review, replay and fault campaigns, approval by a person, and a canary before it replaces the active one. |

## Security assurance

Readiness work, agreement preparation, and application testing each have a
scope and evidence record. The current phases are:

| Area | Current phase |
|---|---|
| SOC 2 | **Type I readiness underway**, covering the Security and Confidentiality criteria. As of 2026-11-20, the system description, control mapping and security policies are drafted, and a dated readback of our source-control and CI settings is recorded. We don't hold a SOC 2 report yet. |
| HIPAA BAA | **Readiness underway; deployment review packet prepared.** Workflows with patient data run inside a boundary you control. Data-flow questions, agreement review notes and a safeguards checklist are ready for each engagement's review. A BAA is decided per engagement. |
| Security testing | **Internal testing underway.** The first round of testing of the hosted service, on a staging copy, ran on 2026-11-20. An independent penetration test is planned. |
| Vulnerability disclosure | Private reporting is available. See [Vulnerability disclosure](vulnerability-disclosure.md). |
| Subprocessors | Hosted services only. See [Subprocessors](subprocessors.md). |
| Supply chain | GitHub Actions pinned by commit SHA, Dependabot, and checksums plus a software bill of materials on Desktop releases. See [Release integrity](release-integrity.md). |

For the current security packet or a scoped deployment review, email
[hello@openadapt.ai](mailto:hello@openadapt.ai).

## Pages in this section

- [Data handling](data-handling.md): where each kind of data lives, how
  patient data is scrubbed, and what may leave your network.
- [Deployment boundaries](deployment-boundaries.md): the three places a
  workflow can run and what crosses each boundary.
- [Evidence](evidence.md): what has been tested, on which surface, and how.
- [Subprocessors](subprocessors.md): hosted providers, what runs send to
  OpenAdapt, and retention.
- [Release integrity](release-integrity.md): which releases are admitted for
  production, and how to check a download.
- [Engagements](engagements.md): how a workflow is qualified with OpenAdapt,
  what you provide, and what you get.
- [Execute](execute.md): the API for software providers.
- [Procurement FAQ](procurement-faq.md).
- [Vulnerability disclosure](vulnerability-disclosure.md).

The engine's own list of limits is in
[Limits](../explanation/limits.md).
