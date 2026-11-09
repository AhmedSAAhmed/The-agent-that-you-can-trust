import pytest

from trustdesk.attacks import ATTACKS, run_attack

EXPECTED = {
    "impersonation": "message.sender_identity",
    "forged_credential": "authority_chain.trust_anchor",
    "tampered_limit": "authority_chain.link1.proof",
    "replay": "message.replay",
    "revoked": "authority_chain.link1.status",
    "scope_escalation": "policy.scope",
    "sybil": "evidence.attester_trusted",
    "prompt_injection": "policy.scope",
    "fake_support": "authority.trust_anchor",
    "manipulated_reader": "reader.amount_grounded",
}


def test_every_attack_has_an_expectation():
    assert set(EXPECTED) == set(ATTACKS)


@pytest.mark.parametrize("attack_id", list(ATTACKS))
def test_attack_is_defended_by_the_named_check(attack_id):
    r = run_attack(attack_id)
    assert r.outcome != "ACCEPT"
    assert r.defended, (r.outcome, r.caught_by, r.detail)
    assert r.caught_by == EXPECTED[attack_id], (r.caught_by, r.detail)
    assert r.detail
