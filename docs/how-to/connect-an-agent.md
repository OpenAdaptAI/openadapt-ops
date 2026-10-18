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

The sandbox has one workflow, `add_triage_note`, on MockMed, a synthetic
clinic app. It needs no account. In Claude Code, register the server:

```bash
claude mcp add --scope user openadapt -- uvx --python 3.12 openadapt-agent serve
```

This only registers the server. It prints `Added stdio MCP server openadapt
... to user config` and nothing else. Claude Code starts the server the next
time you run `claude`. `--scope user` makes it available in every folder;
without it, Claude Code saves it for the current folder only.

Then:

1. Run `claude`.
2. Optional: type `/mcp` to check that `openadapt` is connected.
3. Ask: "Use the OpenAdapt sandbox to run add_triage_note with the note
   'Synthetic: recheck blood pressure in 2 weeks' and request id demo-0001."

The agent calls `list_workflows`, then `run_workflow`. The result includes:

```json
{
  "outcome": "done",
  "label": "Done and checked",
  "safe_to_retry": false,
  "next_step": "none",
  "proof": "simulated",
  "model_calls": 0,
  "what_happened": "Simulated sandbox result (no app was opened): Saved the change and read the record back to confirm it."
}
```

Add `sandbox_case` to the inputs to see each outcome. The tool's input
schema lists every case, among them `normal`, `duplicate_record`,
`timeout_after_save`, and `app_offline`. Use a new request id for each try. A used id returns the
earlier result, or `did_not_run` with `request_id_conflict` if the inputs
changed.

This sandbox simulates each run. To have the engine drive MockMed in a
hidden browser, install the `tutorial` extra instead, then restart `claude`:

```bash
claude mcp remove openadapt
claude mcp add --scope user openadapt -- uvx --python 3.12 --from 'openadapt-agent[tutorial]' openadapt-agent serve
```

The first run records the workflow once, so it can return `running`; the
agent then calls `get_run`. A run that passes returns `done` with
`"proof": "local"`.

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
the reason `waiting_for_approval`.

In openadapt-agent 2.2.0, the server has no approval tools. A person answers
on the computer that runs OpenAdapt with `openadapt flow item-approval`; see
[Run a workflow](run.md#3-choose-how-saves-are-approved).

The `main` branch, not yet released, adds three tools:

- `get_approval_mode` reports the server's approval mode and whether the
  agent may answer.
- `list_approval_requests` lists a run's waiting saves, without values or
  screenshots.
- `answer_approval_request` approves or declines one of them.

The last two appear only when the operator starts the server with
`serve --delegate-approvals AGENT_ID`. Flow accepts the agent's answer only
where the run's approver policy allows an agent for that step, and records the
agent as the approver. By default, only a person may answer.

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

A web chat can't start a server on your computer. To record from one:

1. On [openadapt.ai](https://openadapt.ai/#job-box), type the job under
   **What job do you want to automate?** and click **Get a job page**.
2. On the job page, click **Connect this computer**. Its **Open OpenAdapt**
   link is the runner link (`openadapt://runner?pack=...&bind=oab_...`). It
   opens OpenAdapt Desktop if you have it. The link works once and expires
   after five minutes if nobody claims it.
3. Without Desktop, copy that link and run this on the computer that has the
   app:

    ```bash
    openadapt agent authoring connect '<runner link>'
    ```

It polls openadapt.ai over outgoing HTTPS and asks you in the terminal before
a chat account may drive it.
