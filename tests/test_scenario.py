from trustdesk.ledger import verify_history
from trustdesk.policy import ACCEPT, ESCALATE, REFUSE
from trustdesk.scenario import build_world


def test_dids_are_stable_across_worlds():
    assert build_world().support.did == build_world().support.did


def test_mutual_trust_handshake():
    w = build_world()
    checks = w.assistant.verify_counterparty(w.support.introduce(w.assistant.did))
    assert all(c.passed for c in checks), [str(c) for c in checks if not c.passed]


def test_small_refund_is_accepted_and_recorded():
    w = build_world()
    parsed, env, res = w.ask("Hi, I'm Layla's assistant. Order 1042 arrived with broken vases, please refund AED 250.")
    assert res.decision.outcome == ACCEPT, res.decision.reason
    assert res.receipt["outcome"] == ACCEPT
    assert res.reply["body"]["outcome"] == ACCEPT
    assert "refund of AED 250" in res.reply["body"]["text"]
    assert verify_history(w.support.ledger.receipts, w.support.did).passed


def test_mid_refund_escalates_then_supervisor_approves():
    w = build_world()
    _, _, res = w.ask("Refund AED 380 for order 1042")
    assert res.decision.outcome == ESCALATE
    esc, checks, receipt = w.decide(res.escalation.id, approved=True, note="photo confirms damage")
    assert all(c.passed for c in checks)
    assert esc.status == "approved"
    assert receipt["details"]["decided_by"] == w.supervisor.did
    assert verify_history(w.support.ledger.receipts, w.support.did).passed


def test_supervisor_can_decline():
    w = build_world()
    _, _, res = w.ask("Refund AED 380 for order 1042")
    esc, _, receipt = w.decide(res.escalation.id, approved=False)
    assert esc.status == "declined" and receipt["outcome"] == "DECLINED"


def test_escalation_cannot_be_approved_twice():
    w = build_world()
    _, _, res = w.ask("Refund AED 380 for order 1042")
    w.decide(res.escalation.id, approved=True)
    _, checks, receipt = w.decide(res.escalation.id, approved=True)
    assert receipt is None
    assert any(c.name == "approval_target" and not c.passed for c in checks)


def test_forged_approval_is_rejected():
    from trustdesk.identity import Identity
    from trustdesk.agents.support import Supervisor
    w = build_world()
    _, _, res = w.ask("Refund AED 380 for order 1042")
    mallory = Supervisor(Identity.generate("Mallory"), w.supervisor.credential)  # stolen credential, wrong key
    approval = mallory.sign_decision(res.escalation.id, approved=True)
    _, checks, receipt = w.support.resolve(res.escalation.id, approval, w.supervisor.credential)
    assert receipt is None
    assert any(not c.passed for c in checks)


def test_revocation_takes_effect_and_reinstating_restores():
    w = build_world()
    w.revoke("delegation")
    assert w.ask("Refund AED 250 for order 1042")[2].decision.outcome == REFUSE
    w.reinstate("delegation")
    assert w.ask("Refund AED 250 for order 1042")[2].decision.outcome == ACCEPT


def test_merchant_revoking_its_own_agent_stops_all_refunds():
    w = build_world()
    w.revoke("support_authority")
    res = w.ask("Refund AED 50 for order 1042")[2]
    assert res.decision.outcome == REFUSE
    assert "not authorized" in res.decision.reason


def test_rescoping_lowers_the_limit():
    w = build_world()
    w.redelegate(max_amount=200, orders=["1042"])
    assert w.ask("Refund AED 250 for order 1042")[2].decision.outcome == REFUSE
    assert w.ask("Refund AED 150 for order 1042")[2].decision.outcome == ACCEPT


def test_missing_evidence_escalates():
    w = build_world()
    assert w.ask("Refund AED 250 for order 1042", include_evidence=False)[2].decision.outcome == ESCALATE


def test_arabic_request_works_end_to_end():
    w = build_world()
    assert w.ask("ابي استرداد ٢٥٠ درهم للطلب ١٠٤٢")[2].decision.outcome == ACCEPT
