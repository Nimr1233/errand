import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

ENV_EXAMPLE_CONTENT = """# ==============================================================================
# Autonomous Browser Agent Configuration
# ==============================================================================

# Steel Browser (Self-hosted or Cloud)
STEEL_API_KEY=
STEEL_CDP_URL=ws://localhost:3000/
STEEL_HTTP_URL=http://localhost:3000

# Email Verification (AgentMail or Standard IMAP)
AGENTMAIL_API_KEY=
AGENTMAIL_INBOX_ID=

IMAP_HOST=
IMAP_USER=
IMAP_PASSWORD=
IMAP_PORT=993

# Two-Factor Authentication (TOTP base32 secret)
ACCOUNT_TOTP_SECRET=JBSWY3DPEHPK3PXP

# Local Stealth Browser & Session Persistence
USE_SYSTEM_CHROME=false
CHROME_PROFILE_DIR=Default
PERSISTENT_PROFILE_DIR=./.browser_profile
CREDENTIALS_VAULT_PATH=./.credentials_vault.json

# Composio OAuth & Tool Integrations
COMPOSIO_API_KEY=

# LLM Providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
"""

def ensure_env_files(base_dir: Path | None = None) -> None:
    """Ensure both .env.example and .env exist, preserving any existing keys."""
    if base_dir is None:
        base_dir = Path.cwd()

    env_example_path = base_dir / ".env.example"
    env_path = base_dir / ".env"

    if not env_example_path.exists():
        env_example_path.write_text(ENV_EXAMPLE_CONTENT, encoding="utf-8")

    if not env_path.exists():
        env_path.write_text(ENV_EXAMPLE_CONTENT, encoding="utf-8")

# Initialize and load .env
ensure_env_files()
load_dotenv(override=False)

@dataclass
class AgentConfig:
    # Steel Browser
    STEEL_API_KEY: str = field(default_factory=lambda: os.getenv("STEEL_API_KEY", ""))
    STEEL_CDP_URL: str = field(default_factory=lambda: os.getenv("STEEL_CDP_URL", "ws://localhost:3000/"))
    STEEL_HTTP_URL: str = field(default_factory=lambda: os.getenv("STEEL_HTTP_URL", "http://localhost:3000"))

    # Email
    AGENTMAIL_API_KEY: str = field(default_factory=lambda: os.getenv("AGENTMAIL_API_KEY", ""))
    AGENTMAIL_INBOX_ID: str = field(default_factory=lambda: os.getenv("AGENTMAIL_INBOX_ID", ""))
    IMAP_HOST: str = field(default_factory=lambda: os.getenv("IMAP_HOST", ""))
    IMAP_USER: str = field(default_factory=lambda: os.getenv("IMAP_USER", ""))
    IMAP_PASSWORD: str = field(default_factory=lambda: os.getenv("IMAP_PASSWORD", ""))
    IMAP_PORT: int = field(default_factory=lambda: int(os.getenv("IMAP_PORT", "993")))

    # 2FA / TOTP
    ACCOUNT_TOTP_SECRET: str = field(default_factory=lambda: os.getenv("ACCOUNT_TOTP_SECRET", "JBSWY3DPEHPK3PXP"))

    # Browser & Storage
    USE_SYSTEM_CHROME: bool = field(
        default_factory=lambda: os.getenv("USE_SYSTEM_CHROME", "false").lower() in ("true", "1", "yes")
    )
    CHROME_PROFILE_DIR: str = field(default_factory=lambda: os.getenv("CHROME_PROFILE_DIR", "Default"))
    PERSISTENT_PROFILE_DIR: str = field(default_factory=lambda: os.getenv("PERSISTENT_PROFILE_DIR", "./.browser_profile"))
    CREDENTIALS_VAULT_PATH: str = field(default_factory=lambda: os.getenv("CREDENTIALS_VAULT_PATH", "./.credentials_vault.json"))

    # Integrations & LLMs
    COMPOSIO_API_KEY: str = field(default_factory=lambda: os.getenv("COMPOSIO_API_KEY", ""))
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    HEADLESS: bool = field(default_factory=lambda: os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes"))

_config_instance: AgentConfig | None = None

def get_config(reload: bool = False) -> AgentConfig:
    """Return the global AgentConfig singleton, optionally reloading."""
    global _config_instance
    if _config_instance is None or reload:
        if reload:
            load_dotenv(override=True)
        _config_instance = AgentConfig()
    return _config_instance
