---
description: >-
  Record a demonstration in a browser, a Windows, macOS, or Linux app, or an
  RDP or Citrix session, by a person or an agent.
---

# Record a demonstration

A demonstration is one recording of the task, done by a person or by an
agent. One recording is enough to compile a program. Several recordings of
the same task let the compiler work out what changes between runs; see
[Build a program from several demonstrations](combine-demonstrations.md).

Record against a test copy of the application. A recording performs the task
for real.

## Install for your surface

`pip install openadapt` covers browser recording. Recording on the desktop
needs the capture extra, plus the extra for the surface you will replay on:

| Surface | Install |
|---|---|
| Browser | `python -m pip install openadapt` |
| Windows app | `python -m pip install "openadapt[capture,windows]"` |
| macOS app | `python -m pip install "openadapt[capture,macos]"` |
| Linux app (X11) | `python -m pip install "openadapt[capture,linux]"`, plus the AT-SPI system packages |
| RDP | `python -m pip install "openadapt[capture,rdp]"` |
| Citrix client window | `"openadapt[capture,macos]"` on a Mac, `"openadapt[capture,windows]"` on Windows |

Run `openadapt doctor --backend <surface>` to see what else that surface
needs on this computer. The surfaces are `web`, `windows`, `macos`, `linux`,
`rdp`, and `citrix`.

On macOS, the app or terminal that records needs the Screen Recording,
Accessibility, and Input Monitoring permissions in System Settings, and a
restart after you grant Screen Recording. Without them, recordings come out
blank with no error.

## A person records

### Browser

```bash
openadapt flow record --url https://staging.your-app.example --out rec
```

Do the task in the window that opens, then close the window or press Ctrl-C.
To record in a browser you're already signed in to, start Chromium with
remote debugging and attach to it:

```bash
openadapt flow record --url https://staging.your-app.example \
  --browser-cdp-endpoint http://127.0.0.1:9222 --out rec
```

The recorder picks the tab on the `--url` origin and doesn't launch,
navigate, or close the browser. Use `--browser-page-url` when more than one
tab is open on that origin.

### Desktop app

With no `--url`, `record` captures this computer's desktop:

```bash
openadapt flow record --out rec --task "Post an invoice"
```

To record one window only, which keeps other apps out of the recording (supported on macOS and Windows):

```bash
openadapt flow record --out rec --window "TextEdit"
openadapt flow record --backend macos --macos-app TextEdit --out rec
```

### RDP or Citrix

OpenAdapt drives the client window on the local computer, the way a person
at that computer does. Nothing is installed inside the remote session. Scope
the recording to the client window:

```bash
openadapt flow record --backend citrix --out rec
openadapt flow record --backend rdp --rdp-window "<client app>" \
  --rdp-window-title "<window title>" --out rec
```

For Citrix, the client window's owner defaults by host operating system.
`--rdp-window` names the client exactly: its process name on Windows (for
example `wfica32`) or its app name on macOS (for example `Citrix Viewer`).
`--rdp-window-title` picks one window when the client has several open.

A remote session shows only pixels, so mark the area that identifies the
record, such as the patient banner, with `--identifier X,Y,W,H` in recording
pixels. The compiler crops it, and replay compares it before each save.

### Inputs and secrets

| Option | What it does |
|---|---|
| `--param FIELD` | Records a typed value as an input with a default. In the browser, `FIELD` is the field name or id. On a desktop or remote surface, use `NAME=VALUE`. |
| `--secret FIELD` | Never saves the typed value. At run time it comes from `OPENADAPT_FLOW_SECRET_<FIELD>`. Password fields are always treated as secret. |
| `--identifier FIELD` | Marks the field or region that identifies the record (browser: field name; desktop or remote: `X,Y,W,H`). |

## An agent records

An agent can perform the demonstration through the recording tools of the
OpenAdapt MCP server, such as `observe`, `start_record`, `click`,
`pause_for_input`, `stop_record`, `compile`, and `admit`. A person stays at the computer to sign in, type secrets, and
accept the result. The recording notes who did each step, and an agent never
accepts its own recording.

In Claude Code:

```bash
claude mcp add --scope user openadapt-authoring -- uvx --python 3.12 --from 'openadapt-agent[tutorial]' \
  openadapt-agent serve --authoring --url https://staging.your-app.example --headed
```

This only registers the server. Claude Code starts it the next time you run
`claude`. The `tutorial` extra brings the browser driver that `--url` needs.
`--url` opens the app in a new Chromium window with no saved sign-ins, and
`--headed`, which `--url` requires, keeps it visible so the person can sign in
when the agent pauses. Run `claude` and ask your agent to record the task with
you. When the task is done, the agent
calls `compile`, which writes the bundle to
`~/.openadapt/runs/authoring/bundle` by default. The agent then calls
`admit`: your MCP client shows the person a confirmation form, and only the
person's answer accepts the bundle. A client that can't show forms can't
accept a bundle. The authoring server doesn't turn on runs.

An agent can also record on native Windows apps, through the Windows agent
server, and in RDP and Citrix client windows, from pixels alone. This is on the
`main` branch and not yet in a release. Its tests run against a mock Windows
server and stand-in client windows; no recording against a real Windows, RDP,
or Citrix session is on record yet. See
[Recording on Windows, RDP and Citrix](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/RECORDING_ON_WINDOWS_RDP_CITRIX.md).

## One program per surface

A compiled program is bound to the surface it was recorded on: one browser
tab, one desktop app, or one remote session. A run on a different surface is
refused unless you pass `--allow-surface-override`, and the run report
records that override. For a task that crosses two applications, record one
program per surface and chain them with `compose`; see
[Build a program from several demonstrations](combine-demonstrations.md#chain-programs-across-applications).

## Next

[Compile the recording](../tutorials/first-workflow.md#3-compile-it), then
[add record checks](record-checks.md).
