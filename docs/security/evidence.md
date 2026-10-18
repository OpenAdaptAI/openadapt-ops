---
description: >-
  What OpenAdapt has been tested on, on which surface, and how, separated from
  what is still being proven.
---

# Evidence

This page lists what has been tested and how. The engineering limits are in
[Limits](../explanation/limits.md).

## Surfaces

| Surface | Kind of evidence | What was run |
|---|---|---|
| Web | Required CI and field runs | The full pipeline on every CI build, plus third-party OpenEMR runs |
| macOS desktop | Counted trials | 3 of 3 TextEdit runs with exact file contents checked; refused a case with two matching windows without changing either file |
| Windows desktop | Counted trials | 3 of 3 WinForms runs with the saved rows confirmed in SQLite; 3 of 3 refusals for stale and ambiguous targets |
| Linux desktop | Required CI and counted trials | A real GTK3 workflow in CI: three confirmed saves, three refusals for an ambiguous target, three for a stale one |
| RDP | Counted trials | 3 of 3 runs over a real network into Windows 11 through the Aardwolf client, with the files checked through guest tools |
| Citrix | Required CI and a stand-in | 3 normal and 3 drift runs on a stand-in with no web page structure. The result records `ica_hdx_accepted=false`: no run over a real Citrix ICA/HDX session has been counted. |

A surface that isn't listed hasn't been tested. The detail and the retained
reports for each row:

**Windows.** The counted `20260717-candidate-56759c8-v2` WinForms run
completed 3/3 trials, an independent SQLite read confirmed 3/3 saves, and
stale-target and ambiguous-target controls each refused 3/3, with 0 silent
incorrect successes, 0 over-halts, and 0 model calls. The report also keeps
earlier diagnostic runs that were rejected; they aren't counted. It covers
the named task on a Windows 11 ARM virtual machine snapshot.
[Report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/windows_uia/results.json), first retained at Flow commit `defafbae758a75c8e149d9693f2cffe1f2264b8c`.

**macOS.** On one macOS 15.7.3 arm64 host, candidate `b1b61a5` completed 3/3
TextEdit trials with the exact file bytes checked, and refused a two-window
ambiguity without changing either file. The original report still reads
`status: failed`, because cleanup warnings at close were counted as a batch
failure. A separate review keeps that result, checks that the test's
processes and temporary folder were gone, and accepts the save and refusal
evidence.
[Review](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/macos_native/textedit_counted_3plus1_b1b61a5_20260717.adjudication.json), first retained at Flow commit `ca1b522cad215875f7471782283f8f8bb8e6c998`.

**Linux.** The required CI job
[`linux-atspi-x11`](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/.github/workflows/ci.yml)
at Flow commit `3de5fc67acf3024a621f812c5a6ed9be07fac335` (Actions run
30059807758, job 89378981573) ran a fresh GTK3
process per trial on Ubuntu 24.04 with X11: 3/3 exact file saves, 3/3
ambiguous-target refusals, and 3/3 stale-target refusals, with no model
calls. It covers that test app and CI image, and doesn't establish Wayland
or arbitrary third-party application support.

**RDP.** Aardwolf 0.2.14 into a Parallels Windows 11 virtual machine
completed 3/3 file saves through the Windows Run dialog, read back through
guest tools
([report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/rdp/results_82a658a_20260718.sanitized.json)).
Separately, a real FreeRDP round trip recorded, compiled, and replayed a
synthetic note task: 3/3 healthy saves and 3/3 drift halts, with no model
calls
([report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/rdp_ladder/results.json), first retained at Flow commit
`affedc5f1f0de533a0744deaa8e30a203c91c6b3`).
That second run is a synthetic Linux app, not Aardwolf, a Windows app, or
Citrix ICA/HDX.

**Citrix.** The `--backend citrix` path binds the exact Workspace or Viewer
window and requires on-screen readiness text before a governed run. On a
stand-in with no web page structure it completed 3/3 healthy saves and 3/3
severe-drift halts with no model calls. The retained result records
`code_readiness_accepted: true` and `ica_hdx_accepted: false`: it is not a
counted real ICA/HDX batch.
[Report](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/benchmark/citrix_workspace/results.json), first retained at Flow commit
`f6faac5b900b78cbda5980de0e983a9f987285ac`.

## Fault cases

Certification and qualification run six cases, three times each, against the
exact bundle: one normal run and five where something breaks, such as a
second copy of the save button or a missing record check. Each fault case
passes only if the run stops before it can report a false success. A full
qualification of the MockMed sample on 17 October 2026 passed all 18 trials
in 71.2 seconds. See
[Certify and qualify a workflow](../how-to/certify-and-qualify.md).

## Production workflow admissions

The public list of workflow admissions is
[production-workflow-admissions.json](https://docs.openadapt.ai/production-workflow-admissions.json).
As of 14 October 2026, every entry is a synthetic workflow for remote
testing. None is a customer workflow.

## The managed runner

The managed browser runner installs a pinned engine release, not the newest
one. As of 2026-10-17, the managed runner's runtime manifest pins Flow 1.34.0
at release commit `30fc60e55778a0e0f92b9776117cafcfe2512249`, wheel SHA-256
`56d32818989cb3a92830080ead39e10b08718c55e00988117f22cbfeaac98854`, and sdist
SHA-256 `a941a70015fe91897e655bfc9bf83e6cf8fbcf8bd4e4c7206ffb133c505203f8`.
This is the configured pin in OpenAdapt Cloud's source, not a check of the
live service. Runs on your own computer use whatever version you install.
The managed runner is only for browser workflows; desktop, RDP, and Citrix
runs happen on a runner you control.

## Still being proven

- A real Citrix ICA/HDX session.
- Recording Windows, RDP, and Citrix through the agent's Windows agent
  server, tested so far against mock servers only.
- Production qualification of a customer workflow.

