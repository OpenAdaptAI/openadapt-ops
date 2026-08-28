# Database backup activation fixtures

These files use synthetic identifiers and test-only HMAC keys. They don't
contain customer, Stripe, database, or AWS credentials.

The request fixture key is:

```text
payment-signal-key-that-is-at-least-32-bytes
```

The deactivation fixture key is:

```text
cloud-deactivation-key-that-is-at-least-32-bytes
```

The activation and lease fixtures use these additional keys:

```text
readiness-receipt-key-that-is-at-least-32-bytes
cloud-activation-ack-key-that-is-at-least-32-bytes
ops-schedule-lease-key-that-is-at-least-32-bytes
cloud-continuation-key-that-is-at-least-32-bytes
ops-renewal-receipt-key-that-is-at-least-32-bytes
cloud-lease-ack-key-that-is-at-least-32-bytes
```

Never configure these values outside a test.
