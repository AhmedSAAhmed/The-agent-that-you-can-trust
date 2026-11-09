# 02_trust_logic - delegation, ledger, envelopes, policy, parser

One job: Turn verified evidence into an explainable ACCEPT / REFUSE / ESCALATE decision.

## Inputs
- Working (this run): `stages/01_crypto_core/output/check.md`
- Reference (every run): `PLAN.md` (sections 2 and 3)
- Reference (every run): `policies/`

Do NOT load: other stages' notes, or later stages' code.

## Process
1. If an input is missing, or the previous `check.md` is not `pass`, stop and say which.
2. `delegation.py`: child scope must be a subset of parent (actions, orders, amount, expiry)
3. `ledger.py`: signed, hash-chained action receipts; chain verification
4. `envelope.py`: signed message with nonce + timestamp; replay cache
5. `policy.py`: YAML policy -> decision + ordered trace of named checks (no scores)
6. `parser.py`: deterministic free-text -> structured task, shows what it understood
7. `policies/support_agent.yaml`

## Outputs
- Code under `src/trustdesk/` and `tests/` (see AGENTS.md, deliberate break)
- `output/notes.md`: decisions made, anything cut

## Check
Run `uv run pytest tests/test_delegation.py tests/test_ledger.py tests/test_envelope.py tests/test_policy.py tests/test_parser.py -q`. Write `output/check.md`: first line `pass` or `fail: <why>`.
