"""Keep Cloud account-security documentation aligned with the product UX."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = (ROOT / "docs" / "guides" / "account-security.md").read_text()
GUIDE_PROSE = " ".join(GUIDE.split())
CONNECT = (ROOT / "docs" / "desktop" / "connect-to-cloud.md").read_text()
CONNECT_PROSE = " ".join(CONNECT.split())
NAV = (ROOT / "mkdocs.yml").read_text()


def test_account_security_guide_explains_sign_in_step_up_and_admin_gates():
    assert "separates **sign-in** from **privileged session assurance**" in GUIDE_PROSE
    assert "platform-administrator allowlist" in GUIDE_PROSE
    assert "current session must have passed two-factor verification" in GUIDE_PROSE
    assert "asks for one current code" in GUIDE_PROSE
    assert "returns to the intended protected page automatically" in GUIDE_PROSE
    assert "does not start a second enrollment" in GUIDE_PROSE
    assert "requires two-factor authentication for organization owners" not in GUIDE_PROSE


def test_account_and_organization_switching_are_distinguished():
    assert "Switch organization" in GUIDE_PROSE
    assert "Use **Sign out** to end the current user session" in GUIDE_PROSE
    assert "Changing organizations never changes the authenticated person" in GUIDE_PROSE
    assert "exactly one active **organization**" in CONNECT_PROSE


def test_recovery_returns_to_enrollment_without_granting_privileged_access():
    assert "choose **Use recovery code**" in GUIDE_PROSE
    assert "returns you to sign-in explicitly" in GUIDE_PROSE
    assert "Sign in again; Cloud returns to **Security & 2FA**" in GUIDE_PROSE
    assert "does not grant a two-factor session or open the protected page" in GUIDE_PROSE
    assert "restores the code instead of burning it" in GUIDE_PROSE


def test_account_security_guide_is_in_the_security_navigation():
    assert (
        "Account security and privileged access: guides/account-security.md"
        in NAV
    )
