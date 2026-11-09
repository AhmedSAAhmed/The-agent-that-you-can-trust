"""Conversation state for the support agent: memory for *reading*, never for trusting.

- Memory holds only what the customer wrote. The agent's own replies are never used to
  ground numbers, so nothing the agent says can be turned into an amount.
- A half-finished request (e.g. a refund with no amount yet) waits as `pending` while the
  agent asks a clarifying question; the customer's answer completes it.
- Every completed request is still a fresh, signed, fully verified message, decided by policy.
- History arrives only through the agent's own record of signed messages. A "transcript" pasted
  inside a message is just text: it can't grant approvals.
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field

from .parser import _DIGITS, ParsedRequest

_FRACTIONS = {0.5: r"\bhalf\b|50\s*%|نص|نصف", 0.25: r"\bquarter\b|25\s*%|ربع"}
_FULL = r"\b(full|whole|entire|all of it|everything)\b|كامل|كل المبلغ"

_ARABIC = re.compile(r"[؀-ۿ]")
PENDING_TTL = 15 * 60  # seconds a half-finished request waits for the customer's answer


def detect_language(text: str) -> str:
    letters = re.findall(r"[A-Za-z؀-ۿ]", text)
    if not letters:
        return "en"
    return "ar" if sum(bool(_ARABIC.match(c)) for c in letters) / len(letters) > 0.3 else "en"


@dataclass
class Conversation:
    customer_texts: deque = field(default_factory=lambda: deque(maxlen=4))
    pending: dict = field(default_factory=dict)  # intent / order / amount / currency waiting for completion
    pending_since: float = 0.0
    last_question: str = ""
    lang: str = "en"

    def context(self) -> list[str]:
        """Earlier customer messages (oldest first), for reading only."""
        return list(self.customer_texts)

    def note_customer(self, text: str) -> None:
        self.lang = detect_language(text) if text.strip() else self.lang
        self.customer_texts.append(text)

    def merge(self, parsed: ParsedRequest) -> ParsedRequest:
        """Fill what this message left out from the pending request. New details win (corrections)."""
        if not self.pending or time.time() - self.pending_since > PENDING_TTL:
            self.pending = {}
            return parsed
        if parsed.intent is None or parsed.intent == self.pending.get("intent"):
            parsed.intent = parsed.intent or self.pending.get("intent")
            if parsed.order is None:
                parsed.order = self.pending.get("order")
            if parsed.amount is None:
                parsed.amount = self.pending.get("amount")
            parsed.notes.append("completed using details from earlier in this conversation")
        return parsed

    def answer_slots(self, parsed: ParsedRequest, text: str, orders: dict[str, dict]) -> ParsedRequest:
        """Read a short answer to our own question: a bare number, 'half' or 'full' becomes the amount.

        Only used while a question is pending, and only on the customer's own words.
        """
        if not self.pending or parsed.amount is not None or parsed.intent != "refund.request":
            return parsed
        clean = text.translate(_DIGITS).lower()
        total = orders.get(parsed.order or "", {}).get("total")
        for frac, pattern in _FRACTIONS.items():
            if total and re.search(pattern, clean):
                parsed.amount = round(total * frac, 2)
                return parsed
        if total and re.search(_FULL, clean):
            parsed.amount = float(total)
            return parsed
        numbers = [n for n in re.findall(r"\d+(?:\.\d+)?", clean) if n != parsed.order]
        if len(numbers) == 1:
            parsed.amount = float(numbers[0])
        return parsed

    def hold(self, parsed: ParsedRequest, question: str) -> None:
        self.pending = {"intent": parsed.intent, "order": parsed.order, "amount": parsed.amount,
                        "currency": parsed.currency}
        self.pending_since = time.time()
        self.last_question = question

    def clear(self) -> None:
        self.pending, self.last_question = {}, ""


def missing_slots(parsed: ParsedRequest) -> list[str]:
    if parsed.intent is None:
        return ["intent"]
    if parsed.intent == "refund.request":
        return [s for s, v in (("order", parsed.order), ("amount", parsed.amount)) if not v]
    if parsed.intent == "order.lookup" and not parsed.order:
        return ["order"]
    return []


def clarifying_question(missing: list[str], parsed: ParsedRequest, allowed_orders: dict[str, dict], lang: str) -> str:
    """Ask for exactly what's missing. Only orders the requester is authorized for are mentioned."""
    listing = ", ".join(f"#{oid} ({o['item']}, AED {o['total']:g})" for oid, o in allowed_orders.items())
    ar_listing = "، ".join(f"#{oid} ({o['item']}، {o['total']:g} درهم)" for oid, o in allowed_orders.items())
    if "intent" in missing:
        if parsed.order and parsed.order not in allowed_orders:
            return (f"آسف على اللي صار. للأسف ما أقدر أساعد في هذا الطلب ضمن الصلاحية الحالية، لكن أقدر أساعدك في: {ar_listing}."
                    if lang == "ar" else
                    f"Sorry to hear that. That order isn't covered by the authority you presented; I can help with {listing}.")
        return ("آسف على اللي صار! كيف أقدر أساعدك؟ أقدر أرتب استرداد مبلغ، أو أتحقق من الطلب، أو أحولك لأحد من فريقنا."
                if lang == "ar" else
                "Sorry to hear that! How can I help? I can arrange a refund, check the order, or connect you with our team.")
    if "order" in missing:
        if lang == "ar":
            return f"أي طلب تقصد؟ الطلبات اللي أقدر أساعدك فيها: {ar_listing}." if allowed_orders else "ممكن تعطيني رقم الطلب؟"
        return f"Which order is this about? I can help with {listing}." if allowed_orders else "Could you share the order number?"
    order = allowed_orders.get(parsed.order or "", {})
    total = order.get("total")
    if lang == "ar":
        tail = f" أو المبلغ كامل ({total:g} درهم)" if total else ""
        return f"كم المبلغ اللي تبي تسترده للطلب #{parsed.order}؟ تقدر تكتب مبلغ، أو «النص»{tail}."
    tail = f", or 'the full amount' (AED {total:g})" if total else ""
    return f"How much would you like refunded for order #{parsed.order}? You can give an amount, 'half'{tail}."


def smalltalk_reply(text: str, lang: str) -> str:
    t = text.lower()
    if lang == "ar":
        if re.search(r"شكر|مشكور|يعطيك", text):
            return "العفو! إذا احتجت أي شي ثاني بخصوص طلباتك، أنا موجود."
        return "أهلاً وسهلاً! أنا مساعد خدمة عملاء سوق بلوم. كيف أقدر أساعدك اليوم؟"
    if re.search(r"thank|thx|cheers|appreciate", t):
        return "You're welcome! If anything else comes up with your orders, I'm here."
    if re.search(r"\b(bye|goodbye|see you)\b", t):
        return "Take care! Your orders and requests stay on record if you need us again."
    return "Hi! I'm Souq Bloom's support assistant. How can I help with your order today?"
