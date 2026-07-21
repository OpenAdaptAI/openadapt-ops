# Record your own app

The bundled demo shows the loop end to end, but the point is your app. This
guide records a real workflow, compiles it, and replays it. It uses the **web
substrate** throughout; a native Windows desktop or a pixel-only Citrix/RDP
session follows the same steps with a different
[backend](../reference/cli.md#backend) (`--backend windows` / `--backend rdp` and
its target flag) in place of `--url`.

## Record

On the web substrate, `record --url` opens a headed browser on your app and
watches what you do: clicks, typing, key presses, and scrolls. It writes the same
recording format `compile` consumes.

```bash
openadapt flow record --url https://your.app --out rec
```

Perform the workflow the way you want it replayed, then press ++ctrl+c++ or close
the window to finish.

!!! tip "Record headless for scripted or CI capture"
    Add `--headless` to run the browser without a window, for scripted recording
    in a pipeline.

## Compile and replay

```bash
openadapt flow compile rec --out bundle --name my-task
openadapt flow replay  bundle --url https://your.app
```

Pass `--url` to `replay` to run against your own app. Recorded parameter values
are the defaults; `--param key=value` overrides them.

## Check before you trust

Run `lint` to see the bundle's coverage gaps (unarmed clicks, vacuous
postconditions, under-classified writes) before relying on it:

```bash
openadapt flow lint bundle
```

For a bundle that will do consequential writes, gate it behind a policy with
[`certify`](policy-and-certification.md).

## Practical notes

- **Per-tenant re-recording.** A bundle recorded on one instance can halt at
  login on another instance of the same app version, because instance-specific
  screen state (a module menu, a dashboard) differs. Treat per-tenant
  re-recording as the working assumption.
- **No zoom or reflow.** Record and replay at the same browser zoom and display
  scale. A cosmetic 125% zoom currently zeroes replayability.
- **Demonstrate scrolls you need.** Closed-loop scrolling extends recorded
  scrolls; it does not invent them. If a target can be below the fold,
  demonstrate the scroll that reveals it.
- **One clear path.** The compiler treats your demonstration as intent: one with
  dead ends compiles those dead ends in.

## Handling variation

If the same workflow runs with different values each time (a different note, a
different record), make those values [parameters](parameters-and-secrets.md).
If it runs with real conditionals or loops, that is the
[workflow-program IR](../concepts/workflow-ir.md) and
[multi-trace induction](../concepts/multi-trace-induction.md): record the common
path first, then use `disambiguate` to surface the questions.
