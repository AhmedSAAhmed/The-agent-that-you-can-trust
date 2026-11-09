# Two-year thesis: agent identity and reputation

By 2028, most commercial requests will be agent-to-agent before any human sees them. The customer's assistant will talk to the merchant's support agent, which talks to the courier's agent. Every one of those hops raises one question: *who is this, and who said they could do that?*

The tempting answer is a reputation score. Wrong primitive. A score compresses evidence into a number that can't be audited, can't be scoped, and is easy to farm: twenty fake accounts vouching for each other look like trust. Scores are a UI, not a foundation.

The foundation is four boring things that already have W3C standards:

1. **Self-certifying identity.** A DID that *is* a key, so a signature proves who spoke without asking a platform.
2. **Scoped, delegated authority.** "Layla's assistant may request a refund on order 1042, up to AED 400, for seven days." Authority must only narrow as it is handed down, and every agent should act within its *own* credential, not its operator's.
3. **Revocation that's instant and public.** Trust you can't withdraw isn't trust.
4. **Evidence over opinion.** Signed receipts of what an agent did, and attestations from parties with something to lose, outweigh any number of anonymous vouches.

On top of that sits **policy**: readable rules that turn verified evidence into accept, refuse or escalate, with the reason written down. The escalation path is the point. Agents should know the edge of their authority and hand that decision to a human, who signs it too.

The winners won't own a reputation database. They'll own the **trust anchors** that businesses already rely on (merchants, banks, couriers, regulators) issuing machine-verifiable credentials. Within two years, "show me your credential chain" will be as routine for an agent as HTTPS is for a website.
