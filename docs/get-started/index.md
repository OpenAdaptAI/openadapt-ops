---
description: >-
  Choose how to start with OpenAdapt: the command line, the Desktop app, or an
  AI agent connected over MCP. Each track installs the same engine. Read the
  operating-system permission notes first.
---

# Get started

OpenAdapt has three ways in. They install the same engine and produce the same
compiled programs, so you can start with one and add another later.

| Track | Start here if | What you run first |
|---|---|---|
| [Command line](cli.md) | You work in a terminal, or you want to see a verified run in a few minutes. | The bundled tutorial, on a synthetic app. |
| [Desktop app](../desktop/install.md) | You want a window to record, check, and run tasks, and to answer stopped runs. | A short test recording of your own screen. |
| [Connect an agent over MCP](agent-mcp.md) | You have an AI agent, such as Claude Code or Cursor, that should call OpenAdapt as a tool. | A sandbox server that returns each outcome on demand. |

Whichever track you pick, a person or an agent shows the task in the real app,
OpenAdapt compiles it into a program from one or more demonstrations, and a
person accepts that program before it does real work.

## Before you install: operating-system permissions

!!! warning "Grant permissions before your first recording"
    Recording and replaying a desktop app needs operating-system permissions.
    Without them, capture can return blank or black frames and input can go
    nowhere, with no error dialog.

    - **macOS:** the Desktop app needs Screen Recording, Accessibility, and
      Input Monitoring. To record a native app from the command line, grant
      Screen Recording and Accessibility to your terminal app. Quit and reopen
      the app after you grant Screen Recording. macOS applies it only after a
      restart.
    - **Windows:** ordinary windows need no prompt. If the target app runs as
      administrator, run OpenAdapt as administrator too, or that window is
      captured blank and ignores input.
    - **Browser workflows and the bundled tutorial** run in a browser that
      OpenAdapt starts, and need none of these permissions.

    The step-by-step settings are in
    [Desktop app: grant OS permissions](../desktop/install.md#2-grant-os-permissions).
    Blank capture and the Windows session-0 case are in
    [Troubleshooting](../guides/troubleshooting.md).

Sign in to your apps on this computer, in the real app. Don't type passwords
into a chat.

## If you came from a job link

A chat assistant such as ChatGPT can give you a job link of the form
`openadapt.ai/j/{id}`. That page holds the brief for your AI and the install
steps for this computer.

1. Install OpenAdapt with one of the tracks above.
2. Go back to the job tab. The job is still there.
3. If the job page gives you a runner link for a recording job (it contains
   `bind=oab_`), run this on the computer that has the app:

   ```bash
   openadapt-agent authoring connect '<runner link>'
   ```

   It asks you in the terminal before a chat account may drive this computer.
   It isn't the launcher's `openadapt connect`, which pairs a computer with
   OpenAdapt Cloud.

A chat in a web browser can't start a server on your computer, so it can't
use the local MCP command in [Connect an agent over MCP](agent-mcp.md).

## After the first run

- Optional: the bundled tutorial in the [command-line track](cli.md) shows a
  verified run, then a run that stops because the record disagrees with the
  screen.
- Author one real task on your own app in
  [Author a workflow](first-workflow.md). Start with a lookup that doesn't
  change business data.
- [What you get](what-you-get.md) explains the compiled bundle and the run
  report.
- [Packages](packages.md) lists what each OpenAdapt package does and how it
  installs.
