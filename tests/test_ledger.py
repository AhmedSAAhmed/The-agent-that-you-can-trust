import copy
from datetime import datetime, timezone

from trustdesk.credentials import add_proof
from trustdesk.identity import Identity
from trustdesk.ledger import GENESIS, Ledger, summarize, verify_history

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def make():
    agent = Identity.from_seed("Support Agent", b"t-agent")
    ledger = Ledger(agent)
    ledger.append("refund.issue", outcome="ACCEPT", counterparty="did:key:x", details={"order": "1042", "amount": 250}, now=NOW)
    ledger.append("refund.issue", outcome="ESCALATE", details={"order": "1042", "amount": 380}, now=NOW)
    ledger.append("refund.issue", outcome="REFUSE", details={"reason": "revoked"}, now=NOW)
    return agent, ledger


def test_intact_history_verifies():
    agent, ledger = make()
    assert ledger.receipts[0]["prev"] == GENESIS
    assert verify_history(ledger.receipts, agent.did).passed
    assert summarize(ledger.receipts) == {"ACCEPT": 1, "ESCALATE": 1, "REFUSE": 1}


def test_editing_a_past_receipt_is_detected():
    agent, ledger = make()
    receipts = copy.deepcopy(ledger.receipts)
    receipts[0]["details"]["amount"] = 25  # rewrite history
    assert not verify_history(receipts, agent.did).passed


def test_re_signing_an_edited_receipt_still_breaks_the_chain():
    agent, ledger = make()
    receipts = copy.deepcopy(ledger.receipts)
    edited = {k: v for k, v in receipts[0].items() if k != "proof"}
    edited["outcome"] = "ACCEPT_WITH_BONUS"
    receipts[0] = add_proof(edited, agent)  # even the owner can't silently rewrite
    result = verify_history(receipts, agent.did)
    assert not result.passed
    assert "receipt 1" in result.detail


def test_deleting_a_receipt_is_detected():
    agent, ledger = make()
    receipts = [ledger.receipts[0], ledger.receipts[2]]
    assert not verify_history(receipts, agent.did).passed


def test_receipts_signed_by_someone_else_fail():
    agent, _ = make()
    mallory = Identity.generate("Mallory")
    fake = Ledger(mallory)
    fake.append("refund.issue", outcome="ACCEPT", now=NOW)
    assert not verify_history(fake.receipts, agent.did).passed
