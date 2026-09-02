---
description: >-
  Install OpenAdapt on this computer with Desktop or pip. Show the task
  once; it becomes a program your agent can run. Tutorial is optional.
---

# Get started

You want an agent to do a job on this computer. Keep that job here.

You show the clicks once. OpenAdapt turns that into a program on this
computer, and later an agent runs it and checks the work landed. Healthy
repeats don't send your data to a model.

OpenAdapt is a compiler. The chat is the IDE, and credentials stay on this
computer. The core is free forever under MIT.

## Install

Python 3.10 through 3.12 for pip. Desktop and the CLI compile the same
program.

### Desktop

Get the installer for this machine from
[openadapt.ai/download](https://openadapt.ai/download). You can also start
from [openadapt.ai/start](https://openadapt.ai/start). Open the app. Grant
Screen Recording and Accessibility if asked.

First-run permissions and checksums are in
[Install Desktop](../desktop/install.md).

### CLI

```bash
python -m pip install --upgrade openadapt
```

If you don't want to touch the Python you already have, use the isolated
installer:

```bash
curl -fsSL https://openadapt.ai/install.sh | sh
```

Either command leaves `openadapt` on PATH.

## After install

If you came from a job page (`/j/{id}`), go back to that tab. It's already
there. If a local coding agent is on this machine, it can call `openadapt`
on PATH.

Sign in on this computer, in the real app. Not in the chat.

### Optional tutorial

`openadapt flow tutorial` records a bundled tutorial and compiles it, then
runs it locally. A healthy run writes a VERIFIED receipt. To see a halt
when the on-screen banner disagrees with the record, run
`openadapt quickstart --break-it`. The run stops because the independent
read failed, and the store stays as it was. Add `--headed` if you want to
watch the browser.

Skip it if you already have a real task.

The tutorial writes the recording, the compiled bundle, and the run
receipt under its output directory (default
`tutorials/tutorial-<UTC timestamp>`):

- `<out>/recording/`
- `<out>/bundle/`
- `<out>/run/REPORT.md`
- `<out>/run/receipt.json`

```bash
less <out>/run/REPORT.md
openadapt flow visualize <out>/bundle --out graph.html
openadapt flow lint <out>/bundle
```

## Local coding agents

Claude Code and Cursor on this machine can use the local MCP command
below. ChatGPT.com can't talk to localhost, so it can't use this
command. For a hosted chat, stay on the job tab and put OpenAdapt on
this computer. Don't send that chat your passwords.

```bash
claude mcp add openadapt -- \
  uvx --from 'openadapt-agent[tutorial]' openadapt-agent \
  serve --allow-run
```

`--allow-run` is an explicit opt-in. Halt, refused, timeout, and error come
back as those outcomes. Never summarize halt as success.

The machine contract is in [agents.txt](../agents.txt).

## Next

Author one real read-only task on your own app in
[Author a workflow](first-workflow.md). Start with a lookup that doesn't
change business data.

More Desktop setup is in [Install Desktop](../desktop/install.md).
