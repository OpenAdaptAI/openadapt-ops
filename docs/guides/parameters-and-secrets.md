# Parameters and secrets

A workflow that runs many times usually varies a value each run: a different
note, a different reference number. Some of those values are secrets that must
never touch disk. OpenAdapt handles both, and treats them differently on
purpose.

## Parameters

Mark a typed field as a parameter at record time. Its demonstrated value becomes
the default, overridable at replay:

```bash
openadapt flow record --url https://your.app --out rec --param note
openadapt flow compile rec --out bundle --name my-task
openadapt flow replay  bundle --url https://your.app --param note="Follow-up in 2 weeks"
```

Repeat `--param` for multiple values.

### Parameterizing typed text works end to end

Parameterizing the *typed text* of a step is fully supported and verified: a
distinct value each run, read back and confirmed by OCR of the resulting screen.
Making a value a parameter also strips it from every compiled assertion, by
design, because it varies per run.

### Parameterizing *which record* is stricter

Parameterizing a value that changes **what appears on screen** (which patient to
open) is different. Anchors recorded on one entity cannot match another, so
resolution degrades to geometry, and that click is [identity gated](../concepts/identity-gate.md):
the run's value is substituted into the recorded band and the whole substituted
band must match the resolved row. A wrong row halts, and a row that merely
*mentions* the value halts too.

!!! note "The disclosed cost"
    When the entity's own row text varies with the entity (a search result that
    carries the surname the recorded band baked in), the substituted band can
    fail to match even the correct row, and the run halts. Clicking by position
    is what caused wrong-record writes, so OpenAdapt takes the halt. Re-anchoring
    verifies cleanly only when the band's non-parameter text is stable across
    entities.

## Secrets

A secret is a parameter whose value is **never persisted**. A `password` input,
or any field you mark `--secret`, is treated as secret: its value is never
written to the recording, the events log, the compiled bundle, or the saved
frames (its on-screen region is redacted). At replay it is injected from the
environment, and a missing one fails fast.

```bash
openadapt flow record --url https://your.app --out rec --secret password
export OPENADAPT_FLOW_SECRET_PASSWORD='...'          # supplied at replay time
openadapt flow replay  bundle --url https://your.app
```

The environment variable name is `OPENADAPT_FLOW_SECRET_<FIELD>` with the field
name upper-cased. `input[type=password]` is always treated as secret, whether or
not you pass `--secret`.

## Parameter versus secret at a glance

| | Parameter | Secret |
|---|---|---|
| Demonstrated value stored | Yes, as the default | No, never |
| Overridable at replay | `--param key=value` | Injected from env |
| Stripped from assertions | Yes | Yes |
| Region redacted in frames | No | Yes |
| Missing at replay | Uses the default | Fails fast |

## Leakage is linted at compile time

Recorded parameter values do not leak into geometry landmarks, and a
compile-time check fails the build if a demonstrated parameter value appears in
any text postcondition or landmark OCR text. The check reads text evidence only,
so a later region-stable template can still embed a value's rendered pixels; that
failure is in the safe direction (the region will not match under a different
run value and the run halts safely), but it is not linted. See the
[configuration reference](../reference/configuration.md) for the full list of
secret and parameter environment variables.
