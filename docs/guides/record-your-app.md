# Record your own app

The bundled demo shows the loop end to end, but the point is your app. This
guide records a real workflow, compiles it, and replays it. It uses the **web
substrate** throughout; Windows, macOS, Linux, RDP, and Citrix follow the same
steps with a different [backend](../reference/cli.md#backend) and its exact
target flags in place of `--url`.

## Record

On the web substrate, `record --backend web --url` opens a headed browser on
your app and watches what you do: clicks, typing, key presses, and scrolls. It
writes the same recording format `compile` consumes.

```bash
openadapt flow record --backend web --url https://your.app --out rec
```

Perform the workflow the way you want it replayed, then press ++ctrl+c++ or close
the window to finish.

!!! tip "Record headless for scripted or CI capture"
    Add `--headless` to run the browser without a window, for scripted recording
    in a pipeline.

### Use an existing signed-in Chromium session

Flow can attach the same Playwright recorder to one existing local Chromium
tab. Use this mode when the browser profile has already completed sign-in, SSO,
or 2FA.

Start Chromium with a dedicated debugging profile. For example, on macOS:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  --user-data-dir="./.openadapt-chrome-profile"
```

Open the application in that browser. Then run:

```bash
openadapt flow record --backend web --url https://your.app \
  --browser-cdp-endpoint http://127.0.0.1:9222 --out rec
```

Flow selects the sole open tab on the `--url` origin. It refuses an ambiguous
selection. If the browser has two or more tabs on that origin, add the exact
current URL with `--browser-page-url`. Flow does not navigate or close the
attached browser.

The endpoint must be on localhost or a loopback IP address. The attached
screenshots use the tab's actual CSS viewport, so retained frames and DOM input
coordinates stay aligned on high-density displays. Password fields and fields
declared with `--secret` keep the same source-time exclusion and frame-redaction
contract as launch mode.

Keep the selected tab on the declared application origin. You can resize the
tab or move its window between monitors while no action is in progress. Flow
observes viewport and device-scale changes. It waits for a stable CSS-pixel
frame and binds later events to the new coordinate space. The recording keeps
the viewport history and the exact before and after viewport for each event.

Flow refuses a cross-origin navigation or an event from an iframe. It also
refuses an action that overlaps a resize or monitor-scale transition. The last
refusal is necessary because no exact pre-action frame exists in the new
coordinate space. An overlapping action aborts the recording and publishes no
complete metadata. When you resize between actions, stop interacting until the
new frame is stable. Recording then continues automatically.

The custom Chrome extension in `openadapt-capture` is a development prototype.
It is not this supported path and it is not a governed replay mechanism.

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
