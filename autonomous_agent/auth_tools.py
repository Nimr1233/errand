import os
import re
import json
import time
import secrets
import string
from urllib.parse import urlparse
from pathlib import Path
from typing import Any

import pyotp
from browser_use import Controller, ActionResult
from .config import get_config, AgentConfig

def _normalize_domain(domain_or_url: str) -> str:
    """Extract clean lowercase domain without protocol or path."""
    if not domain_or_url:
        return "default"
    clean = domain_or_url.strip().lower()
    if "://" in clean:
        clean = urlparse(clean).netloc
    clean = clean.split("/")[0].split(":")[0]
    # Remove leading www.
    if clean.startswith("www."):
        clean = clean[4:]
    return clean or "default"

def generate_strong_password(length: int = 18) -> str:
    """Generate a high-entropy password meeting strict complexity requirements."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd)
                and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%^&*()-_=+" for c in pwd)):
            return pwd

def _get_vault_path() -> Path:
    cfg = get_config()
    return Path(cfg.CREDENTIALS_VAULT_PATH)

def load_vault() -> dict[str, Any]:
    """Read credentials vault safely."""
    vault_path = _get_vault_path()
    if not vault_path.exists():
        return {}
    try:
        with open(vault_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_vault(data: dict[str, Any]) -> None:
    """Save credentials vault atomically."""
    vault_path = _get_vault_path()
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = vault_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp_path.replace(vault_path)

def generate_2fa_totp(service_env_key: str = "ACCOUNT_TOTP_SECRET") -> str:
    """
    Generate and return a live 6-digit RFC 6238 authenticator code using pyotp.
    Accepts an environment variable name (e.g. 'ACCOUNT_TOTP_SECRET')
    or a raw base32 secret.
    """
    secret = os.getenv(service_env_key, "")
    if not secret:
        # Check if parameter is a raw secret itself (base32 string)
        cleaned_param = service_env_key.replace(" ", "").replace("-", "").strip()
        if len(cleaned_param) >= 16 and all(c.isalnum() for c in cleaned_param):
            secret = cleaned_param
        else:
            secret = get_config().ACCOUNT_TOTP_SECRET

    clean_secret = secret.replace(" ", "").replace("-", "").strip()
    if not clean_secret:
        clean_secret = "JBSWY3DPEHPK3PXP" # RFC 6238 test vector secret

    totp = pyotp.TOTP(clean_secret)
    return str(totp.now())

def extract_otp_and_links(html_or_text: str) -> dict[str, Any]:
    """
    Deterministic regex extractor for 6-digit OTP codes and activation/magic links.
    """
    if not html_or_text:
        return {"otp": "", "magic_link": "", "all_otps": [], "all_links": []}

    # Extract all URLs first
    url_pattern = re.compile(
        r'https?://[^\s<>"\'\]]+(?:verify|confirm|activate|magic|token|login|auth)[^\s<>"\'\]]*',
        re.IGNORECASE
    )
    magic_links = list(dict.fromkeys(url_pattern.findall(html_or_text)))

    # Look for contextual OTP first (e.g., "verification code: 123456", "Your code is 654321")
    context_pattern = re.compile(
        r'(?:verification|security|confirmation|login|auth|one-time|code|otp|pin|passcode)[\s\w:=-]{0,35}?(\b\d{6}\b)',
        re.IGNORECASE
    )
    context_matches = context_pattern.findall(html_or_text)

    # General 6-digit number search (avoiding years/dates)
    general_pattern = re.compile(r'\b\d{6}\b')
    all_6_digits = general_pattern.findall(html_or_text)

    # Filter out obvious false positives (e.g., 202601)
    filtered_digits = [d for d in all_6_digits if not (d.startswith("19") or d.startswith("20"))]
    if not filtered_digits:
        filtered_digits = all_6_digits

    primary_otp = ""
    if context_matches:
        primary_otp = context_matches[0]
    elif filtered_digits:
        primary_otp = filtered_digits[0]

    primary_link = magic_links[0] if magic_links else ""

    return {
        "otp": primary_otp,
        "magic_link": primary_link,
        "all_otps": list(dict.fromkeys(context_matches + filtered_digits)),
        "all_links": magic_links,
    }

def fetch_verification_email_or_otp(
    sender_filter: str = "",
    timeout_seconds: int = 20,
    poll_interval: float = 3.0
) -> dict[str, Any]:
    """
    Supports both AgentMail and standard IMAP.
    Polls unseen messages with retry backoff, extracts 6-digit OTPs and magic links.
    """
    cfg = get_config()
    start_time = time.time()

    # 1. Try AgentMail if API key configured
    if cfg.AGENTMAIL_API_KEY:
        try:
            from agentmail import AgentMail
            client = AgentMail(api_key=cfg.AGENTMAIL_API_KEY)
            while time.time() - start_time < timeout_seconds:
                try:
                    inbox_id = cfg.AGENTMAIL_INBOX_ID or "default"
                    messages = client.inboxes.get_messages(inbox_id=inbox_id)
                    for msg in getattr(messages, "data", []):
                        body = getattr(msg, "text", "") or getattr(msg, "html", "")
                        extracted = extract_otp_and_links(body)
                        if extracted["otp"] or extracted["magic_link"]:
                            return {
                                "status": "found",
                                "source": "agentmail",
                                "sender": getattr(msg, "from_", ""),
                                **extracted
                            }
                except Exception:
                    pass
                time.sleep(poll_interval)
        except Exception:
            pass

    # 2. Try standard IMAP if credentials configured
    if cfg.IMAP_HOST and cfg.IMAP_USER and cfg.IMAP_PASSWORD:
        try:
            from imap_tools import MailBox, AND
            while time.time() - start_time < timeout_seconds:
                try:
                    with MailBox(cfg.IMAP_HOST, port=cfg.IMAP_PORT).login(cfg.IMAP_USER, cfg.IMAP_PASSWORD) as mailbox:
                        criteria = AND(seen=False)
                        if sender_filter:
                            criteria = AND(seen=False, from_=sender_filter)

                        for msg in mailbox.fetch(criteria, limit=5, reverse=True):
                            body = f"{msg.subject}\n{msg.text}\n{msg.html}"
                            extracted = extract_otp_and_links(body)
                            if extracted["otp"] or extracted["magic_link"]:
                                return {
                                    "status": "found",
                                    "source": "imap",
                                    "sender": msg.from_,
                                    "subject": msg.subject,
                                    **extracted
                                }
                except Exception:
                    pass
                time.sleep(poll_interval)
        except Exception:
            pass

    return {
        "status": "not_found",
        "message": "No new verification email or OTP found within timeout period.",
        "otp": "",
        "magic_link": "",
        "all_otps": [],
        "all_links": [],
    }

def get_stored_credentials(domain: str, auto_create_if_missing: bool = True) -> dict[str, Any]:
    """
    Reads site credentials or sign-up profile details from the vault.
    If missing and auto_create_if_missing=True, generates a new robust profile,
    saves it immediately to ./.credentials_vault.json, and returns it.
    """
    clean_domain = _normalize_domain(domain)
    vault = load_vault()

    if clean_domain in vault:
        creds = vault[clean_domain]
        return {
            "domain": clean_domain,
            **creds,
            "is_new": False,
        }

    if auto_create_if_missing:
        token = secrets.token_hex(3)
        new_username = f"agent_{token}"
        new_email = f"agent_{token}@{clean_domain}.local"
        new_password = generate_strong_password(18)
        new_creds = {
            "username": new_username,
            "password": new_password,
            "email": new_email,
            "totp_secret": get_config().ACCOUNT_TOTP_SECRET,
            "first_name": "Alex",
            "last_name": "Agent",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        vault[clean_domain] = new_creds
        save_vault(vault)
        return {
            "domain": clean_domain,
            **new_creds,
            "is_new": True,
        }

    return {"domain": clean_domain, "is_new": False}

def save_credentials(domain: str, credentials_data: dict[str, Any]) -> dict[str, Any]:
    """Explicitly save or update credentials in the vault."""
    clean_domain = _normalize_domain(domain)
    vault = load_vault()
    existing = vault.get(clean_domain, {})
    existing.update(credentials_data)
    existing["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    vault[clean_domain] = existing
    save_vault(vault)
    return {"domain": clean_domain, **existing}

def register_auth_tools(controller: Controller, config: AgentConfig | None = None) -> Controller:
    """Registers deterministic custom actions with browser_use Controller."""

    @controller.action("Generate 6-digit 2FA / TOTP code for the current service/account")
    def tool_generate_2fa_totp(service_env_key: str = "ACCOUNT_TOTP_SECRET") -> ActionResult:
        code = generate_2fa_totp(service_env_key)
        return ActionResult(extracted_content=f"2FA_TOTP_CODE: {code}")

    @controller.action("Fetch verification email or 6-digit OTP / magic activation link from inbox")
    def tool_fetch_verification_email_or_otp(sender_filter: str = "") -> ActionResult:
        res = fetch_verification_email_or_otp(sender_filter=sender_filter)
        content = json.dumps(res, indent=2)
        return ActionResult(extracted_content=content)

    @controller.action("Get stored login credentials or generate autonomous sign-up profile")
    def tool_get_stored_credentials(domain: str) -> ActionResult:
        creds = get_stored_credentials(domain=domain, auto_create_if_missing=True)
        content = json.dumps(creds, indent=2)
        return ActionResult(extracted_content=content)

    @controller.action("Save or update newly created login credentials into vault")
    def tool_save_credentials(domain: str, credentials_json: str) -> ActionResult:
        data = json.loads(credentials_json) if isinstance(credentials_json, str) else credentials_json
        saved = save_credentials(domain, data)
        return ActionResult(extracted_content=f"Saved credentials for {domain}: {saved.get('username')}")

    return controller
