---
description: Answers to common procurement and vendor-risk questions about OpenAdapt.
---

# Procurement FAQ

This page doesn't create contract terms. The written proposal and agreement
do.

## Buying

**What does it cost?**
See the [pricing page](https://openadapt.ai/pricing). The engine is free to
run on your own computers.

**What do we get from a qualification sprint?**
A signed go or no-go decision for one workflow, with the evidence behind it.
See [Engagements](engagements.md).

**Does a sprint fee count toward production?**
Only if your written proposal says so.

## License and lock-in

**What license is the software under?**
The engine, recorder, agent, and launcher are MIT-licensed and public. The
hosted service is proprietary. Bundles and evidence produced for you are
yours.

**What happens if we stop paying?**
The engine keeps running on your computers. You lose the hosted services and
support. There is no license key that turns it off.

**Can we run everything ourselves?**
Yes, including fully offline deployments. See
[Deployment boundaries](deployment-boundaries.md) and
[Deploy](../how-to/deploy.md).

## Security and compliance

**Do you have SOC 2?**
No.

**Will you sign a BAA or process patient data in your cloud?**
The managed cloud runner is for data that isn't regulated. Workflows with
patient data run inside a boundary you control, where that data stays. A BAA
is decided per engagement.

**Where does our data live?**
See [Data handling](data-handling.md).

**Who are the subprocessors?**
See [Subprocessors](subprocessors.md). A fully local deployment uses none at
run time.

**How do we audit what it did?**
Every run writes a readable report and a machine-readable one: which record
was checked, what each record check found, any repairs, model calls, and why
it stopped. On-premises deployments add an append-only, hash-chained audit
log. See [Files and evidence](../reference/artifacts.md).

## Operation

**Does a person approve every save?**
Not necessarily. Each workflow is certified and admitted once before it runs
in production. Separately, the approval mode decides whether a run pauses
before each save: `openadapt flow run` pauses (`each_item`) unless the
deployment chooses another mode. Runs dispatched from OpenAdapt Cloud don't
pause per save; they
rely on certification, the right-record check, and the record check, and
stop when any of them can't confirm. See
[Verification](../explanation/verification.md#how-a-save-is-approved).

**What is a Seal? Is it a clinician's signature?**
A Seal is a signed receipt from OpenAdapt Cloud that a run's identity and
record checks passed. It isn't a signature by a person, and it doesn't make
OpenAdapt the legal actor. See [Execute](execute.md#the-seal).

**What if it gets something wrong without noticing?**
The acceptance target is zero runs that report success while the record
disagrees. Each save is read back through a path other than the screen, and
anything other than a confirmation stops the run. Your numbers come from
your own qualification.

**What are the known limits?**
See [Limits](../explanation/limits.md).

**Can another tool, such as Copilot or Power Automate, do the clicking?**
OpenAdapt is built to run the steps itself, so that it can check the record
before acting and read the save back after. Ask about your setup during
scoping.

**What support and requalification do we get?**
The production agreement sets the support channel, response targets, what
triggers requalification (such as an application upgrade), and how evidence
is refreshed.

**Insurance, indemnity, liability?**
Set by the agreement. Ask for current certificates.
