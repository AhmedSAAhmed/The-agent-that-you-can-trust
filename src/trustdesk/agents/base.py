"""Shared agent plumbing: an identity, a signed action history and a replay guard."""

from __future__ import annotations

from datetime import datetime

from ..envelope import ReplayGuard, seal
from ..identity import Identity
from ..ledger import Ledger

CHAIN_TYPES = {"CustomerCredential", "DelegationCredential", "AuthorityCredential", "SupervisorCredential"}


class Agent:
    def __init__(self, identity: Identity):
        self.identity = identity
        self.ledger = Ledger(identity)
        self.guard = ReplayGuard()

    @property
    def did(self) -> str:
        return self.identity.did

    @property
    def name(self) -> str:
        return self.identity.name

    def send(self, to: str, body: dict, *, credentials: list[dict] | None = None,
             now: datetime | None = None, nonce: str | None = None) -> dict:
        return seal(self.identity, to=to, body=body, credentials=credentials, now=now, nonce=nonce)


def types_of(vc: dict) -> set[str]:
    return set(vc.get("type", []))


def order_chain(credentials: list[dict]) -> list[dict]:
    """Arrange authority credentials root-first by following parentCredential links."""
    chain_creds = [c for c in credentials if types_of(c) & CHAIN_TYPES]
    by_parent = {c.get("credentialSubject", {}).get("parentCredential"): c for c in chain_creds}
    ids = {c.get("id") for c in chain_creds}
    roots = [c for c in chain_creds if c.get("credentialSubject", {}).get("parentCredential") not in ids]
    if not roots:
        return chain_creds
    chain, node = [roots[0]], roots[0]
    while node.get("id") in by_parent and len(chain) <= len(chain_creds):
        node = by_parent[node["id"]]
        chain.append(node)
    return chain
