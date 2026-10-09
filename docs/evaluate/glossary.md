---
title: Plain-language glossary
description: >-
  The plain terms used on the Evaluate pages, the technical terms the rest of
  the OpenAdapt docs use for the same things, and what each one means.
---

# Plain-language glossary

The Evaluate pages use plain terms. The technical pages use exact ones. This
table maps one to the other, and each technical term links to the page that
explains it. The full technical glossary is in
[Reference](../reference/glossary.md).

| Plain term | Technical term | What it means |
|---|---|---|
| Workflow | Workflow | The task you hand off, such as entering a referral. |
| Showing the task, recording | [Demonstration](../concepts/demonstration-compiler.md), recording, capture | A person does the task once while OpenAdapt watches. |
| The automation | [Compiled program](../concepts/demonstration-compiler.md), [bundle](../reference/bundle-format.md) | What OpenAdapt builds from the recording. Technical pages call it the program. |
| Run | Run, replay | One time the automation does the task. |
| Done and checked | [`VERIFIED`](../reference/run-outcomes.md) | It saved the entry and read the record back to confirm it. |
| Stopped for review | [`HALTED`](../reference/run-outcomes.md) | Something didn't match, so it stopped before saving and asked a person. |
| Check if it saved | [`RECONCILIATION_REQUIRED`](../reference/run-outcomes.md#transaction-outcomes) | It can't tell whether the save went through, so a person checks before anything is retried. |
| Didn't finish | [`FAILED`](../reference/run-outcomes.md) | It couldn't complete the task and saved nothing it couldn't confirm. |
| Receipt, signed receipt | [Seal](../commercial/seal.md), receipt | A record of what was entered and how it was checked. It's called signed when the signature matters. |
| Readiness test | [Qualification](../guides/qualify-a-workflow.md), admission | Testing the automation on your system with your cases before it goes live. |
| Approved fix | [Governed repair](../concepts/self-healing.md), repair candidate | When a screen changes, OpenAdapt proposes a fix and a person approves it. |
| Screen changes | Drift, [re-resolve](../concepts/capability-ladder.md) | The app looks different. OpenAdapt finds the same field again or stops. |
| Right-record check | [Identity gate](../concepts/identity-gate.md), wrong-patient defense | It confirms it's in the right patient's chart before typing. |
| Record check | [Effect verification](../concepts/effect-verification.md), oracle, system-of-record read | It reads the saved record back from the system to confirm the change. |
| A person steps in | [Attended operation](../concepts/halt-learn-loop.md), takeover | Someone takes over or decides, then the automation continues. |
| The computer that runs it | Runner | A machine you control, or one we host. See [deployment boundaries](../commercial/deployment-boundaries.md). |
