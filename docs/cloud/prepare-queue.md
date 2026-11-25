---
description: >-
  Review and sign off staged PrepareCard drafts across offices at
  app.openadapt.ai/prepare with forced-choice keyboard shortcuts, zero-PHI
  previews, and SHA-256 signed decisions.
---

# Multi-Office PREPARE Sign-Off Queue

The `PREPARE` Sign-Off Queue at
[app.openadapt.ai/prepare](https://app.openadapt.ai/prepare) lets operators
review and clear staged claims, quotes, and portal drafts across multiple
offices and portals from one screen.

## Try the live preview

Open [app.openadapt.ai/prepare?demo=1](https://app.openadapt.ai/prepare?demo=1)
to inspect the queue with sample cards and zero setup. You can also filter the
queue by office or portal with query parameters such as `?office=...` and
`?portal=...`.

## Keyboard shortcuts

Every card can be cleared without leaving the keyboard:

| Key | Action |
|---|---|
| `1` to `9` | Select an option for the active highlighted field and advance to the next unresolved field |
| `A` | Approve and sign off the card (enabled only after every unresolved field is bound) |
| `R` | Reject the card |
| `S` | Skip the card and move it to the back of the pending queue |

## Safety invariants

- **Anti-rubber-stamping:** Bulk approval (`approve_all: true`) is rejected
  whenever a card has unresolved fields. Each highlighted field requires an
  explicit forced-choice binding to a declared `$var` or an allowed enum option
  before **Approve & Sign Off** becomes active.
- **Zero-PHI previews:** Cards and resolutions contain only variable
  references (`$var`), enum options, control labels, selectors, and masked
  suffixes. Raw Social Security numbers, phone numbers, and email addresses are
  rejected before a card can enter the queue.
- **SHA-256 signed decisions:** Every approve or reject decision produces a
  deterministic SHA-256 digest over the canonical resolution payload. The
  digest is recorded in the queue's audit trail so downstream runners can
  verify what the operator signed off before committing.

## Related guides

- [openadapt-kernel](../guides/openadapt-kernel.md): generate `PrepareCard`
  drafts in Stage-Only mode.
- [Chrome Co-Pilot extension](../guides/chrome-copilot.md): stage form drafts
  inside your signed-in Chrome session.
- [Review a repair](review-a-repair.md): approve or reject proposed workflow
  repairs in OpenAdapt Cloud.
