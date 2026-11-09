# 03_agents_demo - notes

## Built
- `agents/base.py`: `Agent` (identity, ledger, replay guard, `send`), `order_chain` (root-first by parentCredential).
- `agents/support.py`: `SupportAgent.handle(env)` builds the check groups `message`, `presentation` (+ `holder_is_sender`) and `authority_chain`, then evaluates the policy, records a receipt, creates an `Escalation` if needed, and sends a signed reply. `introduce()` sends its AuthorityCredential for the mutual check. `resolve()` applies a `Supervisor`'s signed `EscalationDecision` (signature, approver identity, target, SupervisorCredential chain + scope).
- `agents/assistant.py`: `verify_counterparty(hello)` (refuses to talk to agents not authorized by Souq Bloom); `request()` attaches the chain + courier evidence.
- `agents/courier.py`: signs `DeliveryAttestation`s.
- `scenario.py`: `build_world()` creates a fresh, seeded world (stable DIDs). Helpers: `ask`, `decide`, `revoke`/`reinstate` ('delegation' | 'support_authority'), `redelegate`, `name_of`.
- `attacks.py`: 9 attacks; `run_attack(id)` → `AttackResult(outcome, caught_by, detail, trace, defended)`.
- `replies.py`: reply templates. `demo.py`: CLI (`--verbose` prints full traces).

## For the UI (stage 04)
Keep one `World` per Gradio session (`gr.State(build_world)`). Decision trace = `HandleResult.decision.trace`; escalations = `world.support.escalations`; trust profile = credentials + `ledger.receipts` + `verify_history`.

## Decisions
- A supervisor approval is a signed document checked against a merchant-issued SupervisorCredential (limit AED 5000), so even the human step is verifiable.
- Re-scoping issues a new delegation and revokes the old one, instead of mutating it.
- `World.clock()` uses real time, so signatures and the freshness window behave as they would live.

## Cut
None.
