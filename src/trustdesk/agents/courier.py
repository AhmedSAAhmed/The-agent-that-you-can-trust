"""SwiftDrop, a (fictional) courier whose agent signs delivery attestations."""

from __future__ import annotations

import hashlib
from datetime import datetime

from ..credentials import issue_credential
from .base import Agent


class CourierAgent(Agent):
    def attest(self, order: str, status: str, *, photo: bytes = b"", now: datetime | None = None) -> dict:
        vc = issue_credential(
            self.identity,
            subject_did=f"urn:souqbloom:order:{order}",
            types=["DeliveryAttestation"],
            claims={"order": str(order), "status": status,
                    "photoSha256": hashlib.sha256(photo).hexdigest() if photo else None},
            name=f"Delivery attestation for order #{order}",
            now=now,
        )
        self.ledger.append("delivery.attest", outcome="SIGNED", details={"order": order, "status": status}, now=now)
        return vc
