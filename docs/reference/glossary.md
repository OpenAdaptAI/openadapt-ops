---
description: >-
  The one list of terms the OpenAdapt docs use, each in plain words, with the
  name the engine uses in files and commands.
---

# Glossary

Every page in these docs uses the terms below with these meanings. Where the
engine uses a different name in its files or commands, that name follows in
parentheses.

**Admission**
:   A signed record that one exact version of a program passed qualification
    and may run under the Standard or Regulated profile. `qualify --certify`
    signs a local admission with a test key, which production refuses.

**Agent Skill**
:   A `SKILL.md` file that tells an AI assistant what one workflow does, its
    inputs, and what to do after each outcome. Written by `emit-skill`. It
    holds no recorded values.

**Approval mode**
:   Whether a run waits for an answer before each save: `each_item` (wait
    for each save), `problems_only` (only problems go to a person; not yet
    available), or `not_gated` (no pause, recorded in the report).

**Bundle**
:   The folder a compile writes: the program (`workflow.json`, or
    `workflow.json.enc` when encrypted), screen crops it uses to find
    targets, and a manifest with a digest of every file. The docs also call
    it the program. `openadapt flow seal` writes an encrypted copy.

**Canary**
:   The first few runs of a repaired program after it's activated. Any wrong
    success or failed check switches back to the previous version.

**Certify**
:   Check a program against a policy. A property of the program alone.

**Compile**
:   Turn one recording into a program. `induce` does the same from two or
    more recordings.

**Composition**
:   A parent program that runs several programs in order, each on its own
    surface, and passes confirmed values between them (`compose`).

**Demonstration**
:   One performance of the task in the real application, by a person or an
    agent, while OpenAdapt records it. A program is learned from one or more
    demonstrations.

**Deployment file**
:   A YAML file (`deploy.yaml`) that says where the app is, where its records
    can be read, which profile and policy apply, and whether model help is
    allowed. It holds environment variable names, never secret values.

**Durable run**
:   A run that saves a checkpoint after each confirmed step and pauses when
    it stops, so it can resume without repeating a confirmed save
    (`--durable`, `resume`).

**Execute**
:   OpenAdapt's commercial API for submitting runs to a customer-controlled
    runner and getting back signed results.

**Halt**
:   A designed stop: the run refused to act because a check failed. The
    report says which check and why.

**Model grounding**
:   Asking an AI vision model where a target is when the recorded control
    can't be found. Off by default. When on, screenshots can leave the
    computer unless the model runs on your network.

**Policy**
:   A set of rules a program must meet to run, such as "every save has a
    right-record check". Built in: `clinical-write` and `permissive`.

**Profile**
:   The set of requirements a run is held to: `demo`, `standard`, or
    `regulated`. See [Run a workflow](../how-to/run.md#2-choose-a-profile).

**Qualify**
:   Run a program against the normal case and five faults in a test copy of
    the environment where it will run, and check it saves correctly on the
    normal case and stops on every fault. A property of the program in one
    environment.

**Receipt**
:   A small JSON summary of a `VERIFIED` run that's safe to share. It holds
    counts and digests, not record values (`receipt.json`). Only `VERIFIED`
    runs get one.

**Reconciliation**
:   A person checking the record after a run ended
    `RECONCILIATION_REQUIRED`, because a save may or may not have landed.

**Record check** (effect check)
:   A read of the saved record after a save, through a different path from
    the screen that did the work, such as the app's API, its database, or a
    separate signed-in session (`effects`).

**Recording**
:   The folder `record` writes: the steps, screenshots, and what each step
    acted on. Password fields and fields marked secret are never saved.

**Repair candidate**
:   A changed program proposed after a halt. It must pass review, a replay
    campaign, a fault campaign, approval by a person, and a canary before it
    becomes active.

**Right-record check** (identity check)
:   A check before an action that the screen shows the record the inputs
    name, for example the right patient's banner.

**Run report**
:   `REPORT.md` and `report.json` in the run directory: every step, how its
    target was found, every check and its result, and the number of model
    calls.

**Seal**
:   OpenAdapt Cloud's signature on the receipt of a run that Cloud Execute
    tracked. Anyone can check it offline with `openadapt seal verify`.

**Surface**
:   Where a program acts: a browser tab, a Windows, macOS, or Linux app
    window, or an RDP or Citrix client window. A program belongs to one
    surface.

**System of record**
:   The application's own store of the data, such as its database or API,
    as opposed to what its screen shows.

**Teach**
:   Record only the steps that fix a halt and add them to the program as a
    guarded branch for that situation (`teach`, `teach-branch`).

**Worklist**
:   A CSV or JSON list where each row is one run's inputs (`for-each`,
    `run --worklist`).

The outcomes a run can end with, such as `VERIFIED` and
`RECONCILIATION_REQUIRED`, are listed in [Run outcomes](outcomes.md).
