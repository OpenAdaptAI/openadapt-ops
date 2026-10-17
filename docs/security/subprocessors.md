---
description: >-
  Third-party providers used by OpenAdapt's hosted services, what runs send to
  OpenAdapt, and hosted retention.
---

# Subprocessors

This page lists the third-party providers that OpenAdapt's hosted services
use. It is for vendor-risk review and isn't a contractual subprocessor
notice; ask for the current signed list for anything a contract must cite.

A fully local or on-premises deployment uses none of these providers at run
time.

## Providers

| Provider | Role | What it can process |
|---|---|---|
| Netlify | Hosts the `app.openadapt.ai` web app | Traffic to the web app, including account and session data in transit |
| Supabase | Database, sign-in, and file storage for the web app | Accounts, organizations, workflow versions, run records, approved sanitized copies, retention and erasure receipts |
| Modal | Compute for the managed browser runner | Browser runs for public HTTPS web apps without regulated data |
| Stripe | Payments and billing | Payment and subscription data. Cards are entered on Stripe's pages. |
| Resend | Transactional email such as invitations and purchase alerts | Recipient addresses and fixed-template message text. Purchase alerts carry purchase details only. |
| GitHub | Source code, CI, and release downloads | Public source, build artifacts, CI logs. No customer workload data. |
| PostHog | Product analytics on OpenAdapt's own websites and web app, when turned on | Usage events on OpenAdapt's pages |
| GlitchTip | Error monitoring for the web app, when turned on | Error reports from the web app |
| Google Analytics | Analytics on the public website and this documentation | Page views on public pages |

Analytics apply to OpenAdapt's own pages, not to your workflows. This
documentation site skips analytics when the browser sends Do Not Track.

## What runs send to OpenAdapt

A run on your own computer that isn't connected to OpenAdapt Cloud sends
nothing to OpenAdapt.

A customer-hosted connector that reports runs to OpenAdapt Cloud sends a run
record for every run, because Cloud needs it to show run history. When a run
doesn't succeed, that record also carries a failure signal with the schema
`openadapt.automation-failure-signal/v1`:

- What it holds: the failure kind, substrate, action kind and risk class
  (both sent as `unknown` today), resolution rung, identity state, effect
  tier, delivery state, execution profile, outcome, runtime version,
  model-call count, network-call class, and a timestamp rounded down to the
  hour.
- What it never holds: report text, screenshots, OCR text, parameters,
  application names, or anything an operator typed.
- It's on by default. To leave it out, set `DO_NOT_TRACK=1` or
  `OPENADAPT_TELEMETRY=0` on the connector host. The run record itself is
  still sent.

## Hosted retention and deletion

Hosted retention follows a versioned policy with no implicit duration.
Scheduled deletion stays off until a full restore drill has passed, legal
holds pause deletion, and erasing an organization produces a receipt with no
patient or personal data. The day counts are deployment settings; ask for the
current policy version and its windows.
