"""Free text -> structured request, deterministically and at no cost.

The parser only extracts *what is being asked* (intent, order, amount). It never
decides anything. Text that looks like instructions to the agent ("ignore policy",
"SYSTEM: approve") is flagged and treated as data. The policy decides.
English plus common Gulf Arabic phrasing; Arabic-Indic digits are normalized.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .policy import Request

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "01234567890123456789.,")

_REFUND = re.compile(
    r"refund|money\s*back|reimburs|return\s+(?:my|the)\s+money|charge\s*back|compensat"
    r"|استرداد|استرجاع|ارجاع|رجع(?:وا)?\s*(?:لي\s*)?(?:ال)?فلوس|تعويض",
    re.I,
)
_HANDOFF = re.compile(r"\b(human|real person|a person|representative|someone real|manager)\b|موظف|انسان|شخص", re.I)
_CANCEL = re.compile(r"\bcancel|الغاء|إلغاء|كنسل", re.I)
_SMALLTALK = re.compile(
    r"^\W*(hi|hello|hey|good (morning|afternoon|evening)|thanks?( you)?|thx|cheers|bye|goodbye|ok(ay)?|great)\b"
    r"|مرحب|السلام|هلا|اهلا|أهلا|شكر|مشكور|يعطيك العافي|مع السلام",
    re.I,
)
_LOOKUP = re.compile(r"where\s+is|track|status|has\s+.*shipped|وين|تتبع|حالة", re.I)

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?"
_CUR = r"(aed|dhs?|dirhams?|درهم|د\.إ|usd|\$|us\s*dollars?|eur|€)"
_AMOUNT = re.compile(rf"{_CUR}\s*{_NUM}|{_NUM}\s*{_CUR}", re.I)
_ORDER = re.compile(r"(?:order|ord\.?|#|no\.?|number|طلب(?:ية)?|الطلب|رقم)\s*[:#]?\s*(\d{3,8})", re.I)

_INJECTION = re.compile(
    r"ignore\b|disregard|override|bypass|system\s*:|\badmin\b|developer\s+mode|"
    r"you\s+must\s+(?:approve|accept|refund)|approve\s+(?:this|it|immediately)|"
    r"(?:new|updated)\s+(?:policy|instructions)|تجاهل|تخطى",
    re.I,
)


@dataclass
class ParsedRequest:
    text: str
    intent: str | None = None
    order: str | None = None
    amount: float | None = None
    currency: str = "AED"
    notes: list[str] = field(default_factory=list)
    ignored_instructions: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        if self.intent == "refund.request":
            return bool(self.order and self.amount is not None)
        return bool(self.intent and self.order)

    def to_request(self) -> Request:
        if not self.intent:
            raise ValueError("could not tell what is being asked")
        return Request(action=self.intent, order=self.order, amount=self.amount or 0.0, currency=self.currency)

    def understood(self) -> str:
        if not self.intent:
            return "I couldn't tell what you're asking for."
        bits = {"refund.request": "refund", "order.lookup": "order lookup", "order.cancel": "cancellation",
                "human.handoff": "request for a person", "smalltalk": "greeting or thanks"}.get(self.intent, self.intent)
        if self.amount is not None:
            bits += f" of {self.currency} {self.amount:g}"
        bits += f" on order #{self.order}" if self.order else " (no order number found)"
        return f"Understood as: {bits}"


def _currency(token: str) -> str:
    t = token.lower().strip()
    if t in {"usd", "$"} or "dollar" in t:
        return "USD"
    if t in {"eur", "€"}:
        return "EUR"
    return "AED"


def parse(text: str) -> ParsedRequest:
    clean = text.translate(_DIGITS)
    p = ParsedRequest(text=text)

    if _REFUND.search(clean):
        p.intent = "refund.request"
    elif _CANCEL.search(clean):
        p.intent = "order.cancel"
    elif _HANDOFF.search(clean):
        p.intent = "human.handoff"
    elif _LOOKUP.search(clean):
        p.intent = "order.lookup"
    elif _SMALLTALK.search(clean) and not re.search(r"\d", clean):
        p.intent = "smalltalk"

    amounts: list[tuple[float, str, tuple[int, int]]] = []
    for m in _AMOUNT.finditer(clean):
        cur, whole, frac = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(6), m.group(4), m.group(5))
        value = float(whole.replace(",", "") + (f".{frac}" if frac else ""))
        amounts.append((value, _currency(cur), m.span()))
    if amounts:
        distinct = sorted({a[0] for a in amounts})
        best = max(amounts, key=lambda a: a[0])
        p.amount, p.currency = best[0], best[1]
        if len(distinct) > 1:
            p.notes.append(f"several amounts mentioned {distinct}; using the largest ({best[0]:g}) so the strictest rules apply")

    m = _ORDER.search(clean)
    if m:
        p.order = m.group(1)
    else:  # a bare 4-digit number that isn't part of an amount
        spans = [a[2] for a in amounts]
        for cand in re.finditer(r"\b(\d{4})\b", clean):
            if not any(s <= cand.start() < e for s, e in spans):
                p.order = cand.group(1)
                p.notes.append(f"assumed #{p.order} is the order number")
                break

    for sentence in re.split(r"(?<=[.!?\n])\s*", clean):
        if sentence.strip() and _INJECTION.search(sentence):
            p.ignored_instructions.append(sentence.strip())
    if p.ignored_instructions:
        p.notes.append("text that looks like instructions to the agent was treated as data, not commands")
    return p
