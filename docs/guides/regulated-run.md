# Run fail-closed for regulated work

For regulated deployments — clinical, financial, anything where a wrong write has
real consequences — the point of `run` is not that it succeeds, but that it
**refuses to proceed on anything it cannot verify**. This guide is the checklist
for a fail-closed production run: every safety gate on, nothing trusted by
default, and a run report that proves it.

## The fail-closed posture

Assemble one [`deployment.yaml`](../reference/deployment-config.md) that turns
every gate on:

```yaml
name: clinic-triage
backend:
  url: https://emr.internal.example.org
effects:                     # verify writes against the system of record
  kind: fhir
  base_url: https://emr.internal.example.org/apis/default/fhir
  resource_type: Observation
  access_token: "${OPENEMR_FHIR_TOKEN}"
runtime:
  durable: true              # checkpoint each verified step; pause on halt
  allow_model_grounding: false   # zero outbound calls; no screenshots leave the box
policy:
  policy: clinical-write     # refuse an unsafe bundle at certify time
```

Then **certify before you run**, against the policy the bundle will run under:

```bash
openadapt flow certify bundle --config deployment.yaml   # exits 2 if unsafe
openadapt flow run     bundle --config deployment.yaml
```

## What "fail-closed" gets you, gate by gate

Each of these **halts** rather than proceeding when it cannot get a positive
answer — the opposite of an agent that presses on with its best guess:

- **Unverifiable write → halt.** With `effects` configured, every consequential
  write is [verified against the real record](../concepts/effect-verification.md),
  not the screen. `CONFIRMED` proceeds; `REFUTED` or `INDETERMINATE` halts. A step
  that *declares* effects while no verifier is configured is a configuration error
  and halts — an unverifiable write is never silently accepted.
- **On-screen read-back is not verification.** Reading a value back from the same
  UI you just typed into proves the pixels rendered, not that the underlying
  record changed. On desktop and [Citrix](desktop-and-citrix.md) especially,
  there is no independent on-host observation channel, so the system-of-record
  effect verifier is the *only* authoritative check. Configure it.
- **Low-confidence match on an irreversible step → refuse.** Write-shaped clicks
  (save, submit, create, delete) are auto-classified irreversible and refuse to
  act on a low-confidence target match.
- **Unarmed identity is disclosed, not hidden.** The [identity
  gate](../concepts/identity-gate.md) is armed on a *subset* of click steps — the
  ones with a stable discriminating band. The run report states plainly how many
  click steps were armed ("4 of 12 click steps identity-armed") and lists each
  unarmed step with its reason. Use [`lint`](../reference/cli.md#lint) and
  [`certify`](../reference/cli.md#certify) to require coverage before deploy.
- **Halt becomes a durable pause.** With `runtime.durable: true`, a halt writes a
  pending escalation and stops at the last verified checkpoint. An operator
  [`approve`](../reference/cli.md#approve)s it and [`resume`](../reference/cli.md#resume)s
  from the checkpoint — a confirmed write is never re-performed. Require the
  approval explicitly:

  ```bash
  openadapt flow approve runs/replay-... 
  openadapt flow resume  runs/replay-... --require-approval
  ```

## Keep egress closed

`runtime.allow_model_grounding` defaults to **false**, so the run makes **zero
outbound model calls** — the deterministic ladder (template / OCR / geometry)
resolves targets locally. Left off, screenshots never leave the box, and the run
report says so explicitly. If you deliberately enable the model tiers, point them
at an [on-prem VLM appliance](../concepts/vlm-appliance.md) in your own
environment; the report then flags that screenshots could have left the box for
that run.

## PHI in the artifacts

- **Scrub the shareable surfaces**: set `OPENADAPT_FLOW_SCRUB=on` (needs the
  `privacy` extra) to PHI-scrub `REPORT.md` and console logs, fail-closed.
- **The bundle and `report.json` keep literal identifiers on purpose** — they are
  the identity check and the audit trail — protected by a documented boundary,
  not redaction. See [Deploy on-prem](deploy-on-prem.md).

## The compliance gate

!!! danger "No lane carries real PHI until the encryption gate closes"
    The 2026 HIPAA Security Rule makes encryption of ePHI **mandatory both at rest
    and in transit** (no longer merely "addressable"). This applies to the
    **self-hosted and BYOC lanes too**, not only hosted ones — local plaintext
    PHI at rest still violates the rule. Before a deployment carries real PHI,
    confirm with the team that: (1) at-rest bundle/report encryption is enabled,
    (2) every PHI-bearing wire (the in-session agent channels, any remote-display
    stream) is TLS on non-loopback hops, (3) halt descriptors crossing to any
    control plane are PHI-free, and (4) a **signed BAA and a current HIPAA risk
    analysis** are in place. The risk analysis is the single highest-leverage
    compliance artifact.

Some of this remediation is in flight. Treat the honest, current status as the
gate — ask for it when scoping a PHI deployment rather than assuming it is closed.

## Next

- [Run a deployment](run-a-deployment.md) — the full walkthrough of `run`.
- [Choose a deployment](deployment-models.md) — where the data lives.
- [Deploy on-prem](deploy-on-prem.md) — air-gapped data handling.
