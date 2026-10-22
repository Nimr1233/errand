import os
import re
from typing import Any
from urllib.parse import urlparse

from .config import get_config

SUPPORTED_PLATFORMS: dict[str, str] = {
    "gmail": "gmail",
    "github": "github",
    "slack": "slack",
    "notion": "notion",
    "hubspot": "hubspot",
    "linear": "linear",
    "calendar": "googlecalendar",
    "google_calendar": "googlecalendar",
    "google calendar": "googlecalendar",
}

DOMAIN_TO_PLATFORM: dict[str, str] = {
    "mail.google.com": "gmail",
    "gmail.com": "gmail",
    "github.com": "github",
    "api.github.com": "github",
    "slack.com": "slack",
    "app.slack.com": "slack",
    "notion.so": "notion",
    "notion.site": "notion",
    "hubspot.com": "hubspot",
    "app.hubspot.com": "hubspot",
    "linear.app": "linear",
    "calendar.google.com": "googlecalendar",
}

class OAuthBypassManager:
    """
    Integrates Composio to bypass web GUI login forms for API-supported platforms
    (Gmail, GitHub, Slack, Notion, HubSpot, Linear, Calendar) via managed OAuth tokens.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_config().COMPOSIO_API_KEY or os.getenv("COMPOSIO_API_KEY", "")
        self._client = None

    def get_client(self) -> Any:
        """Lazy-initialize Composio client if an API key is available."""
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            from composio import Composio
            self._client = Composio(api_key=self.api_key)
            return self._client
        except Exception:
            return None

    @classmethod
    def identify_platform(cls, target: str) -> str | None:
        """Identify if a URL, domain, or task description matches a supported platform."""
        if not target:
            return None
        target_lower = target.lower()

        # Check URL or domain match
        domain = target_lower
        if "://" in domain:
            domain = urlparse(domain).netloc
        domain = domain.split("/")[0].split(":")[0]
        if domain.startswith("www."):
            domain = domain[4:]

        if domain in DOMAIN_TO_PLATFORM:
            return DOMAIN_TO_PLATFORM[domain]

        # Check keyword matches
        for key, platform in SUPPORTED_PLATFORMS.items():
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, target_lower):
                return platform

        return None

    def is_platform_supported(self, target: str) -> bool:
        """Return True if target corresponds to a platform supported by OAuth bypass."""
        return self.identify_platform(target) is not None

    def get_platform_tools(self, platform_name: str) -> list[str]:
        """Return list of standard API actions available for the platform."""
        client = self.get_client()
        if not client:
            return [f"{platform_name}_api_action"]
        try:
            # Query composio tools if connected
            tools = client.tools.get(apps=[platform_name])
            return [getattr(t, "name", str(t)) for t in tools]
        except Exception:
            return [f"{platform_name}_generic_api_call"]

    def execute_oauth_action(
        self,
        platform_name: str,
        action_name: str,
        parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute API action using managed OAuth credentials via Composio.
        """
        client = self.get_client()
        if not client:
            return {
                "success": False,
                "platform": platform_name,
                "message": (
                    f"Composio API key not set in .env. Configure COMPOSIO_API_KEY to "
                    f"execute '{action_name}' on {platform_name} directly via OAuth APIs."
                ),
            }

        try:
            res = client.tools.execute(
                action=action_name,
                params=parameters or {},
            )
            return {
                "success": True,
                "platform": platform_name,
                "action": action_name,
                "result": res,
            }
        except Exception as e:
            return {
                "success": False,
                "platform": platform_name,
                "action": action_name,
                "error": str(e),
            }
