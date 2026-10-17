# Account security and privileged access

OpenAdapt Cloud separates **sign-in** from **privileged session assurance**.
Google or magic-link sign-in establishes the account session. Actions with
higher impact can additionally require a current 6-digit code from an
authenticator app.

This extra check is called **step-up authentication**. It lets a signed-in user
continue ordinary workspace activity without repeatedly entering a code while
keeping platform administration behind a second factor.

## Set up an authenticator

1. Sign in to [OpenAdapt Cloud](https://app.openadapt.ai).
2. Open the account menu in the dashboard header.
3. Choose **Security & 2FA**.
4. Select **Add authenticator**.
5. Scan the QR code with a TOTP authenticator such as 1Password, Google
   Authenticator, or Authy. You can use the displayed setup key instead.
6. Enter the current 6-digit code and select **Verify & enable**.

The Security page lists each verified authenticator and whether authenticator
enrollment is required by account policy. When policy requires enrollment, the
last verified factor cannot be removed.

## Open a protected page

The platform-admin console has two independent server-side gates:

1. the signed-in email must be on the platform-administrator allowlist; and
2. the current session must have passed two-factor verification.

Organization membership alone never grants platform administration. If an
authorized platform administrator opens **Platform admin** from the account
menu without current two-factor assurance, Cloud asks for one current code.
After the code is accepted, Cloud returns to the intended protected page
automatically. It does not start a second enrollment.

Other accounts can opt in from the same Security page.

## Recover after losing an authenticator

Save the one-time recovery codes shown after enrollment. If the authenticator
is no longer available:

1. Open the protected page and choose **Use recovery code** at the verification
   prompt.
2. Enter one unused recovery code.
3. Cloud removes the inaccessible authenticator factors. Supabase invalidates
   the account's active sessions as part of administrative factor removal, so
   Cloud returns you to sign-in explicitly.
4. Sign in again; Cloud returns to **Security & 2FA**.
5. Enroll and verify a new authenticator before continuing to the protected
   destination.

A recovery code does not grant a two-factor session or open the protected page.
It restores the account to the enrollment path through normal reauthentication.
Each code works once; if factor removal fails, Cloud restores the code instead
of burning it on an incomplete recovery.

## Switch workspace or account

The account menu always shows the signed-in email and active organization:

- If the account belongs to more than one organization, use **Switch
  organization** to change workspace without signing in again.
- Use **Sign out** to end the current user session. Sign in again to use a
  different Google or email account.

Changing organizations never changes the authenticated person, and signing out
does not remove an enrolled authenticator.

## Security model

OpenAdapt Cloud uses authenticator assurance levels to distinguish an ordinary
signed-in session from one that has presented a second factor.
Protected routes re-check both identity and assurance on the server; hiding a
link in the browser is not the security boundary.

Two-factor authentication protects the Cloud account and control plane. It does
not replace workflow-level identity checks, policy, effect verification, or the
declared execution and data boundary.

For the rest of the hosted security model, see
[Security and deployment review](security-review.md) and the public
[OpenAdapt Trust Center](https://openadapt.ai/security).
