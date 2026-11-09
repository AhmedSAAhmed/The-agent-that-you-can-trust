"""Tamper-evident action history: signed, hash-chained receipts.

Each receipt is signed by the agent that acted and commits to the hash of the
previous receipt. Editing, deleting or reordering any past entry breaks every
later link. This is the "history of actions" in a trust profile: evidence,
not a score.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime

import jcs

from .credentials import CheckResult, add_proof, fail, iso, ok, utcnow, verify_proof
from .identity import Identity, controller_of

GENESIS = "0" * 64


def receipt_hash(receipt: dict) -> str:
    return hashlib.sha256(jcs.canonicalize(receipt)).hexdigest()


@dataclass
class Ledger:
    owner: Identity
    receipts: list[dict] = field(default_factory=list)

    @property
    def head(self) -> str:
        return receipt_hash(self.receipts[-1]) if self.receipts else GENESIS

    def append(
        self,
        action: str,
        *,
        outcome: str,
        counterparty: str = "",
        details: dict | None = None,
        now: datetime | None = None,
    ) -> dict:
        body = {
            "type": "ActionReceipt",
            "seq": len(self.receipts),
            "prev": self.head,
            "actor": self.owner.did,
            "action": action,
            "outcome": outcome,
            "counterparty": counterparty,
            "details": details or {},
            "timestamp": iso(now or utcnow()),
        }
        receipt = add_proof(body, self.owner, created=body["timestamp"])
        self.receipts.append(receipt)
        return receipt


def verify_history(receipts: list[dict], owner_did: str) -> CheckResult:
    name = "history"
    prev = GENESIS
    for i, r in enumerate(receipts):
        if r.get("seq") != i:
            return fail(name, f"receipt {i} is out of sequence (missing or reordered entry)")
        if r.get("prev") != prev:
            return fail(name, f"receipt {i} does not link to receipt {i - 1} (history was edited)")
        if r.get("actor") != owner_did:
            return fail(name, f"receipt {i} names a different actor")
        proof = verify_proof(r, purpose="assertionMethod")
        if not proof.passed:
            return fail(name, f"receipt {i}: {proof.detail}")
        if controller_of(r["proof"]["verificationMethod"]) != owner_did:
            return fail(name, f"receipt {i} was not signed by its actor")
        prev = receipt_hash(r)
    return ok(name, f"{len(receipts)} signed receipt(s), hash chain intact")


def summarize(receipts: list[dict]) -> dict:
    """Counts by outcome, for the trust-profile card. Facts, not a score."""
    counts: dict[str, int] = {}
    for r in receipts:
        counts[r.get("outcome", "?")] = counts.get(r.get("outcome", "?"), 0) + 1
    return counts
