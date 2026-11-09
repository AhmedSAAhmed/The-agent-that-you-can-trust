# 03_agents_demo - agents, scenario, attacks, CLI

One job: Run the Souq Bloom world end to end with real signed messages between agents.

## Inputs
- Working (this run): `stages/02_trust_logic/output/check.md`
- Reference (every run): `PLAN.md` (section 2: cast, outcomes, Attack Lab)

Do NOT load: other stages' notes, or later stages' code.

## Process
1. If an input is missing, or the previous `check.md` is not `pass`, stop and say which.
2. `agents/`: base, support, assistant, courier, mallory
3. `scenario.py`: seeds every DID, credential and status list
4. `attacks.py`: the 9 Attack Lab cases
5. `python -m trustdesk.demo`: prints the 3 outcomes and the 9 attacks with traces

## Outputs
- Code under `src/trustdesk/` and `tests/` (see AGENTS.md, deliberate break)
- `output/notes.md`: decisions made, anything cut

## Check
Run `uv run pytest tests/test_scenario.py tests/test_attacks.py -q`. Write `output/check.md`: first line `pass` or `fail: <why>`.
