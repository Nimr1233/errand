import os

import pytest

# The room, server and connector tests drive the demo engine; the real engine has its own tests
# (test_engine.py) with a fake site and a fake brain. Set before errand.server is imported, and
# passed on to the `errand start` the room tests launch.
os.environ.setdefault('ERRAND_DEMO', '1')


@pytest.fixture(autouse=True)
def no_real_memory_or_gemini(monkeypatch, tmp_path):
    """No test ever writes into your real gbrain or spends your real Gemini allowance: test_memory.py
    and test_gemini.py bring their own stand-ins."""
    from errand import gemini, memory, phone, store, telegram
    monkeypatch.setattr(phone, 'FILE', tmp_path / 'phone.json')  # never touches your real phone PIN
    from errand import inbox
    monkeypatch.setattr(inbox, 'CONFIG', tmp_path / 'inbox.json')  # or your inbox secret
    from errand import exports
    monkeypatch.setattr(exports, 'CONFIG', tmp_path / 'exports.json')  # or posts to your Slack and Notion
    for name in ('TOKEN_FILE', 'CHAT_FILE', 'PAIR_FILE'):  # and never messages you through your real bot
        monkeypatch.setattr(telegram, name, tmp_path / name.lower())
    monkeypatch.setattr(memory, 'CMD', [])
    monkeypatch.setattr(store, 'DB', tmp_path / 'errand.db')  # and never touches your saved jobs
    monkeypatch.setattr(store, 'CACHE', tmp_path / 'cache')
    monkeypatch.setattr(gemini, 'load_key', lambda: None)
    monkeypatch.setattr(gemini, 'USAGE_FILE', tmp_path / 'gemini_usage.json')
