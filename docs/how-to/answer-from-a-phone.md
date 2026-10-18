---
description: >-
  Answer a stopped run from a phone, through OpenAdapt Cloud with no inbound
  port, or through the Desktop decision portal on your own network.
---

# Answer a halt from a phone

When a run stops and waits for a person, the question can reach a phone in
two ways: Flow's hosted lane through OpenAdapt Cloud, or the decision portal
in OpenAdapt Desktop. In both, the phone sends back one answer. The runner
then reads the live application again and repeats its checks before anything
continues. An answer is never proof that a save happened.

| | Hosted lane | Desktop decision portal |
|---|---|---|
| The phone opens | `app.openadapt.ai` | An HTTPS address your organization publishes |
| Network setup | None. The runner makes outbound HTTPS requests only | A reverse proxy or VPN that you run in front of the runner |
| The phone shows | Why the run stopped, which steps were tried, and what a continue rechecks, as fixed codes and counts | The same, plus screen crops from the run and the label of the control it couldn't find |
| Sent to OpenAdapt Cloud | A signed task with no screenshot, no free text, and no patient data | Nothing |
| Who can answer | A member of the Cloud organization, signed in with two-factor authentication | A phone paired with this computer |

## Which to use

- Use the **hosted lane** if you don't run your own ingress, if the runner is
  behind NAT, or if staff answer from outside your network.
- Use the **portal** if the person needs to see the screen to decide, for
  example to compare two records, and your IT team can publish an HTTPS
  address for it.

The two are independent. A deployment can run either one, both, or neither.

## Hosted lane

1. Connect this computer to OpenAdapt Cloud from Desktop, so it holds a
   runner credential in the keychain.
2. Turn the lane on in the deployment file, with the tenant and runner IDs
   that Cloud issued for this computer:

    ```yaml
    human_decisions:
      remote:
        enabled: true
        tenant_id: <tenant ID>
        runner_id: <runner ID>
        # context_tier: remote_identifiers   # optional: send only IDs and counts
    ```

    `enabled` must be the boolean `true`; a string or `1` leaves the lane off.
    Both IDs are required. The default `context_tier`,
    `remote_closed_context`, adds why the run stopped as fixed codes. Neither
    tier can carry a screenshot.

3. Start the attended console with the lane on. Desktop does this when you
   start the portal under **Advanced → Phone**. By hand:

    ```bash
    OPENADAPT_RUNNER_TOKEN=... openadapt flow console \
      --attend --allow-actions --remote-decisions --config deployment.yaml
    ```

    The console exits with an error instead of starting without the lane if
    the token is missing, the setting is off, the console is read-only, or the
    Cloud address isn't HTTPS. Desktop also refuses to start when this
    computer isn't registered with Cloud.

4. On the phone, open `app.openadapt.ai`, sign in, and go to
   **Attention**. To get a notification, press **Notify this browser** there.
   On an iPhone or iPad, add the page to the Home Screen first, open it from
   there, and then press **Notify this browser**. See [Get told when a run stops](../cloud/stop-alerts.md).

Each cycle, the runner publishes every open pause. When an answer comes back,
the runner applies it only if it names a pause that is open now. An answer for
a pause that has closed, or whose deadline has passed, is acknowledged and not
carried out.

## Desktop decision portal

The portal is a web page that Desktop serves from the runner. It binds to
`127.0.0.1` by default, so a phone can't reach it until your organization
publishes it.

1. Set these before you start Desktop:

    | Variable | Default | Meaning |
    |---|---|---|
    | `OPENADAPT_PORTAL_INGRESS_MODE` | `loopback` | `loopback` (this computer only) or `customer_ingress` |
    | `OPENADAPT_PORTAL_PUBLIC_ORIGIN` | unset | The exact `https://` origin your reverse proxy or VPN publishes |
    | `OPENADAPT_PORTAL_INGRESS_ACKNOWLEDGED` | `false` | Records that your organization runs that ingress |
    | `OPENADAPT_PORTAL_BIND_HOST` | unset | A literal IP address, only if the proxy isn't on this computer |
    | `OPENADAPT_PORTAL_PORT` | `0` | `0` picks a free port |

    `customer_ingress` needs both the origin and the acknowledgement. It still
    binds to `127.0.0.1` unless you set a bind address, so put the proxy on
    the runner and forward to loopback. The portal refuses to start with a
    wildcard bind address (`0.0.0.0`, `::`), a hostname as the bind address,
    or an origin that isn't plain `https://host`.

2. In Desktop, open **Advanced → Phone** and start the portal.
3. Press **Pair a phone**. Scan the QR code with the phone, then type the code
   the phone shows into Desktop. A QR code works once, for five minutes.
   Showing a new one cancels any unfinished pairing.

Paired phones are listed in Desktop and can be revoked. A phone session lasts
twelve hours.

Pairing identifies the phone, not the person holding it. If your policy needs
a named approver, the deployment must supply the signed-in operator; the phone
can't set a name.

The portal serves screen crops as PNG, JPEG, or WebP only, and marks them and
every decision `no-store`, so the phone doesn't cache them. The phone never
receives the console's own credential.

## What each answer does

The phone offers only the answers that fit the pause:

| Answer | Result |
|---|---|
| Check and continue | The runner rechecks the live application and continues this run only if every check passes |
| Skip | Skips the step, only where the workflow allows that step to be skipped |
| Stop | Ends the run. It can't be resumed |
| Teach | The run stays paused while the fix is taught in Desktop |
| Needs more help | The run stays paused for another authorized person |
| Reconcile | Shown only when an earlier save may have gone through. The runner checks the record and never sends the save again |

Desktop's own notifications say only how many items wait. They name no
workflow, record, or step.

## Related

- [Handle a halt](handle-a-halt.md)
- [Data handling](../security/data-handling.md#what-leaves-the-computer-by-command)
- [Configuration: `human_decisions`](../reference/configuration.md#human_decisions)
