import sys
import os
import asyncio
import argparse
from typing import Any

from browser_use import Agent, Controller
from .config import get_config, AgentConfig
from .auth_tools import register_auth_tools
from .browser_factory import create_browser_session, close_browser_session
from .oauth_bypass import OAuthBypassManager

AUTONOMOUS_SYSTEM_PROMPT = """You are a fully autonomous browser agent with specialized authentication capabilities:
1. CREDENTIALS & LOGIN: Always check ./.credentials_vault.json or .env for existing credentials before logging in. Use get_stored_credentials(domain) to retrieve them.
2. AUTONOMOUS SIGN-UPS: When signing up for a new account, generate credentials via get_stored_credentials(domain), save them to the vault immediately, and check the inbox via fetch_verification_email_or_otp(sender_filter) to complete email verification and activate magic links.
3. TWO-FACTOR AUTH (2FA): Whenever a 2FA, OTP, or Authenticator prompt appears, immediately invoke generate_2fa_totp to produce the live 6-digit authenticator code.
4. OAUTH APIS: If the task targets supported services (Gmail, GitHub, Slack, Notion, Linear, Calendar, HubSpot), leverage OAuth tokens where appropriate.
5. PERSISTENCE & STEALTH: Reuse persistent sessions and cookies to maintain logins and minimize CAPTCHA challenges."""

class AutonomousAgentRunner:
    """Unified runner for autonomous browser tasks."""

    def __init__(self, config: AgentConfig | None = None, headless: bool | None = None):
        self.config = config or get_config()
        self.headless = self.config.HEADLESS if headless is None else headless
        self.oauth_manager = OAuthBypassManager(self.config.COMPOSIO_API_KEY)

    def _resolve_llm(self) -> Any:
        """Resolve LLM model instance based on available environment credentials."""
        if self.config.ANTHROPIC_API_KEY:
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model_name="claude-3-5-sonnet-20241022",
                    anthropic_api_key=self.config.ANTHROPIC_API_KEY,
                )
            except Exception:
                pass

        if self.config.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model="gpt-4o",
                    api_key=self.config.OPENAI_API_KEY,
                )
            except Exception:
                pass

        # Fallback to local or default mock if running offline
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o", api_key="sk-mock-key-for-local-runner")
        except Exception:
            return None

    async def run(self, task: str) -> Any:
        """Execute task autonomously using browser_use, auth tools, and persistent session."""
        print(f"[autonomous_agent] Starting task: {task}")
        controller = Controller()
        register_auth_tools(controller, self.config)

        browser = create_browser_session(self.config, headless=self.headless)
        llm = self._resolve_llm()

        try:
            agent = Agent(
                task=task,
                llm=llm,
                controller=controller,
                browser_session=browser,
                extend_system_message=AUTONOMOUS_SYSTEM_PROMPT,
            )
            result = await agent.run()
            return result
        finally:
            await close_browser_session(browser)

def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous AI Browser Agent CLI")
    parser.add_argument("--task", type=str, required=True, help="Task description for the agent")
    parser.add_argument("--headed", action="store_true", help="Run browser in visible mode")
    parser.add_argument("--use-system-chrome", action="store_true", help="Reuse host Chrome profile")

    args = parser.parse_args()
    config = get_config()
    if args.use_system_chrome:
        config.USE_SYSTEM_CHROME = True

    headless = False if args.headed else config.HEADLESS
    runner = AutonomousAgentRunner(config=config, headless=headless)
    asyncio.run(runner.run(args.task))

if __name__ == "__main__":
    main()
