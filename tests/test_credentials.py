import copy
from datetime import datetime, timedelta, timezone

import pytest

from trustdesk.credentials import (
    add_proof,
    create_presentation,
    hash_data,
    issue_credential,
    verify_credential,
    verify_presentation,
    verify_proof,
)
from trustdesk.identity import Identity

# ---------- W3C vc-di-eddsa Appendix B.3 test vector (eddsa-jcs-2022) ----------
W3C_SECRET = "z3u2en7t5LR2WtQH5PfFqMqwVHBeXouLzo6haApm8XHqvjxq"
W3C_DOC = {
    "@context": [
        "https://www.w3.org/ns/credentials/v2",
        "https://www.w3.org/ns/credentials/examples/v2",
    ],
    "id": "urn:uuid:58172aac-d8ba-11ed-83dd-0b3aef56cc33",
    "type": ["VerifiableCredential", "AlumniCredential"],
    "name": "Alumni Credential",
    "description": "A minimum viable example of an Alumni Credential.",
    "issuer": "https://vc.example/issuers/5678",
    "validFrom": "2023-01-01T00:00:00Z",
    "credentialSubject": {"id": "did:example:abcdefgh", "alumniOf": "The School of Examples"},
}
W3C_CREATED = "2023-02-24T23:36:38Z"
W3C_DOC_HASH = "59b7cb6251b8991add1ce0bc83107e3db9dbbab5bd2c28f687db1a03abc92f19"
W3C_PROOF_HASH = "66ab154f5c2890a140cb8388a22a160454f80575f6eae09e5a097cabe539a1db"
W3C_PROOF_VALUE = "z2HnFSSPPBzR36zdDgK8PbEHeXbR56YF24jwMpt3R1eHXQzJDMWS93FCzpvJpwTWd3GAVFuUfjoJdcnTMuVor51aX"


def test_w3c_vector_hashes():
    ident = Identity.from_secret_multibase("w3c", W3C_SECRET)
    proof_config = {
        "type": "DataIntegrityProof",
        "cryptosuite": "eddsa-jcs-2022",
        "created": W3C_CREATED,
        "verificationMethod": ident.verification_method,
        "proofPurpose": "assertionMethod",
        "@context": W3C_DOC["@context"],
    }
    combined = hash_data(W3C_DOC, proof_config)
    assert combined.hex() == W3C_PROOF_HASH + W3C_DOC_HASH


def test_w3c_vector_signature_matches_byte_for_byte():
    ident = Identity.from_secret_multibase("w3c", W3C_SECRET)
    signed = add_proof(W3C_DOC, ident, created=W3C_CREATED)
    assert signed["proof"]["proofValue"] == W3C_PROOF_VALUE
    assert verify_proof(signed).passed


# ---------- our own credentials ----------
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def merchant():
    return Identity.from_seed("Souq Bloom", b"test-merchant")


@pytest.fixture
def agent():
    return Identity.from_seed("Support Agent", b"test-agent")


@pytest.fixture
def vc(merchant, agent):
    return issue_credential(
        merchant,
        subject_did=agent.did,
        types=["AuthorityCredential"],
        claims={"actions": ["refund.issue"], "maxAmount": 300, "currency": "AED"},
        valid_from=NOW - timedelta(days=1),
        valid_until=NOW + timedelta(days=30),
        now=NOW,
    )


def names(results):
    return {r.name: r.passed for r in results}


def test_issued_credential_verifies(vc):
    results = verify_credential(vc, now=NOW)
    assert all(r.passed for r in results), results
    assert vc["issuer"] == vc["proof"]["verificationMethod"].split("#")[0]
    assert vc["@context"][0] == "https://www.w3.org/ns/credentials/v2"


def test_tampered_claim_fails(vc):
    bad = copy.deepcopy(vc)
    bad["credentialSubject"]["maxAmount"] = 4000
    assert names(verify_credential(bad, now=NOW))["proof"] is False


def test_tampered_proof_value_fails(vc):
    bad = copy.deepcopy(vc)
    pv = bad["proof"]["proofValue"]
    bad["proof"]["proofValue"] = pv[:-2] + ("11" if pv[-2:] != "11" else "22")
    assert names(verify_credential(bad, now=NOW))["proof"] is False


def test_missing_proof_fails(vc):
    bad = copy.deepcopy(vc)
    del bad["proof"]
    assert names(verify_credential(bad, now=NOW))["proof"] is False


def test_issuer_swapped_to_someone_else_fails(vc, agent):
    bad = copy.deepcopy(vc)
    bad["issuer"] = agent.did  # claims a different issuer than the key that signed
    r = names(verify_credential(bad, now=NOW))
    assert r["proof"] is False or r["issuer_binding"] is False


def test_attacker_signs_claiming_merchant_issuer(merchant, agent):
    mallory = Identity.generate("Mallory")
    forged = issue_credential(
        mallory, subject_did=agent.did, types=["AuthorityCredential"],
        claims={"maxAmount": 99999}, now=NOW,
    )
    unsigned = {k: v for k, v in forged.items() if k != "proof"}
    unsigned["issuer"] = merchant.did
    resigned = add_proof(unsigned, mallory)
    r = names(verify_credential(resigned, now=NOW))
    assert r["proof"] is True  # signature itself is mathematically valid...
    assert r["issuer_binding"] is False  # ...but it wasn't made by the issuer's key


def test_expired_credential_fails(vc):
    r = names(verify_credential(vc, now=NOW + timedelta(days=31)))
    assert r["validity_period"] is False


def test_not_yet_valid_credential_fails(vc):
    r = names(verify_credential(vc, now=NOW - timedelta(days=2)))
    assert r["validity_period"] is False


def test_proof_context_mismatch_fails(vc):
    bad = copy.deepcopy(vc)
    bad["@context"] = ["https://www.w3.org/ns/credentials/v2"]
    assert names(verify_credential(bad, now=NOW))["proof"] is False


# ---------- presentations ----------
def test_presentation_round_trip(vc, agent):
    vp = create_presentation(agent, [vc], challenge="nonce-123", domain="souqbloom.example")
    report = verify_presentation(vp, challenge="nonce-123", domain="souqbloom.example", now=NOW)
    assert report.passed, report
    assert len(report.credentials) == 1


def test_presentation_wrong_challenge_fails(vc, agent):
    vp = create_presentation(agent, [vc], challenge="nonce-123", domain="souqbloom.example")
    report = verify_presentation(vp, challenge="nonce-999", domain="souqbloom.example", now=NOW)
    assert not report.passed


def test_presentation_signed_by_non_holder_fails(vc, agent):
    mallory = Identity.generate("Mallory")
    vp = create_presentation(mallory, [vc], challenge="n", domain="d")
    vp_unsigned = {k: v for k, v in vp.items() if k != "proof"}
    vp_unsigned["holder"] = agent.did  # pretend to be the agent
    forged = add_proof(vp_unsigned, mallory, purpose="authentication",
                       extra={"challenge": "n", "domain": "d"})
    report = verify_presentation(forged, challenge="n", domain="d", now=NOW)
    assert not report.passed


def test_presentation_with_tampered_inner_credential_fails(vc, agent):
    bad_vc = copy.deepcopy(vc)
    bad_vc["credentialSubject"]["maxAmount"] = 4000
    vp = create_presentation(agent, [bad_vc], challenge="n", domain="d")
    report = verify_presentation(vp, challenge="n", domain="d", now=NOW)
    assert not report.passed
