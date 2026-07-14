# The bundle format

A **workflow bundle** is the deployable artifact that `compile` produces and
`replay`, `lint`, and `certify` consume. It is a self-contained directory: you
version it, review it, and ship it.

!!! note "Authoritative schema"
    This page describes the bundle at a conceptual level. The exact, versioned
    schema lives in the engine repository (`DESIGN.md` for the shipping v0 IR,
    and [`WORKFLOW_PROGRAM_IR.md`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/design/WORKFLOW_PROGRAM_IR.md)
    for the program IR it evolves toward). Treat the repo as the source of truth
    for field names.

## What a bundle holds

A bundle carries the compiled workflow plus the per-step evidence the replayer
needs to re-find each target:

- **The compiled workflow** (`workflow.json`): the ordered steps and, per step,
  its risk classification and its identity-coverage metadata (`identity_armed`,
  `identity_unarmed_reason`). This is what makes a bundle auditable **before** it
  runs: you can see which steps write and which clicks are identity armed
  without replaying anything.
- **Per-step evidence**: for each step, the redundant anchors the
  [resolution ladder](../concepts/self-healing.md) tries in order: a template
  crop of the target, an OCR label, and geometry landmarks relative to stable
  neighbours.
- **Postconditions**: the assertions derived from what the demonstration
  actually changed on screen, checked after each action.
- **Effects** (when declared): the typed system-of-record assertions
  (`record_written`, `field_equals`) that [effect
  verification](../concepts/effect-verification.md) checks against an API or
  database.

## The step model

Each step is a single primitive (`CLICK`, `DOUBLE_CLICK`, `TYPE`, `KEY`, `WAIT`,
`SCROLL`) carrying:

| Element | Purpose |
|---|---|
| Anchor | Template crop, OCR label, and geometry landmarks used to re-find the target |
| Identity band | The recorded discriminating row text, when the step is identity armed |
| Postconditions | Screen assertions about what should change after the action |
| Effects | Optional typed assertions against the system of record |
| Risk | `reversible` or `irreversible`, auto-classified at compile time, overridable |

## Risk classification

At compile time, write-shaped clicks (create, update, delete, submit, save,
confirm, add, and siblings) are auto-classified `irreversible`, which arms the
low-confidence refusal for those steps. The classifier reads labels and intent
only, so it can miss a write behind a non-write label; a `risk_overrides` map
corrects it in either direction. See [Policy and certify](../concepts/policy-and-certify.md).

## Schema v2: manifest, digest, provenance, validation

The bundle is the **trust boundary** between the compiler and the deterministic
replayer: everything the replayer will do to a real system of record is frozen in
`workflow.json` and its template PNGs. Schema v2 hardens that boundary
additively — it never rewrites an existing bundle's semantics.

- **Manifest / provenance** (`manifest.json`, also embedded in `workflow.json`):
  a per-asset **SHA-256** hash of every template/image, a whole-bundle
  `content_digest`, the **compiler version** that produced the bundle, and — for
  a certified bundle — the policy it was certified against, its certification
  status, and an optional expiry.
- **Integrity check on load**: the digest is recomputed on read, so a bundle
  whose `workflow.json` or assets were tampered with after the manifest was
  sealed is refused, not silently run.
- **Load-time structural validation**: a malformed or uncertifiable graph is
  rejected with clear, per-issue errors **before** the replayer touches it.
  Rules span graph well-formedness (entry exists, every transition target
  resolves, state kinds match their payloads, referenced subflows exist, ids are
  unique, terminals reachable, no unsafe unconditional cycle) and the one safety
  rule that motivates the rest: **every path that reaches a consequential /
  irreversible action also reaches its effect verification.**
- **Clean migration**: a v1 bundle (or one with no `schema_version`) migrates to
  v2 in memory on read. v2 is a strict superset of v1, so an existing bundle
  keeps replaying byte-for-byte — migration only stamps the version and
  back-fills a manifest if one is absent.

The manifest is sealed on `save` and written both inside `workflow.json` and as a
standalone `manifest.json` sidecar for external tooling. This layer is
import-light (no OCR / cv2 / model dependencies), so it is safe to run on every
load.

```
<bundle>/
  workflow.json      # ir.Workflow (+ embedded manifest)
  manifest.json      # sealed integrity + provenance sidecar (schema v2)
  templates/*.png    # anchor crops (hashed in the manifest)
```

## Auditing a bundle without running it

Because the workflow and its coverage metadata are in the bundle, you can audit a
workflow statically:

```bash
openadapt flow lint    bundle                       # coverage gaps, by severity
openadapt flow certify bundle --policy clinical-write   # refuse if a policy fails
```

`lint` and `certify` read exactly this bundle metadata to report gaps and enforce
a policy. Every run then writes its own report separately under `runs/`; see
[Read and audit run reports](../guides/run-reports.md).

## Emitting other formats from a bundle

A bundle can be emitted as an Agent Skills folder or a standalone MCP server, so
other agents can invoke the workflow:

```bash
openadapt flow emit-skill bundle --out skills/
openadapt flow emit-mcp   bundle --out server.py
```

## Recording versus bundle

The **recording** (`record` / `demo-record` output) is the raw demonstration:
input events plus before/after frames. The **bundle** (`compile` output) is the
compiled program. `compile` consumes the former and produces the latter; deploy
the bundle, not the recording.
