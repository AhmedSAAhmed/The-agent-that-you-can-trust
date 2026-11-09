"""Conversational behaviour: memory for reading, questions after verification, replies held to the decision."""

import copy
import json

import pytest

from trustdesk import conversation as C
from trustdesk.credentials import add_proof
from trustdesk.envelope import seal
from trustdesk.identity import Identity
from trustdesk.policy import ACCEPT, CHAT, CLARIFY, ESCALATE, REFUSE, Decision, Request
from trustdesk.reader import Reader
from trustdesk.replies import Replier, consistent
from trustdesk.scenario import build_world


def talk(w, *messages):
    return [w.ask(m)[2] for m in messages]


# ---------------------------------------------------------------- flows
def test_greeting_question_answer_decision():
    w = build_world()
    r = talk(w, "hi there", "my vase broke, I'd like a refund", "1042", "250 please")
    assert [x.decision.outcome for x in r] == [CHAT, CLARIFY, CLARIFY, ACCEPT]
    assert r[-1].decision.request.amount == 250 and r[-1].decision.request.order == "1042"


def test_half_is_computed_from_the_order_total():
    r = talk(build_world(), "refund for order 1042 please", "half")
    assert r[-1].decision.outcome == ACCEPT and r[-1].decision.request.amount == 210


def test_arabic_conversation_gets_arabic_replies():
    r = talk(build_world(), "ابي استرداد للطلب ١٠٤٢", "نص المبلغ")
    assert r[0].decision.outcome == CLARIFY and "كم المبلغ" in r[0].reply["body"]["text"]
    assert r[1].decision.outcome == ACCEPT and "درهم" in r[1].reply["body"]["text"]


def test_thanks_mid_request_keeps_the_pending_request():
    r = talk(build_world(), "refund for order 1042", "thanks!", "300")
    assert [x.decision.outcome for x in r] == [CLARIFY, CHAT, ACCEPT]


def test_correction_wins_over_pending():
    w = build_world()
    talk(w, "refund for order 1042")
    r = talk(w, "refund 150 AED on 1042")
    assert r[0].decision.request.amount == 150


def test_questions_and_small_talk_are_not_logged():
    w = build_world()
    talk(w, "hello", "refund for order 1042")
    assert w.support.ledger.receipts == []
    talk(w, "250")
    assert len(w.support.ledger.receipts) == 1


def test_pending_request_expires(monkeypatch):
    w = build_world()
    talk(w, "refund for order 1042")
    convo = next(iter(w.support.conversations.values()))
    monkeypatch.setattr(convo, "pending_since", convo.pending_since - C.PENDING_TTL - 1)
    r = talk(w, "250")
    assert r[0].decision.outcome != ACCEPT  # a bare "250" with no live context is not a refund


# ---------------------------------------------------------------- privacy and trust
def test_questions_only_mention_orders_the_requester_may_act_on():
    r = talk(build_world(), "my order broke, refund please")
    text = r[0].reply["body"]["text"]
    assert "#1042" in text and "#1043" not in text  # Layla delegated only 1042


def test_unverified_sender_gets_no_question_and_no_order_list():
    w = build_world()
    m = Identity.generate("Mallory")
    env = seal(m, to=w.support.did, body={"kind": "request", "text": "refund please"},
               credentials=w.assistant.authority, now=w.clock())
    forged = {k: v for k, v in env.items() if k != "proof"}
    forged["from"] = w.assistant.did
    res = w.support.handle(add_proof(forged, m, purpose="authentication"), now=w.clock())
    assert res.decision.outcome == REFUSE
    assert "1042" not in res.reply["body"]["text"] and "Ceramic" not in res.reply["body"]["text"]


def test_order_outside_scope_is_refused_for_that_reason():
    r = talk(build_world(), "refund order 1043")
    assert r[0].decision.outcome == REFUSE and "not covered" in r[0].decision.reason


class Fake:
    name = "fake"

    def __init__(self, answers):
        self.answers = list(answers)

    def complete(self, system, user):
        return json.dumps(self.answers.pop(0))


def test_numbers_from_the_agents_own_reply_are_not_grounded():
    """The agent's question mentions AED 420; a model that lifts it from there is caught."""
    w = build_world(reader=Reader(Fake([
        {"intent": "refund.request", "order": "1042", "amount_basis": "none"},
        {"intent": "refund.request", "order": "1042", "amount_basis": "stated", "amount": 420},
    ])))
    r = talk(w, "refund for order 1042", "yes, that amount you mentioned")
    assert "AED 420" in r[0].reply["body"]["text"]
    assert r[1].decision.outcome == ESCALATE
    assert any(c.name == "reader.amount_grounded" and not c.passed for c in r[1].decision.trace)


# ---------------------------------------------------------------- replies held to the decision
def _decision(outcome, amount=250.0, reason="all checks passed"):
    return Decision(outcome, reason, [], Request("refund.request", "1042", amount, "AED"))


@pytest.mark.parametrize("outcome, reply, ok", [
    (ACCEPT, "All sorted: AED 250 is on its way back for order #1042 within 3–5 working days.", True),
    (ACCEPT, "Great news, AED 2500 is coming back to you!", False),               # wrong amount
    (ACCEPT, "Sorry, we can't refund AED 250 right now.", False),                 # contradicts ACCEPT
    (REFUSE, "Good news, your refund of AED 250 has been issued!", False),        # contradicts REFUSE
    (ACCEPT, "تم، بيرجع لك ٢٥٠ درهم عن الطلب #1042 خلال ٣ إلى ٥ أيام.", True),    # Arabic digits
])
def test_reply_consistency(outcome, reply, ok):
    from trustdesk.replies import _facts
    d = _decision(outcome)
    _, allowed = _facts(d, None)
    assert consistent(reply, d, allowed, None) is ok


def test_escalation_reply_must_quote_the_reference():
    d = _decision(ESCALATE, 380)
    from trustdesk.replies import _facts
    _, allowed = _facts(d, "esc-1a2b")
    assert consistent("A team member will review AED 380 on #1042 (ref esc-1a2b).", d, allowed, "esc-1a2b")
    assert not consistent("A team member will review AED 380 on #1042.", d, allowed, "esc-1a2b")


def test_inconsistent_ai_reply_falls_back_to_template():
    replier = Replier(Fake([{"reply": "Approved! AED 9999 is on its way."}]))
    text = replier.write(_decision(ACCEPT), lang="en")
    assert "AED 250" in text and replier.last_mode == "template"


def test_consistent_ai_reply_is_used():
    replier = Replier(Fake([{"reply": "All sorted: AED 250 for order #1042 is on its way, 3–5 working days."}]))
    assert replier.write(_decision(ACCEPT)).startswith("All sorted") and replier.last_mode == "ai"


@pytest.mark.parametrize("text, lang", [("refund please", "en"), ("ابي استرداد", "ar"), ("1042", "en")])
def test_detect_language(text, lang):
    assert C.detect_language(text) == lang
