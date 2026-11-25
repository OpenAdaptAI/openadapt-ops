---
description: >-
  Wrap agents running in Browserbase, Browser Use, E2B, Daytona, or a private
  VPC with OpenAdapt before-click checks and signed receipts.
---

# Verify agents in cloud sandboxes and private VPCs

You can run OpenAdapt verification around any browser or sandbox agent without
moving your agent code into OpenAdapt. `openadapt wrap` accepts a remote Chrome
DevTools Protocol (CDP) WebSocket URL for hosted browsers, uploads signed
receipts to `app.openadapt.ai` when you pass `--upload`, and `openadapt connect`
links a private Windows, Linux, or VPC runner over outbound HTTPS.

## Browserbase (remote CDP)

Pass your Browserbase session WebSocket URL via `--cdp-url` (or leave
`BROWSERBASE_CONNECT_URL` / `OPENADAPT_CDP_URL` in the environment). OpenAdapt
passes `OPENADAPT_CDP_URL` into the wrapped command while keeping your OpenAdapt
cloud keys and verifier credentials withheld.

```bash
pip install -U openadapt
export BROWSERBASE_CONNECT_URL="wss://connect.browserbase.com/?apiKey=$BROWSERBASE_API_KEY&sessionId=$SESSION_ID"
export OPENADAPT_CLOUD_KEY="$YOUR_OPENADAPT_KEY"

openadapt wrap \
  --task task.json \
  --cdp-url "$BROWSERBASE_CONNECT_URL" \
  --upload \
  -- python run_browserbase_agent.py
```

If `--cdp-url` is omitted, `openadapt wrap` reads `OPENADAPT_CDP_URL` first and
falls back to `BROWSERBASE_CONNECT_URL`.

## Browser Use

Wrap any `browser-use` Python script in one line. Your script keeps its own
model key and browser logic; OpenAdapt gates each save, reads back the target
record, and writes a signed receipt.

```bash
pip install -U openadapt browser-use
export OPENADAPT_CLOUD_KEY="$YOUR_OPENADAPT_KEY"

openadapt wrap \
  --task task.json \
  --cdp-url "$OPENADAPT_CDP_URL" \
  --upload \
  -- python browser_use_agent.py
```

Inside `browser_use_agent.py`, connect your browser session to
`os.environ["OPENADAPT_CDP_URL"]` (when driving a remote CDP browser) or call
the local MCP endpoint in `OPENADAPT_MCP_URL`.

## E2B and Daytona sandboxes

Install `openadapt` inside your E2B or Daytona container image (or at sandbox
startup) and pass `OPENADAPT_CLOUD_KEY` as a sandbox environment variable. Each
wrapped run verifies the write inside the container and posts the signed receipt
to `https://app.openadapt.ai`.

```bash
# Inside your E2B or Daytona sandbox
pip install -q openadapt
export OPENADAPT_CLOUD_KEY="$YOUR_OPENADAPT_KEY"

openadapt wrap \
  --task /workspace/task.json \
  --param invoice_id=INV-1042 \
  --upload \
  -- python /workspace/agent.py
```

OpenAdapt strips `OPENADAPT_CLOUD_KEY` and `OPENADAPT_API_KEY` from the wrapped
command's environment before starting your agent process, so the agent cannot
read your upload credential.

## BYOC connector (Windows, Linux, and private VPCs)

When the target application lives inside a private network, virtual desktop, or
Windows host that cloud sandboxes cannot reach, run the Bring-Your-Own-Compute
(BYOC) connector. It opens outbound HTTPS connections only; no inbound firewall
ports are required.

```bash
pip install -U openadapt
openadapt connect --token "$BYOC_CONNECTOR_TOKEN"
```

To generate a service configuration for a long-running host without echoing any
secret token, use `--print-service`:

```bash
openadapt connect --print-service windows --name clinic-runner-1
openadapt connect --print-service systemd --name vpc-runner-1
openadapt connect --print-service docker  --name vpc-runner-1
```

For workspace pairing on a personal desktop instead of a connector token, pass
`--pairing <CODE>` or `--uri <openadapt://connect...>` to `openadapt connect`.
