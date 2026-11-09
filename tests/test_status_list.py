import copy
from datetime import datetime, timezone

from trustdesk.credentials import issue_credential, verify_credential
from trustdesk.identity import Identity
from trustdesk.status_list import (
    MIN_BITS,
    StatusList,
    StatusRegistry,
    decode_bitstring,
    encode_bitstring,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
URL = "https://souqbloom.example/status/1"


def setup():
    merchant = Identity.from_seed("Souq Bloom", b"test-merchant")
    holder = Identity.from_seed("Assistant", b"test-assistant")
    sl = StatusList(merchant, URL)
    registry = StatusRegistry()
    idx = sl.allocate()
    vc = issue_credential(
        merchant, subject_did=holder.did, types=["DelegationCredential"],
        claims={"actions": ["refund.request"]}, status=sl.entry(idx), now=NOW,
    )
    registry.publish(sl.to_credential(now=NOW))
    return merchant, sl, registry, idx, vc


def test_bitstring_round_trip_and_bit_order():
    bits = bytearray(MIN_BITS // 8)
    bits[0] = 0b1000_0000  # index 0 is the left-most bit
    encoded = encode_bitstring(bytes(bits))
    assert encoded.startswith("u")  # multibase base64url
    assert decode_bitstring(encoded) == bytes(bits)


def test_list_meets_minimum_size_for_privacy():
    merchant = Identity.generate("m")
    sl = StatusList(merchant, URL)
    assert len(sl.bits) * 8 >= MIN_BITS == 131072


def test_active_credential_passes_status_check():
    _, _, registry, _, vc = setup()
    results = verify_credential(vc, now=NOW, status_registry=registry)
    assert all(r.passed for r in results), results


def test_revoked_credential_fails():
    _, sl, registry, idx, vc = setup()
    sl.revoke(idx)
    registry.publish(sl.to_credential(now=NOW))
    status = {r.name: r for r in verify_credential(vc, now=NOW, status_registry=registry)}["status"]
    assert status.passed is False
    assert "revoked" in status.detail


def test_unknown_status_list_fails_closed():
    _, _, _, _, vc = setup()
    empty = StatusRegistry()
    status = {r.name: r for r in verify_credential(vc, now=NOW, status_registry=empty)}["status"]
    assert status.passed is False


def test_status_list_signed_by_another_issuer_is_rejected():
    _, sl, _, idx, vc = setup()
    mallory = Identity.generate("Mallory")
    fake = StatusList(mallory, URL)  # same URL, all bits zero, Mallory's key
    registry = StatusRegistry()
    sl.revoke(idx)
    registry.publish(fake.to_credential(now=NOW))
    status = {r.name: r for r in verify_credential(vc, now=NOW, status_registry=registry)}["status"]
    assert status.passed is False


def test_tampered_status_list_is_rejected():
    _, sl, registry, idx, vc = setup()
    sl.revoke(idx)
    signed = sl.to_credential(now=NOW)
    tampered = copy.deepcopy(signed)
    clean = StatusList(sl.issuer, URL)
    tampered["credentialSubject"]["encodedList"] = encode_bitstring(bytes(clean.bits))
    registry.publish(tampered)
    status = {r.name: r for r in verify_credential(vc, now=NOW, status_registry=registry)}["status"]
    assert status.passed is False


def test_unrevoke_is_possible_for_suspension_style_flows():
    _, sl, _, idx, _ = setup()
    sl.revoke(idx)
    assert sl.is_set(idx)
    sl.reinstate(idx)
    assert not sl.is_set(idx)
