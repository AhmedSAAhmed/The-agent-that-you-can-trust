"""The DOO-style customer-support agent for Souq Bloom.

It verifies everything an incoming message carries, asks the policy for a
decision, records a signed receipt, and replies. Refunds above its own
authority wait for a human supervisor's signed approval.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from ..credentials import CheckResult, add_proof, fail, issuer_id, ok, utcnow, verify_credential, verify_presentation, verify_proof
from ..delegation import Scope, scope_allows, scope_of, verify_chain
from ..envelope import verify_envelope
from ..identity import Identity, controller_of
from ..conversation import Conversation, clarifying_question, detect_language, missing_slots, smalltalk_reply
from ..parser import ParsedRequest
from ..reader import Reader
from ..policy import ACCEPT, CHAT, CLARIFY, ESCALATE, Decision, Evidence, Policy, Request
from ..replies import Replier
from .base import Agent, order_chain, types_of


@dataclass
class Escalation:
    id: str
    request: Request
    requester: str
    principal: str
    decision: Decision
    status: str = "pending"  # pending | approved | declined
    resolution: list[CheckResult] = field(default_factory=list)


@dataclass
class HandleResult:
    decision: Decision
    reply: dict
    receipt: dict | None
    escalation: Escalation | None = None
    request_text: str = ""


def _explicit_request(body: dict) -> Request | None:
    """A structured request the sender chose to sign into the message (e.g. fields the user edited)."""
    r = body.get("request")
    if not (isinstance(r, dict) and r.get("action")):
        return None
    try:
        return Request(action=str(r["action"]), order=str(r["order"]) if r.get("order") else None,
                       amount=float(r.get("amount") or 0), currency=str(r.get("currency") or "AED"))
    except (TypeError, ValueError):
        return Request(action="malformed")


class SupportAgent(Agent):
    service = "Souq Bloom customer support"

    def __init__(self, identity: Identity, *, authority: dict, policy: Policy, status_registry,
                 orders: dict[str, dict] | None = None, reader: Reader | None = None, replier: Replier | None = None):
        super().__init__(identity)
        self.authority = authority
        self.orders = orders or {}  # the merchant's own order records (item, total)
        self.reader = reader or Reader()
        self.replier = replier or Replier()
        self.conversations: dict[str, Conversation] = {}  # per sender DID
        self.policy = policy
        self.registry = status_registry
        self.escalations: dict[str, Escalation] = {}

    # ---------------------------------------------------------------- outbound
    def introduce(self, to: str, *, now: datetime | None = None) -> dict:
        """Prove who I work for before a customer's agent shares anything with me."""
        return self.send(to, {"kind": "hello", "service": self.service}, credentials=[self.authority], now=now)

    def own_authority(self, now: datetime) -> Scope | None:
        checks = verify_credential(self.authority, now=now, status_registry=self.registry)
        if all(c.passed for c in checks) and issuer_id(self.authority) in self.policy.trust_anchors:
            return scope_of(self.authority)
        return None

    # ---------------------------------------------------------------- inbound
    def handle(self, env: dict, *, now: datetime | None = None) -> HandleResult:
        now = now or utcnow()
        sender = str(env.get("from", ""))
        groups: dict[str, list[CheckResult]] = {
            "message": verify_envelope(env, expected_to=self.did, guard=self.guard, now=now)
        }

        vp = env.get("presentation")
        credentials: list[dict] = []
        if not isinstance(vp, dict):
            groups["presentation"] = [fail("presentation", "no credentials were presented")]
        else:
            report = verify_presentation(vp, challenge=str(env.get("nonce", "")), domain=self.did, now=now,
                                         status_registry=self.registry)
            pres = list(report.checks)
            pres.append(ok("holder_is_sender", "credentials presented by the message sender")
                        if vp.get("holder") == sender
                        else fail("holder_is_sender", "credentials belong to someone other than the sender"))
            groups["presentation"] = pres
            credentials = list(vp.get("verifiableCredential") or [])

        chain = order_chain(credentials)
        chain_result = verify_chain(chain, trust_anchors=self.policy.trust_anchors, holder=sender,
                                    now=now, status_registry=self.registry)
        groups["authority_chain"] = chain_result.checks

        body = env.get("body") or {}
        text = str(body.get("text", ""))
        convo = self.conversations.setdefault(sender, Conversation())
        # Conversation features (memory, questions, small talk) exist only for verified senders.
        verified = all(c.passed for g in ("message", "presentation", "authority_chain") for c in groups[g])
        lang = detect_language(text) if text.strip() else convo.lang
        request = _explicit_request(body)
        parsed: ParsedRequest | None = None
        grounded = True
        if request is not None:
            groups["reader"] = [ok("mode", "structured request supplied and signed by the sender")]
        else:
            reading = self.reader.read(text, self.orders, context=convo.context() if verified else (),
                                       agent_question=convo.last_question if verified else "")
            parsed, grounded = reading.parsed, reading.grounded
            if verified:
                # Pending details were grounded when the customer gave them; an ungrounded new reading
                # keeps that context (so it escalates) but contributes no new values of its own.
                parsed = convo.merge(parsed)
                if grounded:
                    parsed = convo.answer_slots(parsed, text, self.orders)
            request = parsed.to_request() if parsed.intent and parsed.intent != "smalltalk" else Request(action="unknown")
            groups["reader"] = reading.checks + [ok("understood", parsed.understood())]
            if parsed.ignored_instructions:
                groups["reader"].append(ok("instructions_ignored",
                                           f"treated as data, not commands: “{parsed.ignored_instructions[0][:100]}”"))
        if verified and text.strip():
            convo.note_customer(text)

        if verified and parsed is not None and grounded:
            allowed = self._allowed_orders(chain_result.scope)
            if parsed.intent == "smalltalk":
                return self._converse(CHAT, smalltalk_reply(text, lang), groups, parsed, sender, lang, now)
            missing = missing_slots(parsed)
            outside_scope = parsed.order is not None and parsed.order not in allowed
            # No request type yet: always ask kindly. Missing details: ask, unless the order isn't theirs.
            if missing and (parsed.intent is None or (not outside_scope and parsed.intent in ("refund.request", "order.lookup"))):
                question = clarifying_question(missing, parsed, allowed, lang)
                convo.hold(parsed, question)
                return self._converse(CLARIFY, question, groups, parsed, sender, lang, now)
        convo.clear()

        evidence = Evidence(
            request=request, now=now, groups=groups,
            delegated_scope=chain_result.scope, own_authority=self.own_authority(now),
            attestations=[c for c in credentials if "DeliveryAttestation" in types_of(c)],
            vouches=[c for c in credentials if "VouchCredential" in types_of(c)],
            status_registry=self.registry,
        )
        decision = self.policy.evaluate(evidence)

        escalation = None
        if decision.outcome == ESCALATE:
            escalation = Escalation(f"esc-{uuid.uuid4().hex[:8]}", request, sender, chain_result.principal, decision)
            self.escalations[escalation.id] = escalation

        receipt = self.ledger.append(
            request.action, outcome=decision.outcome, counterparty=sender,
            details={"order": request.order, "amount": request.amount, "currency": request.currency,
                     "reason": decision.reason, "message": env.get("id"),
                     **({"escalation": escalation.id} if escalation else {})},
            now=now,
        )
        reply = self.send(sender, {
            "kind": "decision", "outcome": decision.outcome, "reason": decision.reason,
            "text": self.replier.write(decision, escalation_id=escalation.id if escalation else None, lang=lang),
            "receipt": receipt["proof"]["proofValue"][:16],
        }, now=now)
        return HandleResult(decision, reply, receipt, escalation, text)

    # ---------------------------------------------------------------- conversation helpers
    def _allowed_orders(self, scope: Scope | None) -> dict[str, dict]:
        """Orders the requester may act on: never reveal others in a question."""
        if scope is None:
            return {}
        return {oid: o for oid, o in self.orders.items() if scope.covers_order(oid)}

    def _converse(self, outcome: str, message: str, groups: dict, parsed: ParsedRequest, sender: str,
                  lang: str, now: datetime) -> HandleResult:
        """A question or a pleasantry: nothing is decided, so nothing is written to the action log."""
        trace = [CheckResult(f"{g}.{c.name}", c.passed, c.detail) for g, cs in groups.items() for c in cs]
        trace.append(ok(f"conversation.{outcome.lower()}",
                        "asked for the missing details; nothing decided yet" if outcome == CLARIFY
                        else "greeting or thanks; nothing to decide"))
        request = Request(action=parsed.intent or "unknown", order=parsed.order, amount=parsed.amount or 0.0,
                          currency=parsed.currency)
        decision = Decision(outcome, message, trace, request)
        reply = self.send(sender, {"kind": outcome.lower(), "text": message, "lang": lang}, now=now)
        return HandleResult(decision, reply, None, None, parsed.text)

    # ---------------------------------------------------------------- human in the loop
    def resolve(self, escalation_id: str, approval: dict, supervisor_credential: dict,
                *, now: datetime | None = None) -> tuple[Escalation, list[CheckResult], dict | None]:
        """Apply a supervisor's signed decision on an escalation. Returns (escalation, checks, receipt)."""
        now = now or utcnow()
        esc = self.escalations.get(escalation_id)
        if esc is None:
            raise KeyError(escalation_id)
        approver = str(approval.get("approver", ""))
        checks: list[CheckResult] = []

        sig = verify_proof(approval, purpose="assertionMethod")
        checks.append(CheckResult("approval_signature", sig.passed, sig.detail))
        vm = (approval.get("proof") or {}).get("verificationMethod", "")
        checks.append(ok("approver_identity", "signed by the named supervisor") if controller_of(vm) == approver
                      else fail("approver_identity", "approval not signed by the named supervisor"))
        checks.append(ok("approval_target", "approval refers to this escalation")
                      if approval.get("escalation") == escalation_id and esc.status == "pending"
                      else fail("approval_target", "approval is for a different or already-resolved escalation"))
        chain = verify_chain([supervisor_credential], trust_anchors=self.policy.trust_anchors,
                             holder=approver, now=now, status_registry=self.registry)
        checks.extend(CheckResult(f"supervisor.{c.name}", c.passed, c.detail) for c in chain.checks)
        if chain.scope is not None:
            s = scope_allows(chain.scope, "refund.issue", esc.request.order, esc.request.amount, esc.request.currency)
            checks.append(CheckResult("supervisor.scope", s.passed, s.detail))

        if not all(c.passed for c in checks):
            esc.resolution = checks
            return esc, checks, None

        approved = bool(approval.get("approved"))
        esc.status = "approved" if approved else "declined"
        esc.resolution = checks
        receipt = self.ledger.append(
            "refund.issue" if approved else esc.request.action,
            outcome=ACCEPT if approved else "DECLINED",
            counterparty=esc.requester,
            details={"order": esc.request.order, "amount": esc.request.amount, "escalation": esc.id,
                     "decided_by": approver, "note": approval.get("note", "")},
            now=now,
        )
        return esc, checks, receipt


class Supervisor:
    """A human with a merchant-issued SupervisorCredential. Signs approvals in the UI."""

    def __init__(self, identity: Identity, credential: dict):
        self.identity, self.credential = identity, credential

    @property
    def did(self) -> str:
        return self.identity.did

    def sign_decision(self, escalation_id: str, *, approved: bool, note: str = "", now: datetime | None = None) -> dict:
        from ..credentials import iso
        doc = {"type": "EscalationDecision", "escalation": escalation_id, "approver": self.did,
               "approved": approved, "note": note, "decidedAt": iso(now or utcnow())}
        return add_proof(doc, self.identity)
