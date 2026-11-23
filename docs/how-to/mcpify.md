---
description: >-
  Turn any compiled workflow pack (.oapack.json) into a verified, zero-model-call
  local MCP stdio server with independent read-back and Ed25519 receipts.
---

# Expose a workflow pack with `mcpify`

!!! info "Upcoming release"
    This page documents `openadapt_verify.mcpify`, staged in
    [OpenAdapt#2577](https://github.com/OpenAdaptAI/OpenAdapt/pull/2577) for
    the upcoming `openadapt-verify` and launcher release.

`openadapt_verify.mcpify` turns any compiled workflow pack (`.oapack.json`
manifest) into a local Model Context Protocol (MCP) JSON-RPC 2.0 `stdio`
server. It uses only the Python standard library (zero external MCP SDK
dependencies), enforces zero model calls during deterministic execution,
checks every write against an independent read-back oracle, and emits an
Ed25519 signed receipt when confirmed.

## How `mcpify` verifies every tool call

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 255" role="img" aria-labelledby="oa-mcp-title oa-mcp-desc">
  <title id="oa-mcp-title">mcpify verified stdio MCP execution flow</title>
  <desc id="oa-mcp-desc">An MCP client such as Claude Desktop or Cursor calls a tool over local stdio JSON-RPC 2.0. McpifyServer validates inputs against the workflow pack schema, runs the compiled steps with zero model calls, and queries an independent read-back oracle (SQLite, JSON file, or custom callback). Matching reads return VERIFIED with an Ed25519 signed receipt; mismatches or abstains return HALT with isError true and a null receipt.</desc>
  <defs>
    <marker id="mcp-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="mcp-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
    <marker id="mcp-arr-s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-stopped"/>
    </marker>
  </defs>

  <!-- MCP Client -->
  <rect x="14" y="64" width="176" height="120" rx="12" class="oa-svg-panel"/>
  <text x="28" y="88" font-size="10" class="oa-svg-accent">MCP CLIENT</text>
  <text x="28" y="109" font-size="13.5" class="oa-svg-title">Claude or Cursor</text>
  <text x="28" y="130" font-size="11" class="oa-svg-muted">tools/list</text>
  <text x="28" y="147" font-size="11" class="oa-svg-muted">tools/call</text>
  <text x="28" y="169" font-size="10" class="oa-svg-mono">JSON-RPC 2.0 stdio</text>

  <path d="M190,124 L224,124" class="oa-svg-line-accent" marker-end="url(#mcp-arr)"/>

  <!-- McpifyServer -->
  <rect x="230" y="24" width="236" height="202" rx="12" class="oa-svg-panel-link"/>
  <text x="246" y="48" font-size="10" class="oa-svg-accent">ZERO-DEP STDLIB SERVER</text>
  <text x="246" y="69" font-size="14" class="oa-svg-title">McpifyServer</text>
  <text x="246" y="92" font-size="11" class="oa-svg-muted">1. Load .oapack.json manifest</text>
  <text x="246" y="112" font-size="11" class="oa-svg-muted">2. Validate input_schema</text>
  <text x="246" y="129" font-size="10" class="oa-svg-mono">   (-32602 on invalid args)</text>
  <text x="246" y="152" font-size="11" class="oa-svg-muted">3. Run compiled steps</text>
  <text x="246" y="169" font-size="10" class="oa-svg-mono">   enforces llm_calls == 0</text>
  <text x="246" y="196" font-size="10.5" class="oa-svg-mono">openadapt_verify.mcpify</text>

  <path d="M466,124 L500,124" class="oa-svg-line-accent" marker-end="url(#mcp-arr)"/>

  <!-- Independent read-back -->
  <rect x="506" y="54" width="200" height="140" rx="12" class="oa-svg-panel"/>
  <text x="522" y="78" font-size="10" class="oa-svg-accent">INDEPENDENT ORACLE</text>
  <text x="522" y="99" font-size="13.5" class="oa-svg-title">Read-back check</text>
  <text x="522" y="121" font-size="11" class="oa-svg-muted">• Read-only SQLite query</text>
  <text x="522" y="140" font-size="11" class="oa-svg-muted">• JSON file read-back</text>
  <text x="522" y="159" font-size="11" class="oa-svg-muted">• Custom oracle callback</text>

  <!-- Branches -->
  <path d="M706,96 L748,74" class="oa-svg-line-verified" marker-end="url(#mcp-arr-v)"/>
  <path d="M706,154 L748,176" class="oa-svg-line-stopped" marker-end="url(#mcp-arr-s)"/>

  <!-- VERIFIED -->
  <rect x="754" y="20" width="212" height="96" rx="12" class="oa-svg-panel-verified"/>
  <text x="770" y="44" font-size="11.5" class="oa-svg-verified-txt">VERIFIED</text>
  <text x="770" y="65" font-size="11.5" class="oa-svg-muted">Read-back agrees</text>
  <text x="770" y="84" font-size="11.5" class="oa-svg-muted">Ed25519 signed receipt</text>
  <text x="770" y="103" font-size="10" class="oa-svg-mono">verify_mcpify_receipt()</text>

  <!-- HALT -->
  <rect x="754" y="132" width="212" height="104" rx="12" class="oa-svg-panel-reconcile"/>
  <text x="770" y="156" font-size="11.5" class="oa-svg-reconcile-txt">HALT (isError: true)</text>
  <text x="770" y="177" font-size="11.5" class="oa-svg-muted">Mismatch, abstain, or error</text>
  <text x="770" y="196" font-size="11.5" class="oa-svg-muted">Expected vs. observed diff</text>
  <text x="770" y="216" font-size="10" class="oa-svg-mono">receipt: null · handoff</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Verified MCP tools:</strong> Every tool call is validated against the manifest schema, replayed with zero model calls, and checked by read-back before returning success.</span>
  <span><a href="../connect-an-agent/">Connect an agent &rarr;</a></span>
</figcaption>
</figure>

## Start the stdio MCP server

Serve one workflow pack manifest or a directory of `.oapack.json` packs:

```bash
python -m openadapt_verify.mcpify serve --spec path/to/workflow.oapack.json
```

Each workflow pack JSON file declares:

- `name` and `description` exposed in `tools/list`
- `input_schema`: typed JSON Schema validated before execution (unknown tools
  or missing/invalid arguments return JSON-RPC error `-32602`)
- `steps`: deterministic compiled steps (`McpifyServer` refuses any run where
  `llm_calls != 0`)
- `readback_contract`: independent read-back definition (built-in read-only
  SQLite or JSON file reader, or a custom Python oracle callback)
- `safety_policy`: refusal rules for mismatches, unreadable stores, and
  human-review handoff

## Generate Claude Desktop or Cursor config

Generate a ready-to-paste client configuration block:

=== "Claude Desktop"

    ```bash
    python -m openadapt_verify.mcpify config \
      --spec path/to/workflow.oapack.json \
      --client claude
    ```

=== "Cursor"

    ```bash
    python -m openadapt_verify.mcpify config \
      --spec path/to/workflow.oapack.json \
      --client cursor
    ```

=== "Generic MCP JSON"

    ```bash
    python -m openadapt_verify.mcpify config \
      --spec path/to/workflow.oapack.json \
      --client generic
    ```

## Verify Ed25519 receipts in Python

When independent read-back confirms the write, `McpifyServer` attaches an
Ed25519 signed receipt produced by `issue_mcpify_receipt()`. Any downstream
caller or auditor can verify it offline without running the server:

```python
from openadapt_verify.mcpify import (
    McpifyServer,
    generate_mcp_client_config,
    load_workflow_spec,
    verify_mcpify_receipt,
)

spec = load_workflow_spec("path/to/workflow.oapack.json")
# verify_mcpify_receipt(receipt, public_key_pem) returns True only if
# the signature matches and no field was altered.
```

If the read-back oracle disagrees, abstains, or cannot read the store,
`tools/call` returns `isError: true` with `status: "HALT"`, expected vs.
observed discrepancies, human-review handoff details, and `receipt: null`.

## Related pages

- [Connect an agent](connect-an-agent.md)
- [How a save is checked](../explanation/verification.md)
- [Receipts, Seals, and countersigning](../reference/receipts-and-seals.md)
