# 90-second video script

Record at **https://huggingface.co/spaces/SalQ/trustdesk**, browser at about 1400 px wide, light mode (`?__theme=light`).
**Before recording:** open the page fresh, so you start with an empty chat and one new world.

| Time | Screen | Say (roughly) |
|---|---|---|
| 0:00–0:10 | Hero | "Agents will negotiate and transact for us. TrustDesk is a trust layer for them, and it has no scores. Trust here is signed evidence plus a policy you can read." |
| 0:10–0:25 | Live desk: click the **first example** (AED 250), Send | "Layla's personal assistant asks Souq Bloom's support agent for a refund. It presents W3C credentials: Souq Bloom says Layla owns the order, Layla delegated to her assistant, and the courier attests the vase arrived broken. Every check passes, so: accepted." |
| 0:25–0:45 | Click the **AED 380** example, Send. Point at the tile row | "380 is within what Layla delegated, 400, but above the support agent's *own* authority of 300. So it doesn't guess; it escalates, and the trace says exactly why." |
| 0:45–0:55 | Escalations tab → **Approve (sign)** | "Noura approves. Her decision is signed too, and checked against her own supervisor credential." |
| 0:55–1:10 | Live desk → **⛔ Layla revokes her assistant**, send the AED 250 example again | "Layla revokes her assistant. Same request, now refused: the delegation's bit is flipped in Layla's signed revocation list." |
| 1:10–1:25 | Attack Lab → **Run all 9** | "Nine attacks: impersonation, forged and tampered credentials, replay, Sybil vouches, prompt injection, a phishing bot. Each one is stopped by a named check." |
| 1:25–1:30 | How it works tab | "Identity, claims, verification, policy, built on DIDs, Verifiable Credentials and the W3C test vectors. Link's below." |

**Tips:** rehearse once without recording; it's fine to talk over a click while the result loads. If you go over 90 seconds, cut the approval step (0:45–0:55) first.
