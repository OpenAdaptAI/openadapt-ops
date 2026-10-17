---
description: >-
  The one list of terms the OpenAdapt docs use, each in plain words, with the
  name the engine uses in files and commands.
---

# Glossary

<span id="in-plain-words"></span>Every page in these docs uses the terms below with these meanings. Where the
engine uses a different name in its files or commands, that name follows in
parentheses.

<span id="admission"></span>**Admission**
:   A signed record that one exact version of a program passed qualification
    and may run under the Standard or Regulated profile. `qualify --certify`
    signs a local admission with a test key, which production refuses.

<span id="agent-skill"></span>**Agent Skill**
:   A `SKILL.md` file that tells an AI assistant what one workflow does, its
    inputs, and what to do after each outcome. Written by `emit-skill`. It
    holds no recorded values.

<span id="approval-mode"></span>**Approval mode**
:   Whether a run waits for an answer before each save: `each_item` (wait
    for each save), `problems_only` (only problems go to a person; not yet
    available), or `not_gated` (no pause, recorded in the report).

<span id="bundle"></span>**Bundle**
:   The folder a compile writes: the program (`workflow.json`, or
    `workflow.json.enc` when encrypted), screen crops it uses to find
    targets, and a manifest with a digest of every file. The docs also call
    it the program. `openadapt flow seal` writes an encrypted copy.

<span id="canary"></span>**Canary**
:   The first few runs of a repaired program after it's activated. Any wrong
    success or failed check switches back to the previous version.

<span id="certify"></span>**Certify**
:   Check a program against a policy. A property of the program alone.

<span id="compile"></span>**Compile**
:   Turn one recording into a program. `induce` does the same from two or
    more recordings.

<span id="composition"></span>**Composition**
:   A parent program that runs several programs in order, each on its own
    surface, and passes confirmed values between them (`compose`).

<span id="demonstration"></span>**Demonstration**
:   One performance of the task in the real application, by a person or an
    agent, while OpenAdapt records it. A program is learned from one or more
    demonstrations.

<span id="deployment-file"></span>**Deployment file**
:   A YAML file (`deploy.yaml`) that says where the app is, where its records
    can be read, which profile and policy apply, and whether model help is
    allowed. It holds environment variable names, never secret values.

<span id="durable-run"></span>**Durable run**
:   A run that saves a checkpoint after each confirmed step and pauses when
    it stops, so it can resume without repeating a confirmed save
    (`--durable`, `resume`).

<span id="execute"></span>**Execute**
:   OpenAdapt's commercial API for submitting runs to a customer-controlled
    runner and getting back signed results.

<span id="halt"></span>**Halt**
:   A designed stop: the run refused to act because a check failed. The
    report says which check and why.

<span id="model-grounding"></span>**Model grounding**
:   Asking an AI vision model where a target is when the recorded control
    can't be found. Off by default. When on, screenshots can leave the
    computer unless the model runs on your network.

<span id="policy"></span><span id="certification-policy"></span>**Policy**
:   A set of rules a program must meet to run, such as "every save has a
    right-record check". Built in: `clinical-write` and `permissive`.

<span id="profile"></span>**Profile**
:   The set of requirements a run is held to: `demo`, `standard`, or
    `regulated`. See [Run a workflow](../how-to/run.md#2-choose-a-profile).

<span id="qualify"></span>**Qualify**
:   Run a program against the normal case and five faults in a test copy of
    the environment where it will run, and check it saves correctly on the
    normal case and stops on every fault. A property of the program in one
    environment.

<span id="receipt"></span>**Receipt**
:   A small JSON summary of a `VERIFIED` run that's safe to share. It holds
    counts and digests, not record values (`receipt.json`). Only `VERIFIED`
    runs get one.

<span id="reconciliation"></span>**Reconciliation**
:   A person checking the record after a run ended
    `RECONCILIATION_REQUIRED`, because a save may or may not have landed.

**Record check** (effect check)
:   A read of the saved record after a save, through a different path from
    the screen that did the work, such as the app's API, its database, or a
    separate signed-in session (`effects`).

<span id="recording"></span>**Recording**
:   The folder `record` writes: the steps, screenshots, and what each step
    acted on. Password fields and fields marked secret are never saved.

<span id="repair-candidate"></span>**Repair candidate**
:   A changed program proposed after a halt. It must pass review, a replay
    campaign, a fault campaign, approval by a person, and a canary before it
    becomes active.

**Right-record check** (identity check)
:   A check before an action that the screen shows the record the inputs
    name, for example the right patient's banner.

<span id="run-report"></span>**Run report**
:   `REPORT.md` and `report.json` in the run directory: every step, how its
    target was found, every check and its result, and the number of model
    calls.

<span id="seal"></span>**Seal**
:   OpenAdapt Cloud's signature on the receipt of a run that Cloud Execute
    tracked. Anyone can check it offline with `openadapt seal verify`.

<span id="surface"></span>**Surface**
:   Where a program acts: a browser tab, a Windows, macOS, or Linux app
    window, or an RDP or Citrix client window. A program belongs to one
    surface.

<span id="system-of-record"></span>**System of record**
:   The application's own store of the data, such as its database or API,
    as opposed to what its screen shows.

<span id="teach"></span>**Teach**
:   Record only the steps that fix a halt and add them to the program as a
    guarded branch for that situation (`teach`, `teach-branch`).

<span id="worklist"></span>**Worklist**
:   A CSV or JSON list where each row is one run's inputs (`for-each`,
    `run --worklist`).

The outcomes a run can end with, such as `VERIFIED` and
`RECONCILIATION_REQUIRED`, are listed in [Run outcomes](outcomes.md).
