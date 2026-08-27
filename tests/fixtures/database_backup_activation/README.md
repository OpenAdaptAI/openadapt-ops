# Database backup activation fixtures

These files use synthetic identifiers and test-only HMAC keys. They don't
contain customer, Stripe, database, or AWS credentials.

The request fixture key is:

```text
payment-signal-key-that-is-at-least-32-bytes
```

Never configure these values outside a test.

This directory does not include schedule, renewal, or shutdown fixtures. Those
contracts need an asymmetric authority before they can enter this branch.
