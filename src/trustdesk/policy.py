"""Explainable trust policy: verified evidence + YAML rules -> ACCEPT / REFUSE / ESCALATE.

The decision is a pure function of signed evidence and a readable policy file.
No score, and no LLM. The returned trace lists every check that ran, so a person
can see exactly why the agent acted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from .credentials import CheckResult, StatusChecker, fail, issuer_id, ok, verify_credential
from .delegation import Scope, scope_allows

ACCEPT, REFUSE, ESCALATE = "ACCEPT", "REFUSE", "ESCALATE"


@dataclass(frozen=True)
class Request:
    action: str
    order: str | None = None
    amount: float = 0.0
    currency: str = "AED"

    def describe(self) -> str:
        parts = [self.action]
        if self.order:
            parts.append(f"order #{self.order}")
        if self.amount:
            parts.append(f"{self.currency} {self.amount:g}")
        return " · ".join(parts)


@dataclass
class Evidence:
    request: Request
    now: datetime
    groups: dict[str, list[CheckResult]] = field(default_factory=dict)  # already-run verification checks
    delegated_scope: Scope | None = None  # leaf scope of the requester's authority chain
    own_authority: Scope | None = None  # the deciding agent's own AuthorityCredential scope
    attestations: list[dict] = field(default_factory=list)  # raw VCs; verified here
    vouches: list[dict] = field(default_factory=list)  # raw VCs; verified here
    status_registry: StatusChecker | None = None


@dataclass
class Decision:
    outcome: str
    reason: str
    trace: list[CheckResult]
    request: Request

    @property
    def failed(self) -> list[CheckResult]:
        return [c for c in self.trace if not c.passed]


class Policy:
    def __init__(self, spec: dict, directory: dict[str, str]):
        self.spec = spec
        self.name = spec.get("policy", "policy")
        self.directory = directory
        self.trust_anchors = {self._did(n) for n in spec.get("trust_anchors", [])}
        self.trusted_attesters = {self._did(n) for n in spec.get("trusted_attesters", [])}
        self.min_anchor_vouches = int(spec.get("vouches", {}).get("min_from_anchors", 0) or 0)

    def _did(self, name: str) -> str:
        if name.startswith("did:"):
            return name
        if name not in self.directory:
            raise KeyError(f"policy names unknown party {name!r}")
        return self.directory[name]

    @classmethod
    def load(cls, path: str | Path, directory: dict[str, str]) -> "Policy":
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")), directory)

    # ------------------------------------------------------------ attesters
    def attester_trust(self, did: str, ev: Evidence) -> CheckResult:
        if did in self.trusted_attesters:
            return ok("attester_trusted", "attester is on the policy's trusted list")
        valid_vouches = [
            v for v in ev.vouches
            if v.get("credentialSubject", {}).get("id") == did
            and "VouchCredential" in v.get("type", [])
            and all(c.passed for c in verify_credential(v, now=ev.now, status_registry=ev.status_registry))
        ]
        anchored = {issuer_id(v) for v in valid_vouches} & self.trust_anchors
        if self.min_anchor_vouches and len(anchored) >= self.min_anchor_vouches:
            return ok("attester_trusted", f"vouched for by {len(anchored)} trust anchor(s)")
        return fail(
            "attester_trusted",
            f"{len(valid_vouches)} valid vouch(es), {len(anchored)} from trust anchors "
            f"(need {self.min_anchor_vouches}); unanchored vouches are not counted",
        )

    def _delivery_evidence(self, ev: Evidence, statuses: list[str]) -> tuple[CheckResult, list[CheckResult]]:
        notes: list[CheckResult] = []
        for vc in ev.attestations:
            subject = vc.get("credentialSubject", {})
            if "DeliveryAttestation" not in vc.get("type", []) or str(subject.get("order")) != str(ev.request.order):
                continue
            vc_checks = verify_credential(vc, now=ev.now, status_registry=ev.status_registry)
            bad = [c for c in vc_checks if not c.passed]
            if bad:
                notes.append(fail("attestation_valid", f"attestation rejected ({bad[0].name}: {bad[0].detail})"))
                continue
            trust = self.attester_trust(issuer_id(vc), ev)
            notes.append(trust)
            if trust.passed and subject.get("status") in statuses:
                return ok("delivery_evidence", f"courier attests order #{ev.request.order}: {subject.get('status')}"), notes
        return fail("delivery_evidence", f"no trusted delivery attestation supports a refund on order #{ev.request.order}"), notes

    # ------------------------------------------------------------ decide
    def evaluate(self, ev: Evidence) -> Decision:
        req = ev.request
        trace: list[CheckResult] = []

        def done(outcome: str, reason: str) -> Decision:
            return Decision(outcome, reason, trace, req)

        rule = (self.spec.get("actions") or {}).get(req.action)
        if rule is None:
            trace.append(fail("policy.action", f"no rule permits '{req.action}' (default: {self.spec.get('default', 'refuse')})"))
            return done(REFUSE, f"'{req.action}' is not something I'm allowed to do")
        trace.append(ok("policy.action", f"rule found for '{req.action}'"))

        # 1. hard requirements: cryptographic and authority checks
        first_failure: CheckResult | None = None
        for group in rule.get("must_pass", []):
            results = ev.groups.get(group)
            if not results:
                results = [fail(f"{group}", "not provided")]
            for c in results:
                labelled = CheckResult(f"{group}.{c.name}", c.passed, c.detail)
                trace.append(labelled)
                if not c.passed and first_failure is None:
                    first_failure = labelled
        if first_failure:
            return done(REFUSE, f"{first_failure.name}: {first_failure.detail}")

        # 2. well-formed request
        if rule.get("require_amount"):
            if req.amount <= 0 or not req.order:
                trace.append(fail("policy.request_complete", "a refund needs an order number and a positive amount"))
                return done(REFUSE, "the request does not say which order or how much to refund")
            trace.append(ok("policy.request_complete", f"order #{req.order}, {req.currency} {req.amount:g}"))

        # 3. scope
        if rule.get("within_scope"):
            if ev.delegated_scope is None:
                trace.append(fail("policy.scope", "no delegated scope"))
                return done(REFUSE, "no delegated authority")
            s = scope_allows(ev.delegated_scope, req.action, req.order, req.amount, req.currency)
            trace.append(CheckResult("policy.scope", s.passed, s.detail))
            if not s.passed:
                return done(REFUSE, s.detail)

        # 3. evidence for larger refunds
        evidence_rule = rule.get("evidence") or {}
        threshold = evidence_rule.get("delivery_attestation_above")
        if threshold is not None and req.amount > float(threshold):
            result, notes = self._delivery_evidence(ev, evidence_rule.get("supporting_statuses", []))
            trace.extend(CheckResult(f"evidence.{n.name}", n.passed, n.detail) for n in notes)
            trace.append(CheckResult("policy.delivery_evidence", result.passed, result.detail))
            if not result.passed:
                return done(ESCALATE, f"needs a human: {result.detail}")

        # 4. my own authority limit
        if rule.get("auto_approve_up_to") == "own_authority":
            own = ev.own_authority
            own_action = rule.get("own_action", req.action)
            if own is None:
                trace.append(fail("policy.own_authority", "I hold no authority credential for this"))
                return done(REFUSE, "I am not authorized to act on this")
            mine = scope_allows(own, own_action, None, req.amount, req.currency)
            trace.append(CheckResult(
                "policy.own_authority", mine.passed,
                f"within my own authority ({own.currency} {own.max_amount:g})" if mine.passed
                else f"{req.currency} {req.amount:g} is above my own authority limit ({own.currency} {own.max_amount:g})"))
            if not mine.passed:
                if rule.get("otherwise") == "escalate":
                    return done(ESCALATE, f"allowed by the customer's delegation, but above my own limit "
                                          f"({own.currency} {own.max_amount:g}): a human must approve")
                return done(REFUSE, mine.detail)

        return done(ACCEPT, f"all checks passed: {req.describe()}")
