---
description: >-
  Give an AI agent your compiled workflows as tools over MCP, read the four
  outcomes, and write an Agent Skill for one workflow.
---

# Connect an agent

Your agent decides what to enter. OpenAdapt enters it in the app and checks
that it saved. The OpenAdapt MCP server gives the agent each compiled
workflow as one typed tool call. The agent sends inputs and gets back an
outcome; it doesn't drive the screen, and by default it never sees recorded
values or screens.

The server runs over local stdio on the computer that can open the app. It
needs Python 3.10 to 3.12.

## Try the sandbox

The sandbox has one workflow, `add_triage_note`, and needs no account. In
Claude Code:

```bash
claude mcp add openadapt -- uvx --python 3.12 openadapt-agent serve
```

Start `claude` in the same folder and ask: "Use OpenAdapt to add the triage
note 'Synthetic: recheck blood pressure in 2 weeks' with request id
demo-0001." The agent calls `list_workflows`, then `run_workflow`, and gets:

```json
{
  "outcome": "done",
  "label": "Done and checked",
  "safe_to_retry": false,
  "next_step": "none",
  "proof": "simulated",
  "model_calls": 0
}
```

This sandbox simulates each run. To have the engine drive the MockMed test app
in a hidden browser, install the `tutorial` extra instead:

```bash
claude mcp remove openadapt
claude mcp add openadapt -- uvx --python 3.12 --from 'openadapt-agent[tutorial]' openadapt-agent serve
```

Add `sandbox_case` to the inputs to see each outcome: `normal`,
`duplicate_record`, `false_saved_banner`, `timeout_after_save`, or
`app_offline`.

For any client that reads an `mcpServers` file, such as Claude Desktop or
Cursor:

```json
{
  "mcpServers": {
    "openadapt": {
      "command": "uvx",
      "args": ["--python", "3.12", "openadapt-agent", "serve"]
    }
  }
}
```

## Serve your own workflows

```bash
openadapt agent serve --mode production --bundles /srv/openadapt/bundles \
  --runs-dir /var/lib/openadapt/runs --config deploy.yaml
```

| Mode | What the agent gets |
|---|---|
| No `--mode`, with `--bundles` | Your workflows, listed but not runnable, plus read-only tools for past runs |
| `--mode production` | Runs of your workflows |
| `--mode attended` | Runs, plus decisions on stopped runs by a person at this computer |

Each run goes through `openadapt flow run`, so every gate in
[Run a workflow](run.md) applies. A workflow that isn't ready returns
`did_not_run` with `not_ready_to_run`, and `failed_checks` names what's
missing, such as `not_certified`. Expect that the first time you serve a new
recording.

The agent can't change `--url`, `--config`, `--policy`, `--timeout`, or
`--approval-mode`. Give every server for the same work the same absolute
`--runs-dir`: the check that stops a second entry covers one runs folder.

## The four outcomes

| `outcome` | What happened | What the agent does next |
|---|---|---|
| `done` | Saved, and the record check confirmed it | Mark the request complete. Don't send it again. |
| `needs_review` | Stopped before a save, waiting for a decision. Nothing was written, unless `record_changed` is `unknown`. | Don't start the work again. Call `get_run` later. |
| `not_sure_if_saved` | A save may have gone through, but it wasn't confirmed | Never retry. A person checks the record. |
| `did_not_run` | This call wrote nothing | If `safe_to_retry` is true, fix the cause and resend the same request. |

Only `done` means the save was confirmed. Never summarize a halt as success
when you report back to a person. While a run is still going, `outcome` is
`running`; call `get_run` until it changes. Branch on `outcome` and `safe_to_retry`. `next_step` is a fixed
code: `none`, `call_get_run`, `wait_for_person`, `check_record`,
`fix_inputs`, `fix_setup`, or `retry`. The mapping from engine outcomes is in
[Run outcomes](../reference/outcomes.md#what-an-agent-sees).

Every `run_workflow` call carries your own `request_id`. Sending the same
request again never enters the values twice; it returns the earlier result.

## Approvals

Each save waits for approval unless the operator starts the server with
another `--approval-mode`. While it waits, the agent gets `needs_review` with
the reason `waiting_for_approval`. A person answers on the computer that runs
OpenAdapt. In version 2.2.0, the server has no tool that approves a save.

## Write an Agent Skill

```bash
openadapt agent emit-skill bundle --out ~/.claude/skills
```

This writes a `SKILL.md` for one workflow: what it does, its inputs, how to
call it, and what to do after each outcome. It holds no recorded values or
secrets. `--include-bundle` also copies the bundle, which can hold recorded
values, so keep that copy as private as the recording.

## Security

- The server talks only over stdio and has no sign-in. Don't expose it over
  a network.
- By default the agent gets cards, fixed sentences, ids, and counts.
  `--allow-protected-export` sends recorded values, reports, and output to
  the agent; use it only where the agent's model may see that data.
- Run folders hold the values entered and screenshots of each step. Treat
  them as protected data.
- Model grounding is off unless the deployment file or
  `--allow-model-grounding` turns it on. When it's on, screenshots can leave
  the computer.

## Agents in ChatGPT or Claude on the web

A web chat can't start a server on your computer. To record from one, start
at [openadapt.ai/start](https://openadapt.ai/start). When it gives you a
runner link, run `openadapt agent authoring connect '<runner link>'` on the
computer that has the app. It polls openadapt.ai over outgoing HTTPS and asks
you in the terminal before a chat account may drive it.
