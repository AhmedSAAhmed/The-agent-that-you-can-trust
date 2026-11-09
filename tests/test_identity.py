import pytest

from trustdesk.identity import (
    DIDError,
    Identity,
    did_document,
    public_key_from_did,
    public_key_from_verification_method,
)

# W3C vc-di-eddsa, Appendix B.3 (Example 29)
W3C_PUBLIC = "z6MkrJVnaZkeFzdQyMZu1cgjg7k1pZZ6pvBQ7XJPt4swbTQ2"
W3C_SECRET = "z3u2en7t5LR2WtQH5PfFqMqwVHBeXouLzo6haApm8XHqvjxq"


def test_generated_identity_has_ed25519_did_key():
    ident = Identity.generate("alice")
    assert ident.did.startswith("did:key:z6Mk")
    assert ident.verification_method == f"{ident.did}#{ident.did.removeprefix('did:key:')}"


def test_w3c_secret_key_derives_w3c_public_key():
    ident = Identity.from_secret_multibase("w3c", W3C_SECRET)
    assert ident.public_multibase == W3C_PUBLIC
    assert ident.did == f"did:key:{W3C_PUBLIC}"


def test_did_round_trips_to_public_key():
    ident = Identity.generate("bob")
    pub = public_key_from_did(ident.did)
    sig = ident.sign(b"hello")
    pub.verify(sig, b"hello")  # raises on failure


def test_seeded_identity_is_deterministic():
    a = Identity.from_seed("souq-bloom", b"demo-seed")
    b = Identity.from_seed("souq-bloom", b"demo-seed")
    c = Identity.from_seed("souq-bloom", b"other-seed")
    assert a.did == b.did
    assert a.did != c.did


def test_signature_from_other_key_fails():
    alice, mallory = Identity.generate("alice"), Identity.generate("mallory")
    sig = mallory.sign(b"refund")
    assert not alice.verify(b"refund", sig)
    assert alice.verify(b"refund", alice.sign(b"refund"))


@pytest.mark.parametrize(
    "bad",
    [
        "did:web:example.com",
        "did:key:",
        "did:key:6MkrJVnaZkeFzdQyMZu1cgjg7k1pZZ6pvBQ7XJPt4swbTQ2",  # missing multibase prefix
        "did:key:zQ3shokFTS3brHcDQrn82RUDfCZESWL1ZdCEJwekUDPQiYBme",  # secp256k1, not Ed25519
        "did:key:z111",
    ],
)
def test_invalid_dids_are_rejected(bad):
    with pytest.raises(DIDError):
        public_key_from_did(bad)


def test_verification_method_must_match_its_did():
    ident = Identity.generate("x")
    other = Identity.generate("y")
    with pytest.raises(DIDError):
        public_key_from_verification_method(f"{ident.did}#{other.public_multibase}")


def test_did_document_shape():
    ident = Identity.generate("carol")
    doc = did_document(ident.did)
    assert doc["id"] == ident.did
    vm = doc["verificationMethod"][0]
    assert vm["type"] == "Multikey"
    assert vm["controller"] == ident.did
    assert vm["publicKeyMultibase"] == ident.public_multibase
    for rel in ("authentication", "assertionMethod", "capabilityDelegation", "capabilityInvocation"):
        assert doc[rel] == [vm["id"]]
