import pytest


@pytest.fixture(autouse=True)
def _no_real_ai_key(monkeypatch):
    """Tests never call a real model or spend the owner's key; the AI reader is tested with fakes."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    from trustdesk import reader

    monkeypatch.setitem(reader._COOLDOWN, "until", 0.0)
    monkeypatch.setitem(reader._COOLDOWN, "why", "")
