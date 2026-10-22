import os
import socket
from pathlib import Path
from urllib.parse import urlparse
import httpx

from browser_use import BrowserSession, BrowserProfile
from .config import get_config, AgentConfig

STEALTH_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--no-first-run",
    "--no-default-browser-check",
]

def is_steel_cdp_available(cdp_or_http_url: str = "http://localhost:3000", timeout: float = 0.8) -> bool:
    """Check if the local Steel browser container or endpoint is responding."""
    try:
        parsed = urlparse(cdp_or_http_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (3000 if "3000" in cdp_or_http_url else 80)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False

def create_browser_session(
    config: AgentConfig | None = None,
    headless: bool | None = None,
) -> BrowserSession:
    """
    Factory creating a production-grade BrowserSession.
    Connects to local steel-browser CDP endpoint if active.
    Otherwise falls back seamlessly to a persistent local stealth Chromium context
    or the host system Chrome profile.
    """
    cfg = config or get_config()
    is_headless = cfg.HEADLESS if headless is None else headless

    # 1. Attempt connection to Steel browser if active
    if is_steel_cdp_available(cfg.STEEL_HTTP_URL):
        try:
            profile = BrowserProfile(
                cdp_url=cfg.STEEL_CDP_URL,
                headless=is_headless,
                enable_default_extensions=False,
            )
            return BrowserSession(browser_profile=profile)
        except Exception:
            pass

    # 2. Check if host's signed-in system Chrome profile is requested
    if cfg.USE_SYSTEM_CHROME:
        try:
            return BrowserSession.from_system_chrome(
                profile_directory=cfg.CHROME_PROFILE_DIR,
                headless=is_headless,
                args=STEALTH_ARGS,
            )
        except Exception:
            # Fall back to local persistent profile if system chrome cannot be acquired
            pass

    # 3. Default to persistent local stealth profile context
    profile_dir = Path(cfg.PERSISTENT_PROFILE_DIR)
    profile_dir.mkdir(parents=True, exist_ok=True)

    profile = BrowserProfile(
        user_data_dir=str(profile_dir.resolve()),
        headless=is_headless,
        enable_default_extensions=False,
        args=STEALTH_ARGS,
    )
    return BrowserSession(browser_profile=profile)

async def close_browser_session(session: BrowserSession) -> None:
    """Safely stop and reset a BrowserSession."""
    if session is not None:
        try:
            await session.close()
        except Exception:
            try:
                await session.stop()
            except Exception:
                pass
