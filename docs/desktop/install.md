---
description: >-
  Install the OpenAdapt Desktop cockpit on Windows, macOS, or Linux, grant the
  required permissions, and verify your first local recording.
---

# Desktop app: install and first run

The OpenAdapt desktop app is the local cockpit for the record →
compile → replay → teach loop: record on your own machine, compile into a
deterministic bundle with [`openadapt flow`](../reference/cli.md), then replay,
review, and teach corrections, all locally. Nothing leaves your machine unless
you explicitly push it to a [cloud workspace](connect-to-cloud.md).

!!! note "Prefer the command line?"
    The desktop app and the [`openadapt flow` CLI](../reference/cli.md) drive the
    same engine; the app is a graphical front end over the same compiler and
    governed runtime. To stay in a terminal, start with the
    [five-minute tour](../get-started/index.md) and skip this page.

## 1. Download and install

Get the installer from
[openadapt.ai/download](https://openadapt.ai/download). The page detects your OS
and architecture and offers the right build. Public Beta release
`desktop-v0.14.0` ships the complete Windows, macOS, and Linux installer set with
`SHA256SUMS`, a CycloneDX SBOM, per-platform metadata, and build-provenance
attestations.

| OS | Installer |
|---|---|
| Windows | `.msi` or `.exe` |
| macOS (Apple Silicon / Intel) | `.dmg` |
| Linux | `.AppImage` or `.deb` |

The desktop app and `openadapt flow` use the same released engine. Browser
workflows can use the managed OpenAdapt Cloud runner; native desktop, RDP, and
Citrix workflows execute locally or in a self-hosted/customer-controlled runtime
and can connect to Cloud for governed reports and updates.

## 2. Get past the first-launch OS warning

The Windows/Linux builds are **unsigned** and the macOS builds are **ad-hoc
signed**, so your OS can show a one-time publisher warning at first launch.
Verify `SHA256SUMS` and the release provenance before overriding it.

=== "macOS"

    macOS will say the app is from an unidentified developer. To open it the
    first time: **right-click (or Control-click) OpenAdapt in Applications →
    Open → Open**. macOS remembers your choice, so you won't see this again.
    Signed, notarized builds are planned; the pipeline is signing-ready and
    switches over once credentials are provisioned.

=== "Windows"

    Windows SmartScreen may show a blue **"Windows protected your PC"** banner.
    Click **More info → Run anyway** to install. This appears because the
    installer is not code-signed yet; signing is on the roadmap.

## 3. Grant OS permissions (the step everyone misses)

!!! danger "This is the #1 silent-failure mode"
    Until you grant the permissions below, screen capture returns a **blank or
    black frame** and input may go nowhere: the app looks like it is recording
    but captures nothing. The OS shows no error dialog; recordings just come out
    empty. Grant these **before** your first recording.

=== "macOS"

    OpenAdapt needs two permissions to record: **Screen Recording** (to capture
    the screen) and **Accessibility** (to observe and replay mouse and keyboard
    input).

    1. Open **System Settings** (on macOS 12 Monterey and earlier this is
       **System Preferences → Security & Privacy → Privacy**).
    2. Go to **Privacy & Security → Screen Recording**. Toggle **OpenAdapt on**.
    3. Go to **Privacy & Security → Accessibility**. Toggle **OpenAdapt on**.
    4. **Quit and reopen OpenAdapt.** macOS applies a newly granted Screen
       Recording permission only after the app restarts. This is a macOS
       requirement, not an app bug.

    If OpenAdapt is not listed, click **+**, then add it from `/Applications`.
    If a recording still comes out blank, confirm **both** toggles are on and
    that you restarted the app after granting Screen Recording.

=== "Windows"

    On Windows, capture and UI Automation work out of the box for ordinary
    windows; no permission prompt is needed for a first recording.

    The one exception is **elevated (administrator) windows**. Windows blocks a
    normally-privileged app from seeing or driving a window running
    **as administrator** (UAC elevation). If the target app runs elevated, run
    **OpenAdapt as administrator too** (right-click → *Run as administrator*) so
    both processes share an integrity level. Otherwise capture of that window
    comes back blank and input is ignored.

    For remote-session substrates (Citrix / RDP), see the
    [troubleshooting guide](../guides/troubleshooting.md#session-0) for the
    session-0 / interactive-session caveat.

## 4. Verify with a test recording

Record a few seconds of any app, then stop (the same capture is available from
[`openadapt flow record`](../reference/cli.md#record) on the CLI). If the frames
show your screen (not a blank or black image), permissions are correct and you
are ready to record a real workflow.

- **Blank / black frames on macOS** → Screen Recording is not granted, or you
  did not restart the app after granting it. Redo step 3.
- **Clicks not captured on macOS** → Accessibility is not granted.
- **One specific window is blank on Windows** → that window is elevated; see the
  UAC note in step 3.

The [troubleshooting guide](../guides/troubleshooting.md) covers these and other
first-week failures.

## During a governed run

Desktop 0.14.0 can show a separate always-on-top status surface without adding
anything to the target application. While OpenAdapt is observing or executing,
the surface is non-focusable, ignores pointer input, exposes no controls, and is
excluded from capture before it becomes visible. Controls become interactive
only after the run reaches a safe paused or terminal state. The overlay reports
runtime state; OpenAdapt never uses it as resolution or verification evidence.

For published footage, OpenAdapt post-composes the status surface onto a
derivative as **Guided view**; **Raw footage** shows the immutable media. Guided
target tracking appears only when the media digest, exact decoded frame,
viewport mapping, and runtime-bound rectangle agree. The compact status capsule
uses a bottom corner that does not cover the target or another protected region,
and disappears if neither corner is safe. These presentation elements are not
verification evidence and do not weaken the pointer, focus, or capture-exclusion
boundary. [Watch the public demo](https://app.openadapt.ai/demo#footage) or
review the exact released
[control-overlay contract](https://github.com/OpenAdaptAI/openadapt-desktop/blob/desktop-v0.14.0/docs/CONTROL_OVERLAY.md).

## Where to go next

<div class="grid cards" markdown>

-   [__Connect to a cloud workspace__](connect-to-cloud.md)

    Sign in, mint an ingest token, and push a recording to your dashboard.

-   [__Record your own app__](../guides/record-your-app.md)

    The full record → compile → replay loop on your own application.

-   [__Troubleshooting__](../guides/troubleshooting.md)

    Blank capture, over-halting, a stuck offline queue, and the session-0 case.

</div>
