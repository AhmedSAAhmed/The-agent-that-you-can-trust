---
title: TrustDesk
emoji: 🛡️
colorFrom: indigo
colorTo: green
sdk: gradio
sdk_version: 6.31.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: A trust layer for AI agents (DIDs + Verifiable Credentials)
---

# TrustDesk: the agent that earns trust

A trust layer for AI agents: decentralized identifiers (DIDs), W3C Verifiable Credentials, revocation, scoped delegation and explainable policy. The demo is a DOO-style customer-support agent for a fictional shop, **Souq Bloom**. It decides whether to **accept, refuse or escalate** refund requests sent by other AI agents, and shows the reason for every check.

> Status: under construction. See [PLAN.md](PLAN.md).

## Run locally

```bash
git clone https://github.com/AhmedSAAhmed/The-agent-that-you-can-trust.git
cd The-agent-that-you-can-trust
uv sync
uv run python app.py
```

Tests: `uv run pytest -q`

## License

MIT
