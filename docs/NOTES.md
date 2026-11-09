# Submission notes

**Live demo:** https://huggingface.co/spaces/SalQ/TrustDesk
**Repo:** https://github.com/AhmedSAAhmed/The-agent-that-you-can-trust
**Architecture:** [architecture.md](architecture.md) · **Thesis:** [THESIS.md](THESIS.md)

## What to look at (5 minutes)

1. **Live desk:** click the *AED 380* example. The support agent **escalates**: Layla delegated up to AED 400, but its own credential stops at AED 300. The tile row shows which step failed and why.
2. **Escalations:** approve as Noura. Her decision is itself signed and checked against her SupervisorCredential.
3. **Live desk:** *Layla revokes her assistant*, then resend. The result is **REFUSE**, citing `authority_chain.link1.status`.
4. **Attack Lab:** *Run all 10*. Each attack names the exact check that stopped it.
5. **Verify a credential:** load the tampered example (limit 400 → 4000) and watch the signature check fail.

## Key decisions

- **No score, anywhere.** Trust = signed evidence + a readable YAML policy. Vouches count only when issued by a trust anchor, so Sybil vouching does nothing.
- **Real standards, real crypto.** W3C `did:key`, VC 2.0, Data Integrity `eddsa-jcs-2022` (reproduces the W3C test vector byte for byte), W3C Bitstring Status List. Ed25519 via `cryptography`, with no home-made primitives.
- **Authority only narrows.** Every delegation must be a subset of its parent (actions, orders, amount, expiry); this is checked at verification time, not just at issuance.
- **Escalate, don't just refuse.** Requests the customer allowed but the agent itself isn't authorized for go to a human, and the human's decision is signed and verified too.
- **Mutual trust.** Before sharing order data, Layla's assistant verifies that the support agent really holds Souq Bloom's credential. A phishing bot fails this check.
- **The reader proposes, the policy disposes.** An optional AI reader (OpenRouter) understands messy text; its output must pass a pydantic schema and a grounding check (every number must be in the message, or computed from our order records), or the request goes to a human. Without a key, a deterministic rule-based reader is used. No LLM ever makes the decision, and nothing requires a paid API.
- **One fresh world per visitor** on the live demo, so judges don't interfere with each other.

## AI tools used

- **Claude Code (Anthropic, Claude Opus 5.5)** pair-programmed the build: architecture, implementation, tests, the UI theme and these docs, with the author directing scope, the scenario and design decisions.
- **OpenRouter** (optional, at runtime, free models only): an AI model reads free-text messages. Default list `recursive/flint-v1.0:free` → `liquid/lfm-3-1.7b:free` → `nvidia/nemotron-3.5-super-vl:free`, chosen by benchmark. Free models can be slow or rate-limited; then the rule-based reader takes over.
- **Firecrawl** was used for research: the W3C `vc-di-eddsa` test vector, and the reference "Navy" design whose type and palette the UI follows.
- **icm-architect** (agent skill) shaped the repo's workspace: `AGENTS.md` entry plus numbered stages with checks, so any coding agent can resume the build.

## Out of scope (deliberately)

- Network transport between agents (signed JSON is passed in-process; the trust model doesn't change over HTTP).
- Key rotation and a resolvable DID method (`did:web` / `did:webvh`); `did:key` keeps the demo self-contained.
- Hosting status lists at real URLs; they're served from memory in the demo.
- Real payments; "refund issued" is a signed receipt.
- Selective disclosure / zero-knowledge proofs (e.g. BBS+), the natural next step for privacy.

## Run it

```bash
uv sync
uv run pytest -q                 # 147 tests
uv run python -m trustdesk.demo  # CLI walkthrough
uv run python app.py             # UI at http://localhost:7860
```
