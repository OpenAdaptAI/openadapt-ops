---
description: >-
  Review a repaired workflow in OpenAdapt Cloud before the runner tests it.
  Cloud records the decision; it never applies a repair.
---

# Review a repair

When a run stops because the application changed, a repair proposes a new
version of the workflow. Before the runner tests it, a person reviews what
changed. You can do that review in Cloud instead of at the runner. Cloud only
records the decision; the runner's own steps still decide whether the repair
is used. See [Handle a halt](../how-to/handle-a-halt.md#5-promote-the-repaired-program)
for the full sequence.

## 1. Send the candidate to Cloud

On the runner, sign in with an ingest token once (`openadapt flow login`).
Then send a registered repair candidate with the engine's Python API:

```python
from openadapt_flow.repair.cloud_review import propose_to_cloud
from openadapt_flow.repair.lifecycle import RepairStore

store = RepairStore("repair-store")          # the --store the repair commands use
candidate = store.load_candidate("<candidate id>")
result = propose_to_cloud(candidate, workflow_id="<Cloud workflow id>")
print(result["review_url"])
```

What Cloud receives is digests only: for each changed step, the field and the
SHA-256 before and after; the failure fingerprints; and the digests of the
old and new bundle. No file path, screen text, or field value leaves the
runner. A change counts as consequential unless every changed step is marked
reversible.

## 2. Decide in Cloud

Open **Repairs** at `/dashboard/repairs`. Each candidate shows the before and
after fingerprints for each changed step, why the run stopped, and the bundle
digests. An owner or admin chooses:

- **Approve for testing**: the runner may now run its replay and fault tests
  on this version.
- **Reject**: the workflow keeps its current version and keeps stopping at
  that step.

Approving a change to how the record is identified, or to a step that saves
data, needs an extra confirmation. A decision is final, and it is bound to the
exact digests the reviewer saw. Only a person can decide; Cloud refuses a
decision from a model.

## 3. Apply the decision on the runner

The runner reads decided candidates from `GET /api/repairs/decisions` with
its ingest token and applies each one:

```python
from openadapt_flow.repair.cloud_review import apply_cloud_decision

apply_cloud_decision(store, decision)
```

An approval counts as the diff review (`candidate` → `reviewed`). A rejection
rejects the candidate. A decision made for different bundle bytes is refused.
The replay campaign, the fault campaign, the final approval, staging, and the
canary still run on the runner:

```bash
openadapt flow repair campaign <id> --kind replay
openadapt flow repair campaign <id> --kind fault
openadapt flow repair approve <id> --approved-by "jane@example.com"
openadapt flow repair stage <id>
openadapt flow repair canary <id> --max-runs 5
```
