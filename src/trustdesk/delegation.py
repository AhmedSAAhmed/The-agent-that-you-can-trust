"""Scoped authority and delegation chains with attenuation.

Every authority-bearing credential carries `credentialSubject.scope`:
    {"actions": [...], "orders": [... or "*"], "maxAmount": n, "currency": "AED"}

A chain is root -> ... -> leaf. The root must be issued by a trust anchor.
Each child must be issued by its parent's subject, point at its parent's id,
expire no later than its parent, and hold a scope that is a subset of its parent's.
Authority can only shrink as it is handed down, never grow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .credentials import (
    CheckResult,
    StatusChecker,
    fail,
    issue_credential,
    issuer_id,
    ok,
    parse_time,
    verify_credential,
)
from .identity import Identity


@dataclass(frozen=True)
class Scope:
    actions: list[str]
    orders: list[str]
    max_amount: float
    currency: str

    @classmethod
    def from_dict(cls, d: dict) -> "Scope":
        return cls(
            actions=list(d.get("actions", [])),
            orders=[str(o) for o in d.get("orders", [])],
            max_amount=float(d.get("maxAmount", 0)),
            currency=str(d.get("currency", "")),
        )

    def to_dict(self) -> dict:
        amount = int(self.max_amount) if float(self.max_amount).is_integer() else self.max_amount
        return {"actions": self.actions, "orders": self.orders, "maxAmount": amount, "currency": self.currency}

    def covers_order(self, order: str) -> bool:
        return "*" in self.orders or str(order) in self.orders

    def is_subset_of(self, parent: "Scope") -> bool:
        return not self.widening(parent)

    def widening(self, parent: "Scope") -> list[str]:
        """Human-readable list of every way this scope exceeds the parent."""
        problems = []
        extra = set(self.actions) - set(parent.actions)
        if extra:
            problems.append(f"adds actions {sorted(extra)}")
        if "*" in self.orders and "*" not in parent.orders:
            problems.append("widens orders to '*'")
        elif "*" not in parent.orders and set(self.orders) - set(parent.orders):
            problems.append(f"adds orders {sorted(set(self.orders) - set(parent.orders))}")
        if self.max_amount > parent.max_amount:
            problems.append(f"raises limit {parent.max_amount:g} -> {self.max_amount:g}")
        if self.currency != parent.currency:
            problems.append(f"changes currency {parent.currency} -> {self.currency}")
        return problems

    def describe(self) -> str:
        return f"{'/'.join(self.actions)} on orders {', '.join(self.orders)} up to {self.currency} {self.max_amount:g}"


def scope_of(vc: dict) -> Scope:
    return Scope.from_dict(vc.get("credentialSubject", {}).get("scope", {}))


def scope_allows(scope: Scope, action: str, order: str | None, amount: float, currency: str) -> CheckResult:
    name = "scope"
    if action not in scope.actions:
        return fail(name, f"'{action}' is not in delegated actions {scope.actions}")
    if order is not None and not scope.covers_order(order):
        return fail(name, f"order #{order} is not covered (allowed: {', '.join(scope.orders)})")
    if currency != scope.currency:
        return fail(name, f"currency {currency} not allowed (scope is {scope.currency})")
    if amount > scope.max_amount:
        return fail(name, f"{currency} {amount:g} exceeds delegated limit {scope.max_amount:g}")
    return ok(name, f"within scope: {scope.describe()}")


def delegate(
    delegator: Identity,
    *,
    parent: dict,
    delegate_did: str,
    scope: Scope,
    valid_until: datetime | None = None,
    status: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Issue a DelegationCredential. Refuses to widen the parent's scope."""
    if parent.get("credentialSubject", {}).get("id") != delegator.did:
        raise ValueError("only the parent credential's subject can delegate it")
    problems = scope.widening(scope_of(parent))
    if problems:
        raise ValueError("delegation would widen authority: " + "; ".join(problems))
    if valid_until and "validUntil" in parent and valid_until > parse_time(parent["validUntil"]):
        raise ValueError("delegation cannot outlive its parent")
    return issue_credential(
        delegator,
        subject_did=delegate_did,
        types=["DelegationCredential"],
        claims={"scope": scope.to_dict(), "parentCredential": parent["id"]},
        valid_until=valid_until or (parse_time(parent["validUntil"]) if "validUntil" in parent else None),
        status=status,
        now=now,
    )


@dataclass
class ChainResult:
    checks: list[CheckResult] = field(default_factory=list)
    scope: Scope | None = None
    principal: str = ""  # who the authority ultimately acts for (the root's subject)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)


def verify_chain(
    chain: list[dict],
    *,
    trust_anchors: set[str],
    holder: str,
    now: datetime,
    status_registry: StatusChecker | None = None,
) -> ChainResult:
    result = ChainResult()
    if not chain:
        result.checks.append(fail("chain_links", "no authority credentials presented"))
        return result

    # every credential on its own
    for i, vc in enumerate(chain):
        label = "root" if i == 0 else f"link{i}"
        kind = next((t for t in vc.get("type", []) if t != "VerifiableCredential"), "credential")
        for r in verify_credential(vc, now=now, status_registry=status_registry):
            result.checks.append(CheckResult(f"{label}.{r.name}", r.passed, f"{kind}: {r.detail}"))

    root_issuer = issuer_id(chain[0])
    result.checks.append(
        ok("trust_anchor", "root issued by a trust anchor")
        if root_issuer in trust_anchors
        else fail("trust_anchor", "root credential is not issued by any trust anchor")
    )

    links_ok, attenuation_problems = True, []
    for parent, child in zip(chain, chain[1:]):
        if issuer_id(child) != parent.get("credentialSubject", {}).get("id") or \
                child.get("credentialSubject", {}).get("parentCredential") != parent.get("id"):
            links_ok = False
        attenuation_problems += scope_of(child).widening(scope_of(parent))
        if "validUntil" in parent and (
            "validUntil" not in child or parse_time(child["validUntil"]) > parse_time(parent["validUntil"])
        ):
            attenuation_problems.append("child outlives its parent")
    result.checks.append(
        ok("chain_links", f"{len(chain)} link(s), each issued by the previous holder")
        if links_ok
        else fail("chain_links", "a delegation was not issued by the holder of its parent")
    )
    result.checks.append(
        ok("attenuation", "authority only narrows down the chain")
        if not attenuation_problems
        else fail("attenuation", "; ".join(attenuation_problems))
    )

    leaf_subject = chain[-1].get("credentialSubject", {}).get("id")
    result.checks.append(
        ok("holder_is_delegate", "the presenter is the final delegate")
        if leaf_subject == holder
        else fail("holder_is_delegate", "presenter is not the subject of the final credential")
    )
    result.scope = scope_of(chain[-1])
    result.principal = chain[0].get("credentialSubject", {}).get("id", "")
    return result
