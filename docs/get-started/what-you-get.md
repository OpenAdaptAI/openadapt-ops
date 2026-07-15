# What you get

Compiling a demonstration produces two things: a **bundle** you deploy and, on
every replay, a **run report** you can read and audit.

## The bundle

A workflow bundle is a self-contained directory. It is the deployable artifact:
version it, review it, ship it. It holds the compiled workflow program plus the
per-step evidence the replayer needs to re-find each target, along with the
policy metadata `lint` and `certify` read.

Because the bundle is the unit of deployment, everything about a workflow is
auditable before it ever runs: which steps write, which clicks are identity
armed, and which postconditions each step asserts. See
[The bundle format](../reference/bundle-format.md) for the full layout.

## The run report

Every replay writes a timestamped directory under `runs/` with an illustrated
`REPORT.md` (human-readable) and a `report.json` (machine-readable). Review or
sanitize either artifact before it crosses a boundary. The report is
the audit trail. For each step it records:

- **Resolution**: which rung of the ladder resolved the target (template, OCR,
  geometry, or a grounding model), and whether a heal was applied.
- **Identity**: whether the step was identity armed, and what the pre-click
  check verified or refused.
- **Postconditions**: which assertions passed, and any effect verified against
  the system of record.
- **Outcome**: success, or a halt naming the violated expectation.

The report also states, in plain language, how many of the workflow's click
steps were identity armed (for example "4 of 12 click steps identity-armed")
and lists any unarmed steps with the reason. Nothing about a run is hidden.

## Emit for other agents

A compiled bundle is not only a replay target. You can emit it as an
[Agent Skill](https://github.com/OpenAdaptAI/openadapt-flow) or a standalone MCP
server so other agents can invoke the workflow as a tool:

```bash
openadapt flow emit-skill bundle --out skills/
openadapt flow emit-mcp   bundle --out server.py
```

## Privacy of the artifacts

The `REPORT.md` and console logs can be processed by the PHI sanitizer on the
persist/log path (Presidio-backed, via the optional `privacy` extra). The
compiled bundle and `report.json` keep literal identifiers on purpose: they are
the identity check and the audit trail, and they are protected by a documented
boundary rather than by redaction. Detector misses remain possible, so review
sanitized output before egress. See
[Deploy on-prem](../guides/deploy-on-prem.md).
