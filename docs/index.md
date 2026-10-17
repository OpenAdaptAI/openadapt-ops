---
title: OpenAdapt documentation
description: >-
  OpenAdapt compiles one or more demonstrations of a task into a workflow
  program, tests it in the target environment, and runs it with a check
  before and after each save. A run that can't prove a save stops.
hide:
  - toc
---

# OpenAdapt

OpenAdapt turns a repetitive task in an application without a usable API
into a program that enters the data and then checks that it saved. A person
or an agent shows the task in the real application. OpenAdapt compiles one or
more demonstrations into a workflow program you can read, tests it in your
environment, and runs it with new inputs. A healthy run makes no AI model
calls. When a check fails, the run stops and asks a person instead of
guessing.

It drives web apps, Windows, macOS, and Linux apps, and apps reached over RDP
or Citrix: a CRM, a billing system, an insurance portal, or an electronic
health record. The tutorials use a synthetic clinic app as the example. The
engine is open source under the MIT license.

## Start here

<div class="grid cards" markdown>

-   __Run it in one command__

    ```bash
    uvx --python 3.12 openadapt quickstart --break-it
    ```

    Without uv, on Python 3.10 to 3.12: `pip install openadapt`, then
    `openadapt quickstart --break-it`. You don't need an account or an API
    key. [Quickstart tutorial](tutorials/quickstart.md)

-   __Give a workflow to your agent__

    ```bash
    claude mcp add openadapt -- uvx --python 3.12 openadapt-agent serve
    ```

    The MCP server gives an agent each compiled workflow as one tool call.
    This starts a sandbox that needs no account.
    [Connect an agent](how-to/connect-an-agent.md)

</div>

**Jump to:** [Command line](reference/cli.md) ·
[How the compiler works](explanation/how-it-works.md#a-program-not-a-model-in-a-loop) ·
[MCP server](how-to/connect-an-agent.md#serve-your-own-workflows) ·
[Run outcomes](reference/outcomes.md) ·
[Your first workflow](tutorials/first-workflow.md) ·
[Security & procurement](security/index.md)

## How a save is checked

![On the acting surface, the app screen OpenAdapt types into, a run checks that the right record is on screen, then enters and saves. It then reads the record back. A screen read-back uses the app's UI in a separate session and is not independent. An independent read uses the system of record through its API, database, or file export, never through the UI. If the read matches, the run ends VERIFIED with a run report and a receipt; OpenAdapt Cloud signs a Seal only after an independent read. If it doesn't match or can't tell, the run ends RECONCILIATION_REQUIRED and a person checks the record. If the right-record check fails, the run ends HALTED_BEFORE_EFFECT before saving and asks a person.](assets/diagrams/record-check.svg)

The screen that did the work can show "Saved" when nothing was stored, so it
never confirms a save on its own. [How a save is checked](explanation/verification.md)
explains which read-backs count for which result.

## From demonstration to production

```mermaid
flowchart LR
    S["Show the task<br/>(a person or an agent,<br/>one or more times)"] --> C["Compile<br/>a workflow program<br/>you can read"]
    C --> P["Certify<br/>policy and lint checks"]
    P --> Q["Qualify<br/>normal and fault cases<br/>in the target environment"]
    Q --> A["Admit<br/>this exact version"]
    A --> R["Run<br/>right-record check, action,<br/>record check at each save"]
    R --> V(["VERIFIED<br/>report, receipt, Seal"])
    R --> H(["Stopped<br/>HALTED_BEFORE_EFFECT"])
    R --> U(["Not sure it saved<br/>RECONCILIATION_REQUIRED"])
    H -.->|"a person or an agent<br/>shows the fix"| C
    U -.-> K["A person checks<br/>the record"]
```

[How OpenAdapt works](explanation/how-it-works.md) walks through each stage.
Terms are defined once, in the [glossary](reference/glossary.md). Which
releases are admitted for production is on
[Release integrity](security/release-integrity.md).

## When it fits

OpenAdapt fits a task when most of these are true:

- The team does it the same way many times a week.
- What to enter is already decided, by a person, a form, or an AI agent.
- The application has no practical API for the write.
- A wrong entry is costly.
- There is a second way to read the saved record, such as an API, a database,
  a report, or a read-only sign-in.

If the application already has an API for the task, call the API. The
[limits page](explanation/limits.md) lists what OpenAdapt doesn't do.

## What the packages are

On Python 3.10 to 3.12, `pip install openadapt` installs the `openadapt`
command, the engine (`openadapt-flow`), and the MCP server
(`openadapt-agent`). The [packages map](reference/packages.md) lists every
package and repository and which ones you need.
