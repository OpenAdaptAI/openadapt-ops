---
title: Security and where data stays
description: >-
  Where OpenAdapt runs, what leaves your network, what OpenAdapt Cloud
  receives, and what isn't available today. Written for a privacy or IT lead.
---

# Security and where data stays

For work with patient data, OpenAdapt runs on a computer you control, in your
office, your data center, or your own cloud account. Your screens and records
stay on that computer. Our hosted plan is the one exception, and it's for
browser work with non-regulated data only.

## Where it can run

| Option | Where it runs | What it's for |
|---|---|---|
| Your computer or server | A workstation, server, or virtual machine you manage | Any workflow, including patient data |
| Your cloud account | A machine in a cloud account you own | Any workflow, including patient data |
| A computer we host ($29/month) | OpenAdapt's cloud | Browser workflows with non-regulated data only. It's not for patient data. |

On a computer we host, the workflow runs in OpenAdapt's cloud, and that
computer sees the pages it works on. That's why it's only for non-regulated
data. Desktop and Citrix workflows run on a computer you control. Our
$29/month hosted computers don't take them. Prices are on the
[pricing page](https://openadapt.ai/pricing).

## What leaves your network

In a normal run, nothing has to. A normal run makes no AI model calls and sends
no usage data. In a fully local setup, a normal run makes no outbound calls at
all, and your IT team can test that with a script we provide.

If you connect a computer to OpenAdapt Cloud to see run history:

- Cloud receives each run's status, counts, ID numbers for the run and the
  workflow, and fingerprints of the evidence. When a run stops, it gets a coded description of the kind of
  problem.
- From your runs, Cloud doesn't receive screenshots, typed values, or free
  text.
- To upload a workflow, OpenAdapt makes a cleaned copy on your computer. A
  person reviews it and approves it, and only that approved copy is sent.
  Anything the cleaner can't handle, such as video or a database file, blocks
  the upload.

AI model help is off by default. If you turn it on to cope with screen changes,
it calls a model server at an address you choose, which can sit inside your
network.

## Passwords and patient data on disk

- Password fields are left out of recordings, along with any field you mark
  as secret. The computer that runs the workflow supplies them at run time
  from its environment or keychain.
- To confirm it's in the right record, the automation keeps the identifiers it
  needs. They stay on your computer, protected by your disk encryption and
  access controls. You can also encrypt the automation itself with a key you
  manage.
- The shareable receipt can't contain patient data. Its fields are fixed, and
  none of them holds free text or an image.

## What isn't available today

| Item | Status |
|---|---|
| SOC 2 | OpenAdapt doesn't hold a SOC 2 report and doesn't claim any certification. |
| BAA | There's no standard BAA. Hosted isn't for patient data. For an Enterprise engagement, a BAA is agreed case by case with counsel. |
| Hosted desktop and Citrix workflows | The $29/month hosted plan runs browser workflows only. Shared hosting for desktop workflows in OpenAdapt's cloud is deferred. |
| Signed Desktop installers | The Windows and Linux installers are unsigned, and the macOS installer is ad-hoc signed. Check the published checksums before you install. |
| Penetration test | Ask us for the current status. |

We don't publish dates for these items. Ask us for the current status before
you rely on any of them.

??? note "Technical details"
    These pages give the full detail, with links to the engine's own security
    documentation:

    - [Security and data handling](../guides/security-and-data-handling.md)
    - [Security packet](../commercial/security-packet.md)
    - [PHI handling in one page](../commercial/phi-handling.md)
    - [Deployment boundaries](../commercial/deployment-boundaries.md)
    - [Subprocessors and hosted data retention](../commercial/subprocessors.md)
    - [Security and deployment review](../guides/security-review.md)
    - [OpenAdapt trust center](https://openadapt.ai/security)
