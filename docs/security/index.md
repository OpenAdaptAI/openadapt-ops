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
open, and after each save it reads the record back through a path other than
the screen, such as the application's API or database. Any check that fails
or can't tell stops the run. Every run writes a report; on-premises
deployments add an append-only, hash-chained audit log. The engine is
open source under the MIT license, so these controls can be read in the
source.

## Core controls

| Control | What it does |
|---|---|
| Local execution | A local or on-premises run sends nothing outside your network by default. `verify-airgap.sh` checks the software side and probes that a public address can't be reached. |
| Right-record check | Before an armed action, the screen must show the record the inputs name. |
| Record check | After a save, an independent read confirms it. `refuted` and `indeterminate` both stop the run. |
| Governed run gate | Under Standard and Regulated, `run` refuses to start without certification, identity coverage, record checks, and a production admission. Regulated also refuses unencrypted bundles. |
| Encryption at rest | Optional AES-256-GCM for bundles, crops, and checkpoints with `OPENADAPT_BUNDLE_KEY`, on top of your disk encryption. Key management stays yours. |
| Single-use authorization | Each governed run's authorization is bound to the bundle digest, input digest, policy, and record-check digests. |
| Secrets | Secret fields never enter recordings, bundles, or screenshots. Values come from the environment or the OS keychain at run time. |
| Model calls | Off by default. Turning them on is an explicit setting, and patient-data mode limits model endpoints to an allowlist. |
| Changes to a program | A repaired program passes review, replay and fault campaigns, approval by a person, and a canary before it replaces the active one. |

## Attestation status

| Item | Status |
|---|---|
| SOC 2 | Not attested. OpenAdapt doesn't hold a SOC 2 report. |
| HIPAA BAA | No standing BAA offering. Workflows with patient data run inside a boundary you control. A BAA and counsel review are per engagement. |
| Penetration test | Ask for current status. |
| Vulnerability disclosure | See [Vulnerability disclosure](vulnerability-disclosure.md). |
| Subprocessors | Hosted services only. See [Subprocessors](subprocessors.md). |
| Supply chain | GitHub Actions pinned by commit SHA, Dependabot, and checksums plus a software bill of materials on Desktop releases. See [Release integrity](release-integrity.md). |

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
