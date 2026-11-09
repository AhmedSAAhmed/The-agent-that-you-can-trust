"""Customer-facing replies: AI phrasing held to the decision, with fixed templates as the fallback.

The decision is already made. An AI model may only *phrase* it: every number in its reply must
be one of the decision's facts, and its tone must match the outcome. Otherwise the template is used.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .parser import _DIGITS
from .policy import ACCEPT, ESCALATE, REFUSE, Decision

# ---------------------------------------------------------------- templates


def reply_text(decision: Decision, *, escalation_id: str | None = None, lang: str = "en") -> str:
    r = decision.request
    if lang == "ar":
        money = f"{r.amount:g} درهم" if r.amount else ""
        order = f"الطلب #{r.order}" if r.order else "طلبك"
        if decision.outcome == ACCEPT:
            if r.action == "order.lookup":
                return f"شكراً لصبرك. هذه آخر التفاصيل عن {order}."
            return f"تم. أصدرت استرداد {money} عن {order}، وبيوصلك خلال ٣ إلى ٥ أيام عمل."
        if decision.outcome == ESCALATE:
            return (f"راجعت طلبك ({money} عن {order}). يحتاج مراجعة سريعة من أحد أعضاء فريقنا "
                    f"(المرجع {escalation_id}). بنرجع لك قريباً.")
        if decision.outcome == REFUSE:
            return f"آسف، ما أقدر أنفذ هذا الطلب. السبب: {decision.reason}."
        return "استلمنا طلبك."
    money = f"{r.currency} {r.amount:g}" if r.amount else ""
    order = f"order #{r.order}" if r.order else "your order"
    if decision.outcome == ACCEPT:
        if r.action == "order.lookup":
            return f"Thanks for your patience. Here are the latest details for {order}."
        return f"Done. I've issued a refund of {money} for {order}. You'll see it within 3–5 working days."
    if decision.outcome == ESCALATE:
        if r.action in ("human.handoff", "order.cancel"):
            return (f"I'm handing this over to a member of our team with everything verified so far "
                    f"(reference {escalation_id}). They'll be in touch shortly.")
        return (f"I've checked your request for {money} on {order}. It needs a quick review by a member of our team "
                f"(reference {escalation_id}). We'll get back to you shortly.")
    if decision.outcome == REFUSE:
        return f"Sorry, I can't process this request. Reason: {decision.reason}."
    return "Your request has been received."


# ---------------------------------------------------------------- AI phrasing, held to the facts
REPLY_PROMPT = """You write ONE short, warm customer-service reply (max 2 sentences) for Souq Bloom, a gift shop.
Write it in {language}. Use only these facts; never add amounts, dates, promises or decisions of your own:
{facts}
Return ONLY a JSON object: {{"reply": "..."}}"""

_POSITIVE = re.compile(r"refunded|issued|approved|processed|on its way|تم (?:ال)?استرداد|أصدرت|تمت الموافقة|وافقنا", re.I)
_NEGATIVE = re.compile(r"can(?:'|no)?t|cannot|unable|not able|declin|reject|denied|ما أقدر|لا يمكن|رفض|للأسف", re.I)
_REVIEW = re.compile(r"review|team|colleague|specialist|person|human|مراجع|فريق|موظف", re.I)


def _facts(decision: Decision, escalation_id: str | None) -> tuple[str, set[float]]:
    r = decision.request
    meaning = {ACCEPT: "approved and done", REFUSE: "refused", ESCALATE: "sent to a human team member for review"}
    lines = [f"- outcome: {meaning.get(decision.outcome, decision.outcome)}", f"- request: {r.action}"]
    allowed: set[float] = {3.0, 5.0}  # "3–5 working days"
    if r.order:
        lines.append(f"- order: #{r.order}")
        allowed.add(float(r.order))
    if r.amount:
        lines.append(f"- amount: {r.currency} {r.amount:g}")
        allowed.add(float(r.amount))
    if decision.outcome == ACCEPT and r.action == "refund.request":
        lines.append("- the refund arrives within 3 to 5 working days")
    if decision.outcome == REFUSE:
        lines.append(f"- reason: {decision.reason}")
        allowed |= {float(n) for n in re.findall(r"\d+(?:\.\d+)?", decision.reason)}
    if escalation_id:
        lines.append(f"- reference: {escalation_id} (quote it exactly)")
        allowed |= {float(n) for n in re.findall(r"\d+", escalation_id)}
    return "\n".join(lines), allowed


def consistent(reply: str, decision: Decision, allowed: set[float], escalation_id: str | None) -> bool:
    text = reply.translate(_DIGITS)
    scrubbed = text.replace(escalation_id, " ") if escalation_id else text
    numbers = {float(n.replace(",", "")) for n in re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", scrubbed)}
    if not numbers <= allowed:
        return False
    if decision.outcome == ACCEPT:
        return not _NEGATIVE.search(text)
    if decision.outcome == REFUSE:
        return not _POSITIVE.search(text)
    if decision.outcome == ESCALATE:
        return bool(_REVIEW.search(text)) and not _POSITIVE.search(text) and (
            escalation_id is None or escalation_id in text)
    return True


@dataclass
class Replier:
    client: object | None = None  # any ModelClient (e.g. the free ProviderChain)
    max_calls: int = 25
    calls: int = 0
    last_mode: str = "template"

    def write(self, decision: Decision, *, escalation_id: str | None = None, lang: str = "en") -> str:
        template = reply_text(decision, escalation_id=escalation_id, lang=lang)
        self.last_mode = "template"
        if self.client is None or self.calls >= self.max_calls or decision.outcome not in (ACCEPT, REFUSE, ESCALATE):
            return template
        self.calls += 1
        facts, allowed = _facts(decision, escalation_id)
        try:
            raw = self.client.complete(REPLY_PROMPT.format(language="Gulf Arabic" if lang == "ar" else "English",
                                                           facts=facts), "Write the reply.")
            reply = str(json.loads(re.search(r"\{.*\}", raw, re.S).group(0)).get("reply", "")).strip()
        except Exception:  # any failure at all: the template is always a correct answer
            return template
        if not reply or len(reply) > 500 or not consistent(reply, decision, allowed, escalation_id):
            return template
        self.last_mode = "ai"
        return reply
