from datetime import datetime, timezone
from pathlib import Path

import pytest

from trustdesk.credentials import fail, issue_credential, ok
from trustdesk.delegation import Scope
from trustdesk.identity import Identity
from trustdesk.policy import ACCEPT, ESCALATE, REFUSE, Evidence, Policy, Request

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]

merchant = Identity.from_seed("Souq Bloom", b"t-merchant")
courier = Identity.from_seed("SwiftDrop", b"t-courier")
mallory = Identity.from_seed("Mallory", b"t-mallory")
DIRECTORY = {"souq_bloom": merchant.did, "swiftdrop": courier.did}

GOOD = {
    "message": [ok("message_signature", "ok"), ok("sender_identity", "ok")],
    "presentation": [ok("presentation_proof", "ok")],
    "authority_chain": [ok("trust_anchor", "ok")],
}
DELEGATED = Scope(actions=["refund.request"], orders=["1042"], max_amount=400, currency="AED")
OWN = Scope(actions=["refund.issue", "order.lookup"], orders=["*"], max_amount=300, currency="AED")


def attestation(issuer=courier, order="1042", status="delivered_damaged"):
    return issue_credential(issuer, subject_did=f"urn:souqbloom:order:{order}", types=["DeliveryAttestation"],
                            claims={"order": order, "status": status}, now=NOW)


@pytest.fixture
def policy():
    return Policy.load(ROOT / "policies" / "support_agent.yaml", DIRECTORY)


def evaluate(policy, amount, *, order="1042", action="refund.request", groups=None, attestations=None,
             vouches=None, delegated=DELEGATED, own=OWN):
    ev = Evidence(
        request=Request(action=action, order=order, amount=amount),
        now=NOW, groups=groups if groups is not None else GOOD,
        delegated_scope=delegated, own_authority=own,
        attestations=attestations if attestations is not None else [attestation()],
        vouches=vouches or [],
    )
    return policy.evaluate(ev)


def test_small_refund_with_evidence_is_accepted(policy):
    d = evaluate(policy, 250)
    assert d.outcome == ACCEPT, d.reason
    assert not d.failed


def test_tiny_refund_needs_no_attestation(policy):
    assert evaluate(policy, 80, attestations=[]).outcome == ACCEPT


def test_above_own_limit_but_within_delegation_escalates(policy):
    d = evaluate(policy, 380)
    assert d.outcome == ESCALATE
    assert "human" in d.reason


def test_above_delegation_is_refused(policy):
    d = evaluate(policy, 5000)
    assert d.outcome == REFUSE
    assert "exceeds delegated limit" in d.reason


def test_other_order_is_refused(policy):
    assert evaluate(policy, 100, order="1043").outcome == REFUSE


def test_any_failed_crypto_check_refuses_and_names_it(policy):
    groups = dict(GOOD, message=[ok("message_signature", "ok"),
                                 fail("sender_identity", "signature does not belong to the claimed sender")])
    d = evaluate(policy, 50, groups=groups)
    assert d.outcome == REFUSE
    assert d.reason.startswith("message.sender_identity")


def test_missing_group_refuses(policy):
    groups = {k: v for k, v in GOOD.items() if k != "authority_chain"}
    assert evaluate(policy, 50, groups=groups).outcome == REFUSE


def test_refund_without_amount_is_refused(policy):
    d = evaluate(policy, 0)
    assert d.outcome == REFUSE
    assert any(c.name == "policy.request_complete" and not c.passed for c in d.trace)


def test_unknown_action_refused(policy):
    assert evaluate(policy, 0, action="account.delete").outcome == REFUSE


def test_no_attestation_above_threshold_escalates(policy):
    d = evaluate(policy, 250, attestations=[])
    assert d.outcome == ESCALATE
    assert "delivery" in d.reason


def test_attestation_for_other_order_does_not_count(policy):
    assert evaluate(policy, 250, attestations=[attestation(order="7777")]).outcome == ESCALATE


def test_attestation_saying_delivered_fine_does_not_support_refund(policy):
    assert evaluate(policy, 250, attestations=[attestation(status="delivered_ok")]).outcome == ESCALATE


def test_untrusted_courier_with_sybil_vouches_is_not_counted(policy):
    fake_courier = Identity.generate("FakeCourier")
    sybils = [Identity.generate(f"sybil{i}") for i in range(20)]
    vouches = [issue_credential(s, subject_did=fake_courier.did, types=["VouchCredential"],
                                claims={"for": "delivery attestations"}, now=NOW) for s in sybils]
    d = evaluate(policy, 250, attestations=[attestation(issuer=fake_courier)], vouches=vouches)
    assert d.outcome == ESCALATE
    note = next(c for c in d.trace if c.name == "evidence.attester_trusted")
    assert "20 valid vouch(es), 0 from trust anchors" in note.detail


def test_courier_vouched_by_enough_anchors_is_trusted():
    second_anchor = Identity.from_seed("Mall Authority", b"t-anchor2")
    spec_dir = dict(DIRECTORY, mall=second_anchor.did)
    import yaml
    spec = yaml.safe_load((ROOT / "policies" / "support_agent.yaml").read_text(encoding="utf-8"))
    spec["trust_anchors"] = ["souq_bloom", "mall"]
    spec["trusted_attesters"] = []
    p = Policy(spec, spec_dir)
    new_courier = Identity.generate("NewCourier")
    vouches = [issue_credential(a, subject_did=new_courier.did, types=["VouchCredential"], now=NOW)
               for a in (merchant, second_anchor)]
    assert evaluate(p, 250, attestations=[attestation(issuer=new_courier)], vouches=vouches).outcome == ACCEPT


def test_forged_attestation_is_rejected(policy):
    """Mallory signs an attestation but claims SwiftDrop issued it."""
    from trustdesk.credentials import add_proof
    vc = attestation(issuer=mallory)
    unsigned = {k: v for k, v in vc.items() if k != "proof"}
    unsigned["issuer"] = courier.did
    forged = add_proof(unsigned, mallory)
    d = evaluate(policy, 250, attestations=[forged])
    assert d.outcome == ESCALATE
    assert any(c.name == "evidence.attestation_valid" and not c.passed for c in d.trace)


def test_agent_without_own_authority_refuses(policy):
    assert evaluate(policy, 50, own=None).outcome == REFUSE


def test_order_lookup_accepted_without_amount(policy):
    delegated = Scope(actions=["order.lookup"], orders=["1042"], max_amount=0, currency="AED")
    assert evaluate(policy, 0, action="order.lookup", delegated=delegated).outcome == ACCEPT


def test_policy_names_unknown_party_fails_loudly():
    with pytest.raises(KeyError):
        Policy.load(ROOT / "policies" / "support_agent.yaml", {"souq_bloom": merchant.did})
