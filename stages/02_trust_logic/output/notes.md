# 02_trust_logic - notes

## Built
- `delegation.py`: `Scope` (actions, orders, maxAmount, currency) in `credentialSubject.scope`. `delegate()` refuses to widen authority; `verify_chain()` checks each link's VC, `trust_anchor`, `chain_links`, `attenuation` (scope and expiry only narrow) and `holder_is_delegate`, then returns the leaf scope and the principal.
- `ledger.py`: signed, hash-chained `ActionReceipt`s; `verify_history` detects edits, deletions, reordering, and even re-signing by the owner.
- `envelope.py`: `seal()` signs a message (nonce, timestamp, recipient) and embeds a VP bound to challenge=nonce, domain=recipient. `verify_envelope` returns `message_signature`, `sender_identity`, `recipient`, `freshness` and `replay`. Forged messages don't consume the real nonce.
- `policy.py` + `policies/support_agent.yaml`: `Evidence` (pre-run check groups, delegated scope, own authority, raw attestations/vouches) → `Decision(outcome, reason, trace)`. Order: action rule → must_pass groups (REFUSE) → scope (REFUSE) → delivery evidence above AED 100 (ESCALATE) → own authority limit (ESCALATE above it).
- `parser.py`: deterministic intent/order/amount/currency extraction (English + Gulf Arabic, Arabic-Indic digits). Injection-like sentences are flagged; with several amounts it uses the largest.

## How stage 03 should use it
The support agent runs `verify_envelope` → group `message`; `verify_presentation` → group `presentation` (including per-credential results); `verify_chain` → group `authority_chain`. It passes the attestations/vouches carried in the VP to `Evidence`, then calls `Policy.evaluate`, and on ACCEPT/ESCALATE appends a ledger receipt.

## Decisions
- Vouches are counted only when issued by trust anchors (no weights, no score). Sybil vouches stay visible in the trace but never count.
- The agent's auto-approve limit comes from its *own* AuthorityCredential, so the merchant can lower it by reissuing the credential, without editing code.

## Cut
None.
