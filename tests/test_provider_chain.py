"""The free provider chain, with the network faked: no real keys, no real calls."""

import io
import json
import urllib.error

import pytest

from trustdesk import reader as R
from trustdesk.reader import ChainUnavailable, Provider, ProviderChain, Reader

ORDERS = {"1042": {"item": "Ceramic vase set + peonies", "total": 420}}
GOOD = json.dumps({"intent": "refund.request", "order": "1042", "amount_basis": "stated", "amount": 250,
                   "currency": "AED", "summary": "", "suspicious_instructions": []})


class FakeNet:
    """Replaces urllib.request.urlopen; answers per (host, model) from a script."""

    def __init__(self, script):
        self.script, self.calls = script, []

    def __call__(self, req, timeout=None):
        body = json.loads(req.data)
        host = req.full_url.split("/")[2]
        model = body.get("model") or ",".join(body.get("models", []))
        self.calls.append((host, model, dict(req.header_items()), body))
        outcome = self.script.get((host, model), self.script.get(host, "ok"))
        if isinstance(outcome, int):
            payload = {"error": {"message": "Rate limit exceeded: free-models-per-day"}} if outcome == 429 else {}
            raise urllib.error.HTTPError(req.full_url, outcome, "err", {"retry-after": "120"},
                                         io.BytesIO(json.dumps(payload).encode()))
        content = GOOD if outcome == "ok" else outcome
        return io.BytesIO(json.dumps({"model": model, "choices": [{"message": {"content": content}}]}).encode())


def chain():
    return ProviderChain([
        Provider("Groq", "https://api.groq.com/openai/v1/chat/completions", "gsk_x", ["m-a", "m-b"]),
        Provider("Gemini", "https://gemini.example/v1/chat/completions", "AIza_x", ["g-1"]),
        Provider("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", "sk-or-x", ["o-1:free", "o-2:free"],
                 send_model_list=True),
    ])


def install(monkeypatch, script):
    net = FakeNet(script)
    monkeypatch.setattr(R.urllib.request, "urlopen", net)
    return net


def test_first_provider_answers(monkeypatch):
    net = install(monkeypatch, {})
    c = chain()
    assert json.loads(c.complete("s", "u"))["amount"] == 250
    assert len(net.calls) == 1 and c.name == "Groq · m-a"


def test_rate_limited_model_falls_through_and_is_skipped_next_time(monkeypatch):
    net = install(monkeypatch, {("api.groq.com", "m-a"): 429})
    c = chain()
    c.complete("s", "u")
    assert [m for _, m, *_ in net.calls] == ["m-a", "m-b"]
    net.calls.clear()
    c.complete("s", "u")  # m-a is cooling down: not called again
    assert [m for _, m, *_ in net.calls] == ["m-b"]


def test_rejected_key_skips_whole_provider(monkeypatch):
    net = install(monkeypatch, {"api.groq.com": 403})
    c = chain()
    c.complete("s", "u")
    assert [h for h, *_ in net.calls] == ["api.groq.com", "gemini.example"]
    assert c.name.startswith("Gemini")


def test_openrouter_receives_its_model_list(monkeypatch):
    net = install(monkeypatch, {"api.groq.com": 429, "gemini.example": 500})
    c = chain()
    c.complete("s", "u")
    host, models, headers, body = net.calls[-1]
    assert host == "openrouter.ai" and body["models"] == ["o-1:free", "o-2:free"]


def test_every_request_sends_a_user_agent(monkeypatch):
    net = install(monkeypatch, {})
    chain().complete("s", "u")
    headers = {k.lower(): v for k, v in net.calls[0][2].items()}
    assert headers["user-agent"].startswith("TrustDesk/")


def test_all_down_raises_and_reader_explains(monkeypatch):
    install(monkeypatch, {"api.groq.com": 429, "gemini.example": 429, "openrouter.ai": 429})
    c = chain()
    with pytest.raises(ChainUnavailable):
        c.complete("s", "u")
    r = Reader(c).read("refund AED 250 for order 1042", ORDERS)
    assert r.mode == "rules" and "rate-limited" in r.checks[0].detail
    assert r.parsed.amount == 250  # rules still read it


def test_empty_answer_falls_through(monkeypatch):
    install(monkeypatch, {("api.groq.com", "m-a"): "", ("api.groq.com", "m-b"): ""})
    c = chain()
    c.complete("s", "u")
    assert c.name.startswith("Gemini")


def test_from_env_builds_only_configured_providers(monkeypatch):
    assert ProviderChain.from_env() is None
    monkeypatch.setenv("GEMINI_API_KEY", "“AIza-test”")
    monkeypatch.setenv("GEMINI_MODELS", "gemini-x, gemini-y")
    c = ProviderChain.from_env()
    assert [p.name for p in c.providers] == ["Gemini"]
    assert c.providers[0].models == ["gemini-x", "gemini-y"] and c.providers[0].key == "AIza-test"


def test_from_env_orders_groq_first(monkeypatch):
    for var in ("OPENROUTER_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.setenv(var, "k-" + var)
    assert [p.name for p in ProviderChain.from_env().providers] == ["Groq", "Gemini", "OpenRouter"]


def test_bad_key_characters_refused(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_te​st")
    with pytest.raises(ValueError):
        ProviderChain.from_env()
