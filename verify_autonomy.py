import sys
import secrets
import asyncio
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

def log_step(phase: int, name: str, success: bool, details: str = "") -> None:
    status = "PASS" if success else "FAIL"
    symbol = "[OK]" if success else "[X]"
    print(f"{symbol} Phase {phase}: {name} -> {status}")
    if details:
        print(f"    {details}")

def test_imports() -> bool:
    print("\n--- 1. Testing Package Imports ---")
    try:
        import browser_use
        import steel
        import composio
        import agentmail
        import imap_tools
        import pyotp
        import playwright
        from autonomous_agent import (
            AgentConfig,
            get_config,
            generate_2fa_totp,
            fetch_verification_email_or_otp,
            get_stored_credentials,
            save_credentials,
            extract_otp_and_links,
            register_auth_tools,
            OAuthBypassManager,
            create_browser_session,
            close_browser_session,
            AutonomousAgentRunner,
        )
        log_step(1, "Clean imports of all required packages", True, "browser_use, steel, composio, agentmail, imap_tools, pyotp, playwright, autonomous_agent")
        return True
    except Exception as e:
        log_step(1, "Clean imports of all required packages", False, str(e))
        return False

def test_totp_generation() -> bool:
    print("\n--- 2. Testing 2FA (TOTP) Generation ---")
    try:
        from autonomous_agent.auth_tools import generate_2fa_totp

        test_secret = "JBSWY3DPEHPK3PXP"
        code = generate_2fa_totp(test_secret)

        assert isinstance(code, str), f"Expected str, got {type(code)}"
        assert len(code) == 6, f"Expected 6 digits, got '{code}' (length {len(code)})"
        assert code.isdigit(), f"Expected all numeric digits, got '{code}'"

        log_step(2, "Live RFC 6238 TOTP generation", True, f"Secret: {test_secret} -> 6-digit TOTP: {code}")
        return True
    except Exception as e:
        log_step(2, "Live RFC 6238 TOTP generation", False, str(e))
        return False

def test_credentials_vault() -> bool:
    print("\n--- 3. Testing Credential Vault Read/Write Cycle ---")
    try:
        from autonomous_agent.auth_tools import get_stored_credentials, save_credentials

        # Unique domain per test run to guarantee test idempotency
        unique_token = secrets.token_hex(4)
        test_domain = f"verify-test-{unique_token}.com"

        # 1. Autonomous sign-up profile creation
        signup_creds = get_stored_credentials(test_domain, auto_create_if_missing=True)
        assert signup_creds["domain"] == test_domain
        assert signup_creds["is_new"] is True
        assert signup_creds["username"].startswith("agent_")
        assert len(signup_creds["password"]) >= 16

        # 2. Update credentials in vault
        updated_pwd = "VaultSecuredPass_2026!#"
        save_credentials(test_domain, {"password": updated_pwd, "status": "active_verified"})

        # 3. Read back and verify persistence
        retrieved_creds = get_stored_credentials(test_domain, auto_create_if_missing=False)
        assert retrieved_creds["is_new"] is False
        assert retrieved_creds["password"] == updated_pwd
        assert retrieved_creds["status"] == "active_verified"

        log_step(3, "Credential vault autonomous sign-up & persistence", True, f"Domain: {test_domain}, Username: {signup_creds['username']}, Stored & Verified")
        return True
    except Exception as e:
        log_step(3, "Credential vault autonomous sign-up & persistence", False, str(e))
        return False

def test_email_and_otp_extraction() -> bool:
    print("\n--- 4. Testing HTML Email Regex Extraction ---")
    try:
        from autonomous_agent.auth_tools import extract_otp_and_links

        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Verify Your Account</title></head>
        <body style="font-family: Arial, sans-serif;">
            <h2>Welcome to SecureCloud, Alex!</h2>
            <p>Thank you for signing up. Please enter the following 6-digit confirmation code:</p>
            <div style="font-size: 28px; font-weight: bold; color: #2b6cb0; padding: 12px; background: #ebf8ff;">
                739201
            </div>
            <p>This verification code expires in 15 minutes.</p>
            <p>Alternatively, click the link below to automatically activate your account:</p>
            <p>
                <a href="https://securecloud.io/auth/verify?token=4a8f9c1e2b3d4e5f6a7b8c9d0e1f2a3b&email=alex@test.com">
                    Confirm Email Address
                </a>
            </p>
            <p>Security notice: Never share your one-time code with anyone.</p>
        </body>
        </html>
        """

        res = extract_otp_and_links(sample_html)
        assert res["otp"] == "739201", f"Expected OTP '739201', got '{res['otp']}'"
        assert "https://securecloud.io/auth/verify?token=4a8f9c1e2b3d4e5f6a7b8c9d0e1f2a3b&email=alex@test.com" in res["magic_link"], f"Unexpected magic link: {res['magic_link']}"
        assert len(res["all_otps"]) >= 1

        log_step(4, "HTML Email OTP & Magic Link Regex Extraction", True, f"Extracted OTP: {res['otp']}, Magic Link: {res['magic_link'][:60]}...")
        return True
    except Exception as e:
        log_step(4, "HTML Email OTP & Magic Link Regex Extraction", False, str(e))
        return False

async def test_browser_session() -> bool:
    print("\n--- 5. Testing Headless Browser Launch, Navigation, and Teardown ---")
    try:
        from autonomous_agent.browser_factory import create_browser_session, close_browser_session

        browser = create_browser_session(headless=True)
        assert browser is not None, "BrowserSession creation returned None"

        await browser.start()
        await browser.navigate_to("about:blank")

        title = await browser.get_current_page_title()
        url = await browser.get_current_page_url()

        assert "about:blank" in url or url == "about:blank", f"Unexpected URL: {url}"

        await close_browser_session(browser)
        log_step(5, "Browser headless launch, navigation & clean teardown", True, f"Navigated to '{url}' (Title: '{title}'), session reset successfully")
        return True
    except Exception as e:
        log_step(5, "Browser headless launch, navigation & clean teardown", False, str(e))
        return False

async def main_async() -> int:
    print("=" * 70)
    print("AUTONOMOUS AGENT VERIFICATION SUITE")
    print("=" * 70)

    results = []
    results.append(test_imports())
    results.append(test_totp_generation())
    results.append(test_credentials_vault())
    results.append(test_email_and_otp_extraction())
    results.append(await test_browser_session())

    print("\n" + "=" * 70)
    passed = sum(1 for r in results if r)
    total = len(results)

    if passed == total:
        print(f"ALL CHECKS PASSED: {passed}/{total} (100% SUCCESS)")
        print("Exit Code: 0")
        print("=" * 70)
        return 0
    else:
        print(f"FAILED CHECKS: {total - passed}/{total}")
        print("Exit Code: 1")
        print("=" * 70)
        return 1

def main() -> None:
    code = asyncio.run(main_async())
    sys.exit(code)

if __name__ == "__main__":
    main()
