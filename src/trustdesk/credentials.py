"""W3C Verifiable Credentials 2.0 secured with Data Integrity `eddsa-jcs-2022`.

Signing (vc-di-eddsa §3.3):
    proofConfig = proof options (+ the document's @context)
    hashData    = SHA-256(JCS(proofConfig)) || SHA-256(JCS(document without proof))
    proofValue  = "z" + base58btc(Ed25519.sign(hashData))

Checked byte-for-byte against the W3C test vector in tests/test_credentials.py.

Every verifier returns named `CheckResult`s instead of a bare bool, so the UI can
explain *why* something was trusted or refused.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol

import base58
import jcs

from .identity import (
    DIDError,
    Identity,
    controller_of,
    public_key_from_verification_method,
    verify_signature,
)

VC_V2 = "https://www.w3.org/ns/credentials/v2"
# W3C's examples context declares an @vocab, so our custom claim names stay valid JSON-LD.
VC_EXAMPLES = "https://www.w3.org/ns/credentials/examples/v2"
DEFAULT_CONTEXT = [VC_V2, VC_EXAMPLES]
CRYPTOSUITE = "eddsa-jcs-2022"


# ---------------------------------------------------------------- results
@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

    def __str__(self) -> str:
        return f"{'PASS' if self.passed else 'FAIL'} {self.name}: {self.detail}"


def ok(name: str, detail: str) -> CheckResult:
    return CheckResult(name, True, detail)


def fail(name: str, detail: str) -> CheckResult:
    return CheckResult(name, False, detail)


# ---------------------------------------------------------------- time
def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- proofs
def _without(doc: dict, key: str) -> dict:
    return {k: v for k, v in doc.items() if k != key}


def hash_data(unsecured_doc: dict, proof_config: dict) -> bytes:
    return (
        hashlib.sha256(jcs.canonicalize(proof_config)).digest()
        + hashlib.sha256(jcs.canonicalize(unsecured_doc)).digest()
    )


def add_proof(
    doc: dict,
    signer: Identity,
    *,
    purpose: str = "assertionMethod",
    created: str | None = None,
    extra: dict | None = None,
) -> dict:
    """Return a copy of `doc` with a DataIntegrityProof attached."""
    unsecured = _without(doc, "proof")
    config: dict[str, Any] = {
        "type": "DataIntegrityProof",
        "cryptosuite": CRYPTOSUITE,
        "created": created or iso(utcnow()),
        "verificationMethod": signer.verification_method,
        "proofPurpose": purpose,
        **(extra or {}),
    }
    if "@context" in unsecured:
        config["@context"] = unsecured["@context"]
    signature = signer.sign(hash_data(unsecured, config))
    return {**unsecured, "proof": {**config, "proofValue": "z" + base58.b58encode(signature).decode()}}


def verify_proof(doc: dict, *, purpose: str | None = None) -> CheckResult:
    """Cryptographic check only: was this exact document signed by the key in verificationMethod?"""
    name = "proof"
    proof = doc.get("proof")
    if not isinstance(proof, dict):
        return fail(name, "no proof attached")
    if proof.get("type") != "DataIntegrityProof" or proof.get("cryptosuite") != CRYPTOSUITE:
        return fail(name, f"unsupported proof {proof.get('type')}/{proof.get('cryptosuite')}")
    if purpose and proof.get("proofPurpose") != purpose:
        return fail(name, f"proof purpose is {proof.get('proofPurpose')!r}, expected {purpose!r}")
    pv = proof.get("proofValue", "")
    if not isinstance(pv, str) or not pv.startswith("z"):
        return fail(name, "proofValue is not multibase base58btc")
    try:
        signature = base58.b58decode(pv[1:])
        key = public_key_from_verification_method(proof.get("verificationMethod", ""))
    except (ValueError, DIDError) as exc:
        return fail(name, f"cannot resolve signer: {exc}")
    if len(signature) != 64:
        return fail(name, "signature has wrong length")

    config = _without(proof, "proofValue")
    unsecured = _without(doc, "proof")
    if "@context" in config and config["@context"] != unsecured.get("@context"):
        return fail(name, "proof @context does not match document @context")
    if not verify_signature(key, hash_data(unsecured, config), signature):
        return fail(name, "signature does not match the document (tampered or wrong key)")
    return ok(name, f"Ed25519 signature valid ({CRYPTOSUITE})")


# ---------------------------------------------------------------- credentials
def issuer_id(vc: dict) -> str:
    issuer = vc.get("issuer")
    return issuer.get("id", "") if isinstance(issuer, dict) else str(issuer or "")


def issue_credential(
    issuer: Identity,
    *,
    subject_did: str,
    types: Iterable[str],
    claims: dict | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    status: dict | None = None,
    name: str | None = None,
    now: datetime | None = None,
    credential_id: str | None = None,
) -> dict:
    now = now or utcnow()
    vc: dict[str, Any] = {
        "@context": list(DEFAULT_CONTEXT),
        "id": credential_id or f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", *types],
        "issuer": issuer.did,
        "validFrom": iso(valid_from or now),
    }
    if name:
        vc["name"] = name
    if valid_until:
        vc["validUntil"] = iso(valid_until)
    vc["credentialSubject"] = {"id": subject_did, **(claims or {})}
    if status:
        vc["credentialStatus"] = status
    return add_proof(vc, issuer, created=iso(now))


class StatusChecker(Protocol):
    def check(self, entry: dict, expected_issuer: str, now: datetime) -> CheckResult: ...


def verify_credential(
    vc: dict, *, now: datetime | None = None, status_registry: StatusChecker | None = None
) -> list[CheckResult]:
    now = now or utcnow()
    results: list[CheckResult] = []

    # 1. structure
    ctx = vc.get("@context") or []
    types = vc.get("type") or []
    if ctx[:1] != [VC_V2] or "VerifiableCredential" not in types or not issuer_id(vc) or "credentialSubject" not in vc:
        results.append(fail("structure", "not a well-formed VC 2.0 credential"))
    else:
        results.append(ok("structure", f"VC 2.0 {', '.join(t for t in types if t != 'VerifiableCredential')}"))

    # 2. signature
    results.append(verify_proof(vc, purpose="assertionMethod"))

    # 3. the signing key must belong to the stated issuer
    vm = (vc.get("proof") or {}).get("verificationMethod", "")
    if vm and controller_of(vm) == issuer_id(vc):
        results.append(ok("issuer_binding", "signed by the issuer's own key"))
    else:
        results.append(fail("issuer_binding", "signing key does not belong to the stated issuer"))

    # 4. validity window
    try:
        start = parse_time(vc["validFrom"]) if "validFrom" in vc else None
        end = parse_time(vc["validUntil"]) if "validUntil" in vc else None
        if start and now < start:
            results.append(fail("validity_period", f"not valid until {vc['validFrom']}"))
        elif end and now > end:
            results.append(fail("validity_period", f"expired at {vc['validUntil']}"))
        else:
            results.append(ok("validity_period", f"valid until {vc.get('validUntil', 'no expiry')}"))
    except ValueError:
        results.append(fail("validity_period", "unparseable validFrom/validUntil"))

    # 5. revocation
    entry = vc.get("credentialStatus")
    if not entry:
        results.append(ok("status", "no status entry (credential is not revocable)"))
    elif status_registry is None:
        results.append(fail("status", "credential is revocable but no status registry was provided"))
    else:
        results.append(status_registry.check(entry, issuer_id(vc), now))
    return results


# ---------------------------------------------------------------- presentations
def create_presentation(
    holder: Identity,
    credentials: list[dict],
    *,
    challenge: str,
    domain: str,
    now: datetime | None = None,
) -> dict:
    vp = {
        "@context": [VC_V2],
        "type": ["VerifiablePresentation"],
        "holder": holder.did,
        "verifiableCredential": credentials,
    }
    return add_proof(
        vp, holder, purpose="authentication", created=iso(now or utcnow()),
        extra={"challenge": challenge, "domain": domain},
    )


@dataclass
class PresentationReport:
    checks: list[CheckResult] = field(default_factory=list)
    credentials: list[tuple[dict, list[CheckResult]]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks) and all(
            r.passed for _, results in self.credentials for r in results
        )


def verify_presentation(
    vp: dict,
    *,
    challenge: str,
    domain: str,
    now: datetime | None = None,
    status_registry: StatusChecker | None = None,
) -> PresentationReport:
    report = PresentationReport()
    proof = vp.get("proof") or {}
    report.checks.append(verify_proof(vp, purpose="authentication"))

    holder = vp.get("holder", "")
    vm = proof.get("verificationMethod", "")
    if holder and vm and controller_of(vm) == holder:
        report.checks.append(ok("holder_binding", "presentation signed by the holder's own key"))
    else:
        report.checks.append(fail("holder_binding", "presentation not signed by the stated holder"))

    report.checks.append(
        ok("challenge", "fresh challenge echoed")
        if proof.get("challenge") == challenge
        else fail("challenge", "challenge mismatch (possible replay)")
    )
    report.checks.append(
        ok("domain", f"bound to {domain}")
        if proof.get("domain") == domain
        else fail("domain", f"presentation was made for {proof.get('domain')!r}, not {domain!r}")
    )
    for vc in vp.get("verifiableCredential") or []:
        report.credentials.append((vc, verify_credential(vc, now=now, status_registry=status_registry)))
    return report
