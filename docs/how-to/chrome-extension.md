---
description: >-
  Use the OpenAdapt Co-Pilot Chrome Manifest V3 extension for local side-panel
  review, operator sign-in and MFA pause, pop-up tab return, and local secret
  redaction.
---

# Chrome Co-Pilot extension

!!! info "Upcoming release"
    This page documents the Manifest V3 Chrome Co-Pilot extension staged in
    [OpenAdapt#2575](https://github.com/OpenAdaptAI/OpenAdapt/pull/2575) for
    the upcoming Chrome Web Store and launcher release.

The **OpenAdapt Co-Pilot** extension runs inside Chrome (version 116 or newer)
as a Manifest V3 side panel paired with the local OpenAdapt runtime on the same
machine. It lets an operator watch run progress, review prefill conflicts side
by side, pause capture automatically on sign-in or MFA screens, and inspect
Ed25519 receipts without sending browser data to any remote server.

## Extension and local runtime boundary

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 265" role="img" aria-labelledby="oa-ext-title oa-ext-desc">
  <title id="oa-ext-title">Chrome Co-Pilot extension and local runtime boundary</title>
  <desc id="oa-ext-desc">Inside Chrome, the Manifest V3 Co-Pilot extension runs a side panel, background service worker, and content script. It detects sign-in and MFA fields structurally without reading input values, tracks child pop-up tabs by stripped origin only, and redacts secrets locally before sending messages over local Chrome Native Messaging (com.openadapt.extension) to the local OpenAdapt runtime on the same computer. No browser data leaves the machine.</desc>
  <defs>
    <marker id="ext-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="ext-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
  </defs>

  <!-- Chrome browser box -->
  <rect x="14" y="16" width="528" height="232" rx="12" class="oa-svg-panel-link"/>
  <text x="30" y="40" font-size="10" class="oa-svg-accent">CHROME BROWSER · MANIFEST V3</text>

  <rect x="30" y="54" width="236" height="84" rx="10" class="oa-svg-panel"/>
  <text x="44" y="76" font-size="13" class="oa-svg-title">Side panel co-pilot</text>
  <text x="44" y="96" font-size="11" class="oa-svg-muted">• Live run and conflict review</text>
  <text x="44" y="113" font-size="11" class="oa-svg-muted">• Auth pause and 1-click resume</text>
  <text x="44" y="130" font-size="11" class="oa-svg-muted">• Return to parent tab banner</text>

  <rect x="30" y="148" width="236" height="84" rx="10" class="oa-svg-panel"/>
  <text x="44" y="170" font-size="13" class="oa-svg-title">Content script</text>
  <text x="44" y="190" font-size="11" class="oa-svg-muted">• Structural password/MFA pause</text>
  <text x="44" y="207" font-size="11" class="oa-svg-muted">• Never reads .value/.defaultValue</text>
  <text x="44" y="224" font-size="11" class="oa-svg-muted">• Strict CSP, no inline scripts</text>

  <rect x="284" y="54" width="242" height="178" rx="10" class="oa-svg-panel"/>
  <text x="298" y="76" font-size="13" class="oa-svg-title">Background worker</text>
  <text x="298" y="98" font-size="11" class="oa-svg-muted">• Tracks openerTabId (origin only)</text>
  <text x="298" y="117" font-size="11" class="oa-svg-muted">• Local secret redaction</text>
  <text x="298" y="135" font-size="10.5" class="oa-svg-mono">  totp, verification_code,</text>
  <text x="298" y="151" font-size="10.5" class="oa-svg-mono">  passwords, cookies, headers</text>
  <text x="298" y="176" font-size="11" class="oa-svg-muted">• Session state in</text>
  <text x="298" y="193" font-size="10.5" class="oa-svg-mono">  chrome.storage.session</text>
  <text x="298" y="216" font-size="11" class="oa-svg-verified-txt">Zero external network egress</text>

  <!-- Native messaging bridge -->
  <path d="M542,132 L640,132" class="oa-svg-line-accent" marker-end="url(#ext-arr)"/>
  <text x="548" y="118" font-size="10" class="oa-svg-mono">nativeMessaging</text>
  <text x="548" y="149" font-size="9.5" class="oa-svg-muted">local stdio only</text>

  <!-- Local OpenAdapt runtime -->
  <rect x="646" y="28" width="320" height="208" rx="12" class="oa-svg-panel-verified"/>
  <text x="662" y="52" font-size="10" class="oa-svg-verified-txt">LOCAL COMPUTER · SAME MACHINE</text>
  <text x="662" y="74" font-size="14" class="oa-svg-title">OpenAdapt native host</text>
  <text x="662" y="96" font-size="11" class="oa-svg-mono">com.openadapt.extension</text>
  <text x="662" y="122" font-size="11.5" class="oa-svg-muted">• Receives redacted step evidence</text>
  <text x="662" y="141" font-size="11.5" class="oa-svg-muted">• Acks pause/resume by request_id</text>
  <text x="662" y="160" font-size="11.5" class="oa-svg-muted">• Drives compiled replay and checks</text>
  <text x="662" y="179" font-size="11.5" class="oa-svg-muted">• Returns Ed25519 receipt status</text>
  <text x="662" y="212" font-size="10.5" class="oa-svg-mono">openadapt_extension_host.py</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Local-only bridge:</strong> The extension talks only to the local native host over Chrome Native Messaging and never connects to remote servers.</span>
  <span><a href="../../security/data-handling/">Data handling &rarr;</a></span>
</figcaption>
</figure>

## Permissions and security model

The Manifest V3 package requests only the browser capabilities required for
local co-pilot supervision:

| Permission | Why it is needed |
|---|---|
| `sidePanel` | Renders the operator co-pilot panel for live run progress, conflict review, and receipts |
| `nativeMessaging` | Connects over local stdio to the registered `com.openadapt.extension` host on this computer |
| `storage` | Persists pause and child-tab state in `chrome.storage.session` (cleared when Chrome closes) |
| `webRequest` | Observes redacted request metadata during recording so API bindings can be proposed locally |

The extension executes no remote code, uses no inline scripts or `eval()`, and
rejects privileged co-pilot actions from any sender other than the side panel
(`copilot_requires_sidepanel`).

## Operator sign-in and MFA pause

When a web application opens a login form or multi-factor authentication
challenge, the extension pauses capture automatically:

1. **Structural detection only.** The content script detects
   `input[type="password"]` and MFA/OTP attributes (such as
   `autocomplete="one-time-code"`) without ever reading `.value` or
   `.defaultValue`.
2. **Pause and host acknowledgment.** The background worker records the pause
   in `chrome.storage.session`, displays an `AUTH` badge on the extension icon,
   and sends a pause notification carrying a `request_id` to
   `com.openadapt.extension` so the local runtime holds until acknowledged.
3. **Operator sign-in and resume.** The operator signs in directly in Chrome
   using their password manager, passkey, or authenticator app, then clicks
   **I signed in, resume** (`COPILOT_AUTH_RESUME`) in the side panel.

## Pop-up and estimator return

Many web portals open a child tab or pop-up window (for example, a cost
estimator or lookup modal) during a workflow:

- The background worker tracks child tabs and windows via `openerTabId` in
  `chrome.storage.session`, storing only the stripped `origin` (never query
  parameters or tokens).
- While a child pop-up is active, the side panel shows a banner with the child
  origin and a one-click **Return to parent tab** button
  (`COPILOT_RETURN_TO_PARENT`).
- Closing the child pop-up automatically returns focus to the parent tab and
  window.

## Local secret redaction

Before network metadata leaves the browser for the local native host,
`network_redact.js` strips sensitive fields locally, including:

- `password`, `passwd`, `secret`, `token`, `api_key`, and `authorization`
- `verification_code`, `totp`, `otp`, and MFA challenge fields
- `Cookie`, `Set-Cookie`, and authentication headers

No raw credentials or unredacted cookies are written to local recordings or
evidence files.

## Related pages

- [Record a demonstration](record.md)
- [Data handling](../security/data-handling.md)
- [Connect an agent](connect-an-agent.md)
