---
description: >-
  Install and use openadapt-kernel for commit-boundary verification,
  obligation tracking, PortalPack induction, and Stage-Only PrepareCard loops.
---

# openadapt-kernel

`openadapt-kernel` is a minimal, self-contained runtime kernel with no
`openadapt-flow` dependency and no per-application code. It implements
commit-boundary detection, obligation tracking, cross-rail read-back checks,
zero-PII `PortalPack` induction, and Stage-Only form preparation.

## Install from source

`openadapt-kernel` does not have a standalone PyPI release yet. Until that
release lands, install it directly from the `OpenAdapt` repository:

```bash
git clone https://github.com/OpenAdaptAI/OpenAdapt.git
pip install -e OpenAdapt/packages/kernel
```

Once installed, invoke it either as `openadapt kernel` (through the main
`openadapt` CLI) or directly as `openadapt-kernel`.

## Core components

- **`CommitInterceptor` (`interceptor.py`):** Detects commits from actual
  network mutations (`POST`, `PUT`, `PATCH`, `DELETE`) or non-empty dirty form
  submissions instead of matching button labels. Search and filter inputs are
  excluded from dirty buffers.
- **`ObligationLedger` (`ledger.py`):** Starts every episode in `UNVERIFIED`
  and emits `VERIFIED` only when every obligation has an independent
  post-commit read-back proof and no dirty form buffers remain. Step-limit
  timeouts, crashes, and unverified exits return `ESCALATED`.
- **`PortalPack` (`copilot.py`):** A zero-PII portal specification induced
  from live Chrome Co-Pilot `extension_evidence.jsonl` recordings. Packs are
  qualified offline against four counterfactual mutants without needing a
  staging database.
- **`ShadowObserver` (`copilot.py`):** Captures shadow traces from human
  portal runs so the kernel can induce and update `PortalPack` definitions.
- **`PrepareCard` Stage-Only loop:** Stages pre-verified form bindings in
  `DRAFT_TO_COMMIT` mode and stops before submitting. Any field that cannot be
  bound automatically is emitted as a zero-PHI `PrepareCard` for human
  sign-off in the [PREPARE Sign-Off Queue](../cloud/prepare-queue.md) before
  commit.

## CLI quickstart

Induce a `PortalPack` from Chrome Co-Pilot recordings, qualify it offline,
generate an Ed25519 receipt keypair, and run in draft or verified autopilot
mode:

```bash
openadapt kernel shadow-sync --dir ./recordings --pack-id portal-v1 --out pack.json
openadapt kernel qualify --pack pack.json --evidence ./recordings/run_1/extension_evidence.jsonl
openadapt kernel keygen --priv priv.pem --pub pub.pem
openadapt kernel run --pack pack.json --dossier dossier.json --mode draft --cdp-url http://127.0.0.1:9222
openadapt kernel run --pack pack.json --dossier dossier.json --mode autopilot \
  --url https://portal.example --commit-selector '[data-testid="submit-btn"]' \
  --priv priv.pem --receipt-out receipt.json
openadapt kernel verify-receipt --receipt receipt.json --pub pub.pem
```

To expose kernel tools over stdio JSON-RPC 2.0 MCP:

```bash
openadapt kernel serve-mcp
```

## Related guides

- [Chrome Co-Pilot extension](chrome-copilot.md): record live browser sessions
  and stage drafts in your signed-in Chrome profile.
- [PREPARE Sign-Off Queue](../cloud/prepare-queue.md): review and sign off
  staged `PrepareCard` items across offices.
- [How a save is checked](../explanation/verification.md): why commit-boundary
  read-back checks refuse unverified saves.
