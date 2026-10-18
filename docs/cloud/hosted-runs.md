---
description: >-
  How OpenAdapt Cloud schedules runs on its managed runner: one hosted run in
  progress per organization, the rest in a first-in, first-out queue.
---

# How hosted runs queue

A hosted run is one that Cloud runs on its managed runner, such as a browser
workflow. On the Team plan, an organization has at most one hosted run in
progress at a time. A custom or Enterprise plan can allow more. For prices,
see [openadapt.ai/pricing](https://openadapt.ai/pricing).

## What happens when you start a run

| The run | While another hosted run is in progress |
|---|---|
| Started from the dashboard or `POST /api/runs` with no inputs | Waits in the queue. The response is `202` with `hosted_queue.position` |
| A scheduled run | Waits in the queue |
| Started with typed inputs, or an Execute request | Refused with `409` and code `hosted_run_in_progress`. Retry when the current run finishes |
| A run on your own computer (a connected runner) | Not affected; it doesn't use a hosted slot |

Runs with inputs can't wait because Cloud doesn't store a run's inputs.

## Order

Waiting runs start in the order they were queued. When a hosted run finishes,
Cloud starts the oldest waiting run. Cloud also checks the queue every
scheduler tick, so a run whose slot was freed by a lost or timed-out run
still starts.

Each run goes to the managed runner at most once. A workflow can have only
one active run, so a second run of the same workflow is refused, not queued.
