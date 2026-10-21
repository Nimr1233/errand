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
    from errand import gemini, memory
    monkeypatch.setattr(memory, 'CMD', [])
    monkeypatch.setattr(gemini, 'load_key', lambda: None)
    monkeypatch.setattr(gemini, 'USAGE_FILE', tmp_path / 'gemini_usage.json')
