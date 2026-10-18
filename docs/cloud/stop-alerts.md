---
description: >-
  OpenAdapt Cloud stop alerts: an email to owners and admins, a phone
  notification, and the opt-in execution.halted webhook.
---

# Get told when a run stops

When a run in your Cloud organization stops, Cloud can tell you in three ways.
None of them names the workflow, the step, the reason, or the record. Each
links back into the signed-in dashboard, where the details are.

| Channel | Who gets it | Turn it on or off |
|---|---|---|
| Email | Every owner and admin of the organization | **Settings → Organization policy → Email owners and admins when a run stops** |
| Phone or browser notification | The one browser your organization chose for alerts | **Settings → Organization policy → Send a phone notification when a run stops** |
| `execution.halted` webhook | Your webhook endpoint, for Execute API runs | **Settings → Webhooks**, per endpoint |

Both organization settings are on by default. Only owners and admins can
change them. Each stop sends one alert per channel.

## Email

The email links to the run and to **Attention**, the list of everything
waiting on a person. Cloud sends it once per stop to each owner and admin.

## Phone or browser notification

Cloud sends notifications with the Web Push standard, to one browser per
organization. To choose that browser:

1. On the phone or computer that should get alerts, sign in to
   `app.openadapt.ai` and open **Attention**.
2. Press **Notify this browser** and allow notifications when the browser
   asks. On an iPhone or iPad, add the page to the Home Screen first, open it
   from there, and then press the button.

The same browser gets alerts for decisions a paused run is waiting on. Press
**Use this browser instead** on another device to move alerts there, or
**Turn off alerts** to stop them.

The notification shows fixed text. Tapping it opens **Attention**; it carries
no sign-in and no way to act. Answering a decision still needs a signed-in
member with two-factor authentication. A notification that arrives after its
decision expired isn't shown. A browser that drops its subscription is removed,
and an enrollment lasts at most 90 days before it must be renewed.

## The `execution.halted` webhook

For [Execute](../security/execute.md) runs, Cloud sends signed lifecycle
events to one HTTPS endpoint per organization. `execution.halted` is opt-in:
an endpoint receives it only if you select it. It is sent only when a run
ends `halted_before_effect`, alongside the usual `execution.terminal` event,
and carries the same receipt.

Select it when you add the endpoint under **Settings → Webhooks**, or later on
the endpoint. Through the API, as an owner or admin:

```http
POST /api/v1/webhook-endpoints
{"url": "https://hooks.example.com/openadapt", "optional_event_types": ["execution.halted"]}
```

```http
PATCH /api/v1/webhook-endpoints/{id}
{"optional_event_types": []}
```

The endpoint URL must use HTTPS on port 443, resolve to a public address, and
carry no credentials, query, or fragment. Cloud doesn't follow redirects.

### The body

```json
{
  "schema_version": "openadapt.execute-webhook/v1",
  "event_type": "execution.halted",
  "event_id": "...",
  "delivery_attempt": 1,
  "issued_at": "2026-10-17T15:04:05Z",
  "issuer_key_id": "...",
  "receipt": {"outcome": "halted_before_effect", "...": "..."},
  "signature": "hmac-sha256:<64 hex digits>"
}
```

`receipt` is the same Execute receipt the `execution.terminal` event carries.

### Check the signature

The signing secret is shown once, when you add the endpoint or rotate it.
To check a delivery:

1. Remove `signature` from the body.
2. Serialize the rest as canonical JSON: keys sorted, no whitespace, and every
   character above U+007F written as a `\uXXXX` escape.
3. Compute HMAC-SHA256 with the secret over the bytes
   `openadapt.execute-webhook/v1`, one zero byte, then the canonical JSON.
4. Compare `hmac-sha256:` plus the hex digest with `signature`, in constant
   time.

```python
import hashlib, hmac, json

def verify(body: dict, secret: str) -> bool:
    unsigned = {k: v for k, v in body.items() if k != "signature"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"))
    mac = hmac.new(secret.encode(), b"openadapt.execute-webhook/v1\0" + canonical.encode(), hashlib.sha256)
    return hmac.compare_digest("hmac-sha256:" + mac.hexdigest(), body.get("signature", ""))
```

### Delivery

- Delivery is at least once. A retry keeps the same `event_id` and raises
  `delivery_attempt`, so deduplicate by `event_id`.
- Events can arrive out of order. A terminal event is final; a later
  non-terminal event doesn't reopen the run.
- Cloud retries temporary failures with backoff and stops after a permanent
  rejection or when retries run out.
- The `x-openadapt-event-id` and `x-openadapt-delivery-attempt` headers copy
  body fields. The signed body is the authority.
- To fill a gap, read `GET /v1/executions/{execution_id}`.
