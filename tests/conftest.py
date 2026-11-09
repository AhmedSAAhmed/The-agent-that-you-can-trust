import pytest


@pytest.fixture(autouse=True)
def _no_real_ai_key(monkeypatch):
    """Tests never call a real model or spend the owner's key; the AI reader is tested with fakes."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    for var in ("OPENROUTER_MODEL", "GROQ_API_KEY", "GROQ_MODELS", "GEMINI_API_KEY", "GEMINI_MODELS"):
        monkeypatch.delenv(var, raising=False)
    from trustdesk import reader

    monkeypatch.setitem(reader._COOLDOWN, "until", 0.0)
    monkeypatch.setitem(reader._COOLDOWN, "why", "")
    monkeypatch.setattr(reader, "_PROVIDER_COOLDOWN", {})
