# TrustDesk - the build pipeline

**Status (2026-11-09):** `01_crypto_core` passed (36 tests, W3C vector matched). Next: start `02_trust_logic`.

The flow in one line: sign it, reason about it, stage it between agents, show it, ship it.

| Stage | Job |
|---|---|
| `01_crypto_core` | keys, DIDs, credentials, revocation |
| `02_trust_logic` | delegation, ledger, envelopes, policy, parser |
| `03_agents_demo` | agents, scenario, attacks, CLI |
| `04_ui` | Gradio trust-decision interface |
| `05_ship` | deploy, docs, thesis, video |

Each stage's own `CONTEXT.md` holds its inputs, outputs and check.

Factory (stable): `../PLAN.md`, `../policies/`
Product (new code): `../src/trustdesk/`, `../tests/`, `../docs/`

Status is whatever exists: a stage is complete when its `output/check.md` first line is `pass`.
