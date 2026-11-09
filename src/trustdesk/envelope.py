"""Signed agent-to-agent messages with replay protection.

An envelope is signed by the sender's DID (proofPurpose `authentication`) and
carries a random nonce and a timestamp. A Verifiable Presentation inside it is
bound to that nonce (challenge) and the recipient's DID (domain), so credentials
captured from one message cannot be reused in another.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .credentials import (
    CheckResult,
    add_proof,
    create_presentation,
    fail,
    iso,
    ok,
    parse_time,
    utcnow,
    verify_proof,
)
from .identity import Identity, controller_of

MAX_SKEW = timedelta(minutes=5)


def seal(
    sender: Identity,
    *,
    to: str,
    body: dict,
    credentials: list[dict] | None = None,
    now: datetime | None = None,
    nonce: str | None = None,
) -> dict:
    now = now or utcnow()
    nonce = nonce or secrets.token_urlsafe(16)
    env = {
        "type": "TrustDeskMessage",
        "id": f"urn:uuid:{uuid.uuid4()}",
        "from": sender.did,
        "to": to,
        "created": iso(now),
        "nonce": nonce,
        "body": body,
    }
    if credentials is not None:
        env["presentation"] = create_presentation(sender, credentials, challenge=nonce, domain=to, now=now)
    return add_proof(env, sender, purpose="authentication", created=iso(now))


@dataclass
class ReplayGuard:
    """Remembers nonces it has accepted inside the freshness window."""

    window: timedelta = MAX_SKEW
    _seen: dict[str, datetime] = field(default_factory=dict)

    def seen(self, nonce: str) -> bool:
        return nonce in self._seen

    def remember(self, nonce: str, now: datetime) -> None:
        self._seen = {n: t for n, t in self._seen.items() if now - t <= self.window * 2}
        self._seen[nonce] = now


def verify_envelope(env: dict, *, expected_to: str, guard: ReplayGuard, now: datetime | None = None) -> list[CheckResult]:
    now = now or utcnow()
    checks: list[CheckResult] = []

    sig = verify_proof(env, purpose="authentication")
    checks.append(CheckResult("message_signature", sig.passed, sig.detail))

    vm = (env.get("proof") or {}).get("verificationMethod", "")
    sender = env.get("from", "")
    checks.append(
        ok("sender_identity", "message signed by the sender's own DID key")
        if sender and controller_of(vm) == sender
        else fail("sender_identity", "signature does not belong to the claimed sender (impersonation)")
    )

    checks.append(
        ok("recipient", "addressed to me")
        if env.get("to") == expected_to
        else fail("recipient", "message was addressed to a different agent")
    )

    try:
        age = now - parse_time(env.get("created", ""))
        fresh = -MAX_SKEW <= age <= guard.window
        checks.append(
            ok("freshness", f"sent {int(age.total_seconds())}s ago")
            if fresh
            else fail("freshness", f"message is {int(age.total_seconds())}s old (window {int(guard.window.total_seconds())}s)")
        )
    except ValueError:
        checks.append(fail("freshness", "unparseable timestamp"))

    nonce = env.get("nonce", "")
    if not nonce:
        checks.append(fail("replay", "no nonce"))
    elif guard.seen(nonce):
        checks.append(fail("replay", "nonce already used: this is a replayed message"))
    else:
        checks.append(ok("replay", "nonce is new"))
        if sig.passed:  # only a genuine message consumes its nonce
            guard.remember(nonce, now)
    return checks
