---
description: >-
  How OpenAdapt Cloud protects accounts: sign-in, authenticator codes for
  privileged pages, recovery, and switching organizations.
---

# Account security

OpenAdapt Cloud separates **sign-in** from **privileged session assurance**.
Signing in with Google or an emailed link opens an ordinary session. Pages
with higher impact can also require a current 6-digit code from an
authenticator app. This is called step-up authentication: everyday work
doesn't ask for a code, and platform administration always does.

## Set up an authenticator

1. Sign in to [OpenAdapt Cloud](https://app.openadapt.ai).
2. Open the account menu in the dashboard header and choose **Security & 2FA**.
3. Select **Add authenticator**.
4. Scan the QR code with an authenticator app such as 1Password, Google
   Authenticator, or Authy, or type the setup key.
5. Enter the current 6-digit code and select **Verify & enable**.
6. Save the one-time recovery codes.

The Security page lists each verified authenticator. When account policy
requires an authenticator, the last one can't be removed.

## Open a protected page

The platform administration console checks two things on the server:

1. the signed-in email must be on the platform-administrator allowlist; and
2. the current session must have passed two-factor verification.

Belonging to an organization never grants platform administration. If an
allowed administrator opens **Platform admin** without a current
verification, Cloud asks for one current code, then returns to the intended
protected page automatically. It does not start a second enrollment.

## Recover after losing an authenticator

1. At the verification prompt, choose **Use recovery code**.
2. Enter one unused recovery code.
3. Cloud removes the authenticators you can no longer reach. That ends the
   account's active sessions, so Cloud returns you to sign-in explicitly.
4. Sign in again; Cloud returns to **Security & 2FA**.
5. Set up and verify a new authenticator before you continue.

A recovery code does not grant a two-factor session or open the protected
page. It only puts the account back on the setup path. Each code works once;
if removing the old authenticator fails, Cloud restores the code instead of
burning it.

## Switch organization or account

The account menu always shows the signed-in email and the active
organization.

- If the account belongs to more than one organization, use **Switch
  organization** to change workspace without signing in again.
- Use **Sign out** to end the current user session. Sign in again to use a
  different Google or email account.

Changing organizations never changes the authenticated person, and signing
out doesn't remove an authenticator.

Two-factor authentication protects the Cloud account. It doesn't replace the
right-record check, the record check, policy, or the deployment boundary of
a workflow.
