# 04_ui - Gradio trust-decision interface

One job: Make the trust decision visible and explainable in 90 seconds.

## Inputs
- Working (this run): `stages/03_agents_demo/output/check.md`
- Reference (every run): `PLAN.md` (sections 1 and 2)

Do NOT load: other stages' notes, or later stages' code.

## Process
1. If an input is missing, or the previous `check.md` is not `pass`, stop and say which.
2. `app.py` tabs: Chat (free text -> decision trace), Trust Profiles, Grant / Scope / Revoke, Escalations inbox, Attack Lab, Verify any credential, Architecture
3. Per-session state so visitors don't collide

## Outputs
- Code under `src/trustdesk/` and `tests/` (see AGENTS.md, deliberate break)
- `output/notes.md`: decisions made, anything cut

## Check
Run `uv run pytest tests/test_app_smoke.py -q`. Write `output/check.md`: first line `pass` or `fail: <why>`.
