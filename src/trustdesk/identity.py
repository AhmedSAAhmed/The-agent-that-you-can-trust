"""Agent identity: Ed25519 key pairs and the W3C `did:key` method.

A `did:key` is self-certifying: the DID *is* the public key (multicodec
`ed25519-pub` 0xed01, base58btc, multibase prefix `z`). Anyone can verify a
signature from the DID string alone. No registry or network call is needed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import base58
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

ED25519_PUB = b"\xed\x01"  # multicodec varint for ed25519-pub
ED25519_PRIV = b"\x80\x26"  # multicodec varint for ed25519-priv (0x1300)
DID_KEY_PREFIX = "did:key:"


class DIDError(ValueError):
    """A DID or verification method could not be parsed or resolved."""


def _raw_public(pub: Ed25519PublicKey) -> bytes:
    return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def multibase_public(pub: Ed25519PublicKey) -> str:
    return "z" + base58.b58encode(ED25519_PUB + _raw_public(pub)).decode()


def decode_multibase_public(value: str) -> Ed25519PublicKey:
    if not value.startswith("z"):
        raise DIDError("public key must be multibase base58btc (prefix 'z')")
    try:
        raw = base58.b58decode(value[1:])
    except ValueError as exc:
        raise DIDError(f"invalid base58: {exc}") from exc
    if not raw.startswith(ED25519_PUB) or len(raw) != 34:
        raise DIDError("not an Ed25519 multikey")
    return Ed25519PublicKey.from_public_bytes(raw[2:])


@dataclass
class Identity:
    """A named key pair. `name` is a display label only; trust never relies on it."""

    name: str
    _private: Ed25519PrivateKey = field(repr=False)

    # ---- construction ----
    @classmethod
    def generate(cls, name: str) -> "Identity":
        return cls(name, Ed25519PrivateKey.generate())

    @classmethod
    def from_seed(cls, name: str, seed: bytes) -> "Identity":
        """Deterministic key for reproducible demo worlds. Never use a guessable seed in production."""
        return cls(name, Ed25519PrivateKey.from_private_bytes(hashlib.sha256(seed).digest()))

    @classmethod
    def from_secret_multibase(cls, name: str, secret: str) -> "Identity":
        raw = base58.b58decode(secret.removeprefix("z"))
        if not raw.startswith(ED25519_PRIV) or len(raw) != 34:
            raise DIDError("not an Ed25519 secret multikey")
        return cls(name, Ed25519PrivateKey.from_private_bytes(raw[2:]))

    # ---- properties ----
    @property
    def public_key(self) -> Ed25519PublicKey:
        return self._private.public_key()

    @property
    def public_multibase(self) -> str:
        return multibase_public(self.public_key)

    @property
    def did(self) -> str:
        return DID_KEY_PREFIX + self.public_multibase

    @property
    def verification_method(self) -> str:
        return f"{self.did}#{self.public_multibase}"

    # ---- crypto ----
    def sign(self, data: bytes) -> bytes:
        return self._private.sign(data)

    def verify(self, data: bytes, signature: bytes) -> bool:
        return verify_signature(self.public_key, data, signature)


def verify_signature(pub: Ed25519PublicKey, data: bytes, signature: bytes) -> bool:
    try:
        pub.verify(signature, data)
        return True
    except InvalidSignature:
        return False


def public_key_from_did(did: str) -> Ed25519PublicKey:
    if not did.startswith(DID_KEY_PREFIX):
        raise DIDError(f"unsupported DID method: {did.split(':')[1] if ':' in did else did!r}")
    return decode_multibase_public(did[len(DID_KEY_PREFIX):])


def public_key_from_verification_method(vm: str) -> Ed25519PublicKey:
    """Resolve `did:key:z…#z…`. The fragment must name the DID's own key."""
    did, _, fragment = vm.partition("#")
    key = public_key_from_did(did)
    if fragment and fragment != did[len(DID_KEY_PREFIX):]:
        raise DIDError("verification method fragment does not match the DID's key")
    return key


def controller_of(vm: str) -> str:
    return vm.partition("#")[0]


def did_document(did: str) -> dict:
    """Resolve a did:key into its DID Document (W3C DID Core + Multikey)."""
    key = public_key_from_did(did)
    mb = multibase_public(key)
    vm_id = f"{did}#{mb}"
    return {
        "@context": ["https://www.w3.org/ns/did/v1", "https://w3id.org/security/multikey/v1"],
        "id": did,
        "verificationMethod": [
            {"id": vm_id, "type": "Multikey", "controller": did, "publicKeyMultibase": mb}
        ],
        "authentication": [vm_id],
        "assertionMethod": [vm_id],
        "capabilityDelegation": [vm_id],
        "capabilityInvocation": [vm_id],
    }
