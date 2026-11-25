---
description: >-
  Install the OpenAdapt Co-Pilot Chrome extension, stage form drafts inside your
  signed-in browser session, keep PHI local, and optionally pair the Native
  Messaging Host.
---

# Chrome Co-Pilot extension

OpenAdapt Co-Pilot is a Chrome extension that prepares form entries inside your
existing browser session and stops before the final submit click. You keep your
normal sign-in flow, review every draft in the tab, and decide what gets saved.

## 1. Install from the Chrome Web Store

Install the extension in one click from the
[OpenAdapt Co-Pilot listing on the Chrome Web Store](https://chromewebstore.google.com/detail/openadapt-co-pilot/bcpliibliddclnibacbjbmbpgffkjefd)
(extension ID `bcpliibliddclnibacbjbmbpgffkjefd`).

1. Open the Chrome Web Store link in Google Chrome and select **Add to Chrome**.
2. Confirm the extension prompt.
3. Pin **OpenAdapt Co-Pilot** in the Chrome toolbar so you can open the side
   panel on any tab.

No desktop installer, VPN tunnel, or separate staging sandbox is required to use
the extension in Stage-Only mode.

## 2. Stage-Only (`DRAFT_TO_COMMIT`) in your signed-in session

OpenAdapt Co-Pilot runs inside the Chrome profile where you are already signed
in.

- **Your sign-in flow stays untouched.** 1Password, SSO, and MFA work the way
  they always do. OpenAdapt never asks for passwords, session cookies, or
  one-time codes, and you do not need to provision a separate staging sandbox.
- **Drafts stop before commit.** Under Stage-Only (`DRAFT_TO_COMMIT`), the
  extension fills fields on the active web form and stops before clicking
  **Save**, **Submit**, or any other committing action.
- **You hold the final click.** Inspect the filled fields directly in the page.
  Click submit yourself when the values look right, or edit or discard the
  draft if anything is off.

## 3. Zero-PHI local privacy boundary

The Chrome extension enforces a strict local boundary on your workstation:

- **No network egress from the extension.** OpenAdapt Co-Pilot does not send
  page contents, form inputs, screenshots, or credentials to OpenAdapt servers
  or third-party APIs.
- **PHI and secrets stay on your machine.** Patient health information (PHI),
  customer records, and browser credentials remain inside your local Chrome
  session.

Read the full privacy terms at
[openadapt.ai/privacy-policy](https://openadapt.ai/privacy-policy) and review
the broader platform boundary in
[Data handling](../security/data-handling.md).

## 4. Pair the Native Messaging Host (optional)

If you only need browser form staging, you can stop after step 1. Pair the
optional Native Messaging Host when you want the extension to hand off tasks to
a local OpenAdapt runner for verified replay or Windows (Win32) practice
management system (PMS) workflows.

Chrome's Native Messaging channel connects the extension to a local host
process over standard input and output on your machine, without opening a
listening network port.

Run the host installer from your Python environment:

```bash
python -m openadapt_flow.chrome_extension.native_host.install_host
```

If you are running from a local source checkout, you can invoke `install_host.py`
directly instead.

By default, the installer registers the Chrome Web Store extension ID
`bcpliibliddclnibacbjbmbpgffkjefd` in Chrome's native messaging host manifest.
Restart Chrome after installing the host so Chrome picks up the new manifest.

Once paired, you can:

- Trigger local verified replays from the extension while keeping before-click
  and after-save checks on your machine.
- Bridge browser steps with native Win32 PMS desktop workflows through the
  local OpenAdapt runner.

For full desktop recording and approval workflows, see
[Install the desktop app](../how-to/desktop.md) and
[Run a workflow](../how-to/run.md).
