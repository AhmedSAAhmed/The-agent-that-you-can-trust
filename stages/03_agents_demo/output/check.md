pass

`uv run pytest tests/test_scenario.py tests/test_attacks.py -q` → 22 passed (2026-11-09). Full suite: 111 passed.
`uv run python -m trustdesk.demo` shows the handshake, ACCEPT (AED 250), ESCALATE (AED 380) followed by a signed approval, REFUSE after revocation, and all 9 attacks defended.
