# External Citrix zero-install brief

For workflows that live behind Citrix Workspace, VDI, or published
applications, where installing software inside the session is impossible or
prohibited.

## The problem

The highest-value repetitive workflows in healthcare, banking, and insurance
often run inside a Citrix session: the EMR or core system is published from an
environment the operating team cannot modify. Conventional automation fails
here twice over: there is no DOM, no accessibility tree, and no API from the
outside, and the hosting policy forbids installing an agent inside the
session.

## The approach: external black-box execution

OpenAdapt drives the Citrix client window from outside the session, through
exactly what a human uses: rendered pixels, keyboard, and mouse. **Zero
install inside the remote session.** No agent, no driver, no browser
extension, no change request to the Citrix operator.

Governance is not relaxed to make that work; it is the same contract as every
other substrate:

- The dedicated Citrix backend binds the exact Workspace client window,
  optionally an exact title, and requires a readiness marker before a governed
  run proceeds.
- Consequential input reacquires the exact window, focus, geometry, readiness,
  fresh pixels, resolved target, and record identity, then a one-shot input
  lease refuses delivery if **anything** changed between resolution and the
  first input edge.
- Identity checks run on the pixel tier; ambiguity deliberately over-halts
  rather than guessing. A collapsible or unreadable identifier halts the run.
- Business effects are verified out of band where a read path exists (API,
  database, report export, or a read-only second session). Screen-only
  confirmation is labeled as such, and high-risk workflows may not qualify on
  it alone.
- Halts are durable: the run pauses for a human with the violated expectation
  named in the report.

## Honest status

Two claims, kept separate:

1. **Qualified today: the backend contract over a deterministic no-DOM
   stand-in.** The released `--backend citrix` path passed its accepted
   qualification batch: 3/3 healthy effects and 3/3 severe-drift safe halts,
   with zero model calls, zero silent incorrect successes, zero false
   completions, zero healthy over-halts, and zero drift writes. The immutable
   report records `code_readiness_accepted: true` and, explicitly,
   `ica_hdx_accepted: false`
   ([evidence appendix](../get-started/what-works-today.md)).
2. **Pending: counted acceptance in a real ICA/HDX session.** The exact
   client, codec, latency, DPI, lock and readiness behavior, input handling,
   identity, and effect matrix of a real Citrix environment is a
   per-deployment qualification boundary. That acceptance runs in **your**
   Citrix environment as part of a
   [Qualification Sprint](qualification-sprint.md); stand-ins remain
   development fixtures, not Citrix evidence.

We state this plainly because the alternative, generalizing from a stand-in to
your production Citrix farm, is exactly the kind of claim the qualification
process exists to prevent.

## What a Citrix qualification needs from you

In addition to the standard [prerequisite checklist](scope-checklist.md):

- A reachable Citrix session (Workspace or HTML5) with client, codec,
  resolution, and DPI representative of production.
- Permission to drive that session with automated input.
- A verification read path for the business effect, or an explicit decision on
  read-only-session verification and its risk implications.

## Commercial shape

Citrix scope is at the upper end of the sprint ladder: **typically $25,000 to
$40,000** for qualification of one workflow, reflecting per-environment
fixture, identity, and verification work. The
[deployment boundary](deployment-boundaries.md) is customer-controlled: the
runner sits on your side, the session stays in its own boundary, and nothing
is installed in it.
