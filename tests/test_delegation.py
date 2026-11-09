import copy
from datetime import datetime, timedelta, timezone

import pytest

from trustdesk.credentials import add_proof, issue_credential
from trustdesk.delegation import (
    Scope,
    delegate,
    scope_allows,
    verify_chain,
)
from trustdesk.identity import Identity
from trustdesk.status_list import StatusList, StatusRegistry

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def world():
    merchant = Identity.from_seed("Souq Bloom", b"t-merchant")
    layla = Identity.from_seed("Layla", b"t-layla")
    assistant = Identity.from_seed("Layla's Assistant", b"t-assistant")
    registry = StatusRegistry()
    m_list = StatusList(merchant, "https://souqbloom.example/status/1")
    l_list = StatusList(layla, "https://layla.example/status/1")
    root_scope = Scope(actions=["refund.request", "order.lookup"], orders=["1042", "1043"], max_amount=420, currency="AED")
    root_idx = m_list.allocate()
    root = issue_credential(
        merchant, subject_did=layla.did, types=["CustomerCredential"],
        claims={"scope": root_scope.to_dict()}, status=m_list.entry(root_idx),
        valid_until=NOW + timedelta(days=365), now=NOW,
    )
    child_idx = l_list.allocate()
    child = delegate(
        layla, parent=root, delegate_did=assistant.did,
        scope=Scope(actions=["refund.request"], orders=["1042"], max_amount=400, currency="AED"),
        valid_until=NOW + timedelta(days=7), status=l_list.entry(child_idx), now=NOW,
    )
    registry.publish(m_list.to_credential(now=NOW))
    registry.publish(l_list.to_credential(now=NOW))
    return dict(merchant=merchant, layla=layla, assistant=assistant, root=root, child=child,
                registry=registry, l_list=l_list, child_idx=child_idx)


def by_name(results):
    return {r.name: r for r in results}


def run(world, chain=None, anchors=None, holder=None):
    return verify_chain(
        chain or [world["root"], world["child"]],
        trust_anchors=anchors if anchors is not None else {world["merchant"].did},
        holder=holder or world["assistant"].did,
        now=NOW, status_registry=world["registry"],
    )


def test_valid_chain_passes_and_yields_leaf_scope(world):
    result = run(world)
    assert result.passed, [str(c) for c in result.checks]
    assert result.scope.orders == ["1042"]
    assert result.scope.max_amount == 400
    assert result.principal == world["layla"].did


def test_scope_subset_rules():
    parent = Scope(actions=["a", "b"], orders=["1"], max_amount=100, currency="AED")
    assert Scope(actions=["a"], orders=["1"], max_amount=50, currency="AED").is_subset_of(parent)
    assert not Scope(actions=["c"], orders=["1"], max_amount=50, currency="AED").is_subset_of(parent)
    assert not Scope(actions=["a"], orders=["2"], max_amount=50, currency="AED").is_subset_of(parent)
    assert not Scope(actions=["a"], orders=["1"], max_amount=500, currency="AED").is_subset_of(parent)
    assert not Scope(actions=["a"], orders=["1"], max_amount=50, currency="USD").is_subset_of(parent)
    wildcard = Scope(actions=["a"], orders=["*"], max_amount=100, currency="AED")
    assert Scope(actions=["a"], orders=["9"], max_amount=10, currency="AED").is_subset_of(wildcard)
    assert not wildcard.is_subset_of(parent)


def test_delegate_refuses_to_widen_scope(world):
    with pytest.raises(ValueError):
        delegate(world["layla"], parent=world["root"], delegate_did=world["assistant"].did,
                 scope=Scope(actions=["refund.request"], orders=["1042"], max_amount=4000, currency="AED"), now=NOW)


def test_hand_built_escalated_child_is_caught(world):
    """Layla (or anyone) signs a child that bypasses delegate()'s guard."""
    child = copy.deepcopy(world["child"])
    child["credentialSubject"]["scope"]["maxAmount"] = 4000
    child = add_proof({k: v for k, v in child.items() if k != "proof"}, world["layla"])
    assert by_name(run(world, chain=[world["root"], child]).checks)["attenuation"].passed is False


def test_tampered_child_breaks_signature(world):
    child = copy.deepcopy(world["child"])
    child["credentialSubject"]["scope"]["maxAmount"] = 4000
    result = run(world, chain=[world["root"], child])
    assert not result.passed
    assert any(c.name.endswith("proof") and not c.passed for c in result.checks)


def test_untrusted_root_fails(world):
    assert by_name(run(world, anchors=set()).checks)["trust_anchor"].passed is False


def test_self_issued_root_fails(world):
    mallory = Identity.generate("Mallory")
    fake_root = issue_credential(
        mallory, subject_did=mallory.did, types=["CustomerCredential"],
        claims={"scope": Scope(actions=["refund.request"], orders=["*"], max_amount=99999, currency="AED").to_dict()},
        now=NOW,
    )
    result = run(world, chain=[fake_root], holder=mallory.did)
    assert by_name(result.checks)["trust_anchor"].passed is False


def test_broken_link_fails(world):
    """A delegation issued by someone who is not the parent's subject."""
    mallory = Identity.generate("Mallory")
    rogue = issue_credential(
        mallory, subject_did=world["assistant"].did, types=["DelegationCredential"],
        claims={"scope": world["child"]["credentialSubject"]["scope"], "parentCredential": world["root"]["id"]},
        now=NOW,
    )
    assert by_name(run(world, chain=[world["root"], rogue]).checks)["chain_links"].passed is False


def test_holder_must_be_leaf_subject(world):
    mallory = Identity.generate("Mallory")
    assert by_name(run(world, holder=mallory.did).checks)["holder_is_delegate"].passed is False


def test_revoked_delegation_fails(world):
    world["l_list"].revoke(world["child_idx"])
    world["registry"].publish(world["l_list"].to_credential(now=NOW))
    result = run(world)
    assert not result.passed
    assert any("revoked" in c.detail for c in result.checks if not c.passed)


def test_child_cannot_outlive_parent(world):
    child = issue_credential(
        world["layla"], subject_did=world["assistant"].did, types=["DelegationCredential"],
        claims={"scope": world["child"]["credentialSubject"]["scope"], "parentCredential": world["root"]["id"]},
        valid_until=NOW + timedelta(days=9999), now=NOW,
    )
    assert by_name(run(world, chain=[world["root"], child]).checks)["attenuation"].passed is False


def test_scope_allows():
    s = Scope(actions=["refund.request"], orders=["1042"], max_amount=400, currency="AED")
    assert scope_allows(s, "refund.request", "1042", 250, "AED").passed
    assert not scope_allows(s, "refund.request", "1043", 250, "AED").passed
    assert not scope_allows(s, "refund.request", "1042", 401, "AED").passed
    assert not scope_allows(s, "order.cancel", "1042", 0, "AED").passed
    assert not scope_allows(s, "refund.request", "1042", 100, "USD").passed
