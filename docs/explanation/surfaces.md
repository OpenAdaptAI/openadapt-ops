---
description: >-
  The six surfaces OpenAdapt drives, how a step finds its target on each, and
  the evidence behind each one today.
---

# Surfaces

A surface is where a program acts. OpenAdapt drives six: a browser
(`web`), native apps on `windows`, `macos`, and `linux`, and remote sessions
over `rdp` and `citrix`. One runtime, with the same checks, drives all six.

## Vision first, not vision only

OpenAdapt can work from pixels alone: a screenshot in, clicks and keys out.
That's what lets it drive an RDP or Citrix session, where the local computer
sees only an image of the remote screen. It isn't limited to pixels. Where a
surface exposes structure, OpenAdapt uses it first.

Each compiled step stores several ways to find its target. At run time it
tries them in order:

1. **Structure**: the page's DOM in a browser, UI Automation on Windows, the
   accessibility tree on macOS, AT-SPI on Linux.
2. **Image matching** near where the target was, then anywhere on screen.
3. **Text** found by OCR.
4. **Position** relative to nearby landmarks.
5. **A vision model**, only when explicitly turned on. Its answer is a
   proposal and still has to pass the right-record check.

A healthy step usually resolves on the first rung it can use. In a benchmark
of 21 targets on a synthetic screen under rendering changes, the structural
rung acted correctly on all 21, and image matching alone on 6.

Structure makes the right-record check stronger, because it reads an exact
element instead of matching pixels. RDP and Citrix have no structure on the
local side, so every rung there works from the image, and confusable
characters in an identifier (such as `O` and `0`) cause more stops.

## One program per surface

A recording is stamped with its surface, and the compiled program keeps it.
Running a program on a different surface is refused unless you pass
`--allow-surface-override`, which the run report records. Under the Standard
and Regulated profiles, `record` and `run` need an explicit `--backend` or
`backend.kind`. To span applications, compose one program per surface; see
[Build a program from several demonstrations](../how-to/combine-demonstrations.md#chain-programs-across-applications).

## Evidence per surface

Each row is limited to what was tested. A given application on a given
surface still needs its own qualification.

| Surface | Tested how | Result |
|---|---|---|
| Browser | Required CI on every build, plus field runs against OpenEMR | Full record, compile, run, and check cycle |
| macOS | Counted trials | 3 of 3 TextEdit saves confirmed by exact file contents; refused an ambiguous two-window target |
| Windows | Counted trials | 3 of 3 WinForms saves confirmed in SQLite; 3 of 3 refusals each for stale and ambiguous targets |
| Linux (X11) | Required CI and counted trials | A GTK3 app: 3 confirmed saves, 3 ambiguous-target refusals, 3 stale-target refusals |
| RDP | Counted trials | 3 of 3 remote-input trials into Windows 11 over a real network, confirmed by a separate file check |
| Citrix | Required CI and a stand-in with no DOM | 3 confirmed runs and 3 stops under drift on a stand-in; no run over real Citrix ICA/HDX is on record yet |

An agent can record on native Windows, RDP, and Citrix as well as in a
browser. That support is on the `main` branch and not yet in a release, and its
tests use a mock Windows server and stand-in client windows.
