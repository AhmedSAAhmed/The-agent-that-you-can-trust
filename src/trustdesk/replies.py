"""Customer-facing reply wording. Templates only; the decision is already made."""

from __future__ import annotations

from .policy import ACCEPT, ESCALATE, REFUSE, Decision


def reply_text(decision: Decision, *, escalation_id: str | None = None) -> str:
    r = decision.request
    money = f"{r.currency} {r.amount:g}" if r.amount else ""
    order = f"order #{r.order}" if r.order else "your order"
    if decision.outcome == ACCEPT:
        if r.action == "order.lookup":
            return f"Thanks for your patience. Here are the latest details for {order}."
        return f"Done. I've issued a refund of {money} for {order}. You'll see it within 3–5 working days."
    if decision.outcome == ESCALATE:
        return (f"I've checked your request for {money} on {order}. It needs a quick review by a member of our team "
                f"(reference {escalation_id}). We'll get back to you shortly.")
    if decision.outcome == REFUSE:
        return f"Sorry, I can't process this request. Reason: {decision.reason}."
    return "Your request has been received."
