"""Layla's personal AI assistant, acting on her behalf through a delegation."""

from __future__ import annotations

from datetime import datetime

from ..credentials import CheckResult, fail, ok, utcnow, verify_presentation
from ..delegation import verify_chain
from ..envelope import verify_envelope
from ..identity import Identity
from ..parser import ParsedRequest
from ..policy import Request
from .base import Agent, order_chain


class AssistantAgent(Agent):
    def __init__(self, identity: Identity, *, authority: list[dict], merchant_did: str, status_registry):
        super().__init__(identity)
        self.authority = authority  # [CustomerCredential (merchant -> Layla), DelegationCredential (Layla -> me)]
        self.merchant_did = merchant_did  # learned from Layla's signed order receipt
        self.registry = status_registry
        self.evidence: list[dict] = []  # e.g. the courier's delivery attestation

    def verify_counterparty(self, hello: dict, *, now: datetime | None = None) -> list[CheckResult]:
        """Before sharing anything: is this really Souq Bloom's support agent?"""
        now = now or utcnow()
        checks = [CheckResult(f"message.{c.name}", c.passed, c.detail)
                  for c in verify_envelope(hello, expected_to=self.did, guard=self.guard, now=now)]
        vp = hello.get("presentation")
        if not isinstance(vp, dict):
            return checks + [fail("counterparty", "the agent presented no credentials")]
        report = verify_presentation(vp, challenge=str(hello.get("nonce", "")), domain=self.did, now=now,
                                     status_registry=self.registry)
        checks += [CheckResult(f"presentation.{c.name}", c.passed, c.detail) for c in report.checks]
        chain = verify_chain(order_chain(vp.get("verifiableCredential") or []), trust_anchors={self.merchant_did},
                             holder=str(hello.get("from", "")), now=now, status_registry=self.registry)
        checks += [CheckResult(f"authority.{c.name}", c.passed, c.detail) for c in chain.checks]
        serves = chain.scope is not None and "refund.issue" in chain.scope.actions
        checks.append(ok("counterparty", "authorized by Souq Bloom to handle refunds") if serves and chain.passed
                      else fail("counterparty", "not an agent Souq Bloom authorized to handle refunds"))
        return checks

    def request(self, to: str, *, text: str, parsed: ParsedRequest | None = None, request: Request | None = None,
                include_evidence: bool = True, now: datetime | None = None, extra_credentials: list[dict] | None = None) -> dict:
        req = request or (parsed.to_request() if parsed and parsed.intent else None)
        body: dict = {"kind": "request", "text": text}
        if req:
            body["request"] = {"action": req.action, "order": req.order, "amount": req.amount, "currency": req.currency}
        creds = list(self.authority) + (self.evidence if include_evidence else []) + (extra_credentials or [])
        env = self.send(to, body, credentials=creds, now=now)
        self.ledger.append(body.get("request", {}).get("action", "message"), outcome="SENT", counterparty=to,
                           details={"text": text[:200]}, now=now)
        return env
