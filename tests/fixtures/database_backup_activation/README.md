# Database backup activation fixtures

These files use synthetic identifiers and a test-only HMAC key. They contain
no customer, Stripe, database, or AWS credentials.

The request fixture key is:

```text
payment-signal-key-that-is-at-least-32-bytes
```

The deactivation fixture key is:

```text
cloud-deactivation-key-that-is-at-least-32-bytes
```

Never configure either value outside a test.
