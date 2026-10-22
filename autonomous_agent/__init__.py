"""
autonomous_agent - Autonomous AI Browser Agent package.
Supports website sign-ups, logins, session persistence, CAPTCHA mitigation,
email OTP / magic-link verifications, 2FA (TOTP), and OAuth API bypasses.
"""

from .config import AgentConfig, get_config
from .auth_tools import (
    generate_2fa_totp,
    fetch_verification_email_or_otp,
    get_stored_credentials,
    save_credentials,
    extract_otp_and_links,
    register_auth_tools,
)
from .oauth_bypass import OAuthBypassManager
from .browser_factory import create_browser_session, close_browser_session

__all__ = [
    "AgentConfig",
    "get_config",
    "generate_2fa_totp",
    "fetch_verification_email_or_otp",
    "get_stored_credentials",
    "save_credentials",
    "extract_otp_and_links",
    "register_auth_tools",
    "OAuthBypassManager",
    "create_browser_session",
    "close_browser_session",
    "AutonomousAgentRunner",
]

def __getattr__(name: str):
    if name == "AutonomousAgentRunner":
        from .runner import AutonomousAgentRunner
        return AutonomousAgentRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
