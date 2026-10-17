---
description: >-
  Connect an AI agent to OpenAdapt over MCP. Start with the sandbox server,
  read the four outcomes, then serve your own compiled workflows.
---

# Connect an agent over MCP

Your agent decides what to enter. OpenAdapt enters it in the app, checks that
it saved, and returns one outcome. `openadapt-agent` is a local Model Context
Protocol (MCP) server that talks over stdio. It has no network listener, so
the agent, or a program acting for it, runs on the computer that runs the
workflow.

You need [uv](https://docs.astral.sh/uv/) and an MCP client that starts local
servers, such as Claude Code, Claude Desktop, or Cursor. The server needs
Python 3.10 to 3.12; `uvx --python 3.12` fetches 3.12 for it.

## 1. Add the sandbox server

The sandbox needs no account. It has one workflow, `add_triage_note`, which
adds a note to a referral in MockMed, a synthetic clinic app. It simulates
each run without opening the app, and every result says so.

=== "Claude Code"

    ```bash
    claude mcp add openadapt -- uvx --python 3.12 openadapt-agent serve
    ```

    Claude Code saves the server for the current folder. Start `claude` in
    the same folder.

=== "Claude Desktop, Cursor, and other clients"

    Add this to the client's `mcpServers` file:

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

Then ask the agent: "Use OpenAdapt to add the triage note 'Synthetic: recheck
blood pressure in 2 weeks' with request id demo-0001." It calls
`list_workflows`, then `run_workflow` with the workflow, the inputs, and your
`request_id`.

To have Flow drive MockMed in a hidden browser instead of simulating, use the
`tutorial` extra:

```bash
claude mcp add openadapt -- uvx --python 3.12 --from 'openadapt-agent[tutorial]' openadapt-agent serve
```

The first request waits while Flow prepares the workflow and, if needed,
downloads a browser of about 300 MB.

## 2. Read the outcome

Each request ends with one of four outcomes. While a run is still going, the
outcome is `running`, and the agent calls `get_run` with the `run_id`.

| `outcome` | Label | What the agent does next |
|---|---|---|
| `done` | Done and checked | Mark the request complete. Don't send it again. |
| `needs_review` | Stopped before saving | Don't start the same work again. A person at the computer decides; call `get_run` later. |
| `not_sure_if_saved` | Check the record | Never retry. A person checks the record in the app. |
| `did_not_run` | Didn't run | If `safe_to_retry` is true, fix the cause and resend the same request. |

Never summarize halt as success. Branch on `outcome` and `safe_to_retry`, not
on the text. Resending the same `request_id` with the same inputs returns the
earlier result and never enters the values twice.

## 3. Serve your own workflows

A bundle is a compiled workflow directory. Point the server at one bundle or a
directory of bundles:

| Command | What the agent gets |
|---|---|
| `openadapt-agent serve --bundles DIR` | Your workflows, listed but not runnable, plus read-only tools for past and stopped runs. |
| `openadapt-agent serve --mode production --bundles DIR --runs-dir RUNS` | Runs of your workflows. |
| `openadapt-agent serve --mode attended --bundles DIR --runs-dir RUNS` | Runs, plus decisions on stopped runs, which a person confirms in a form. |

`openadapt-agent serve --allow-run` is the older form of `--mode production`.

Flow refuses a bundle that hasn't passed the checks its profile requires, and
the agent gets `did_not_run` with `not_ready_to_run`. Under the Standard and
Regulated profiles, that means certification, an active admission for that
exact bundle version, and a record check that reads the saved record outside
the acting screen. See [Qualify a workflow](../guides/qualify-a-workflow.md).

## Record through the agent

`openadapt-agent serve --authoring` adds recording tools. With them, a person
or the agent shows the task in a web app, a native Windows app, or an RDP or
Citrix session. A person stays at the computer to sign in, and only that
person's answer in the client's confirmation form accepts the compiled bundle.
A task can be learned from one or more demonstrations.

[Recording on Windows, RDP and Citrix](../guides/record-windows-rdp-citrix.md)
covers the Windows agent server, its token, and the pixel path for remote
sessions.

## Chats in a web browser

ChatGPT and Claude in a web browser can't start a server on your computer, so
they can't use the commands above. Start at
[openadapt.ai/start](https://openadapt.ai/start), and see
[If you came from a job link](index.md#if-you-came-from-a-job-link). Don't send
that chat your passwords.

## More

- The full tool list, result fields, and security notes are in the
  [openadapt-agent README](https://github.com/OpenAdaptAI/openadapt-agent#readme).
- The machine-readable contract for agents is [agents.txt](../agents.txt).
- Every engine outcome is in [Run outcomes](../reference/run-outcomes.md).
