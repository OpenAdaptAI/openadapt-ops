---
description: >-
  Install the OpenAdapt Desktop app on Windows, macOS, or Linux, grant the
  permissions recording needs, and check a first recording.
---

# Install the desktop app

OpenAdapt Desktop is a graphical front end for the same engine the
`openadapt flow` commands use. You record, review, teach, and run workflows
on your own computer. Nothing leaves the computer unless you
connect it to [OpenAdapt Cloud](deploy.md#openadapt-cloud).

## 1. Download and install

Get the installer from [openadapt.ai/download](https://openadapt.ai/download).
The page detects your operating system and offers the right build. The
current build is the GitHub pre-release `desktop-v0.15.0`. It includes
openadapt-flow 1.27.1. Its sidebar has **Workflows**, **Record**, **Runner**,
**Phone**, and **Settings**. **Runner** runs workflows that OpenAdapt Cloud sends
to this computer; it's off until you turn it on.

| Operating system | Installer |
|---|---|
| Windows | `.msi` or `.exe` |
| macOS (Apple silicon or Intel) | `.dmg` |
| Linux | `.AppImage` or `.deb` |

The Windows and Linux installers are unsigned, and the macOS installers are
ad-hoc signed, so your operating system may warn on first launch. Before you
override that warning, check the file against the release's `SHA256SUMS`. The
release also includes a CycloneDX software bill of materials. See
[Release integrity](../security/release-integrity.md).

## 2. Grant permissions

Until these are granted, recordings come out blank and the operating system
shows no error.

=== "macOS"

    OpenAdapt needs three permissions: **Screen Recording** to capture the
    screen, **Accessibility** to observe and replay input, and **Input
    Monitoring** to record keyboard and mouse input from desktop apps.

    1. Open **System Settings**.
    2. Go to **Privacy & Security → Screen Recording** and turn on OpenAdapt.
    3. Go to **Privacy & Security → Accessibility** and turn on OpenAdapt.
    4. Go to **Privacy & Security → Input Monitoring** and turn on OpenAdapt.
    5. Quit and reopen OpenAdapt. macOS applies a new Screen Recording
       permission only after the app restarts.

    If OpenAdapt isn't listed, select **+** and add it from `/Applications`.
    If a recording doesn't start and shows "Input Monitoring permission is
    required", turn on Input Monitoring and start again.

=== "Windows"

    Ordinary windows need no permission. Windows blocks an app from seeing or
    driving a window that runs as administrator. If the app you want to
    record runs as administrator, run OpenAdapt as administrator too.
    Otherwise that window records blank and input is ignored.

=== "Linux"

    Recording and replay of native apps use the AT-SPI accessibility service
    on X11. Run `openadapt doctor --backend linux` to see which system
    packages are missing.

## 3. Check a first recording

Record a few seconds of any app, then stop. If the frames show your screen,
the permissions are right. If they're blank, recheck step 2 and restart the
app. [Troubleshoot](troubleshoot.md) covers other first-week problems.

## Approving saves

`desktop-v0.15.0` predates per-save approval, so its runs don't pause before
a save. In the next Desktop build, when a run waits before a save, Desktop
shows the filled form. You approve it to save exactly what you see, or decline
with a reason. Until then, answer waiting saves from `openadapt flow` runs
with `openadapt flow item-approval`; see
[Run a workflow](run.md#3-choose-how-saves-are-approved).
