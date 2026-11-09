"""Revocation with W3C Bitstring Status List v1.0.

Each revocable credential points at (status list URL, index). The issuer
publishes a *signed* credential holding a GZIP-compressed bitstring. Bit = 1
means revoked. Verifiers check the list's signature and that the list's issuer
is the credential's issuer, so nobody else can "un-revoke" a credential.
The list has at least 131,072 entries, so the index alone reveals little about the holder.
"""

from __future__ import annotations

import base64
import gzip
import secrets
from datetime import datetime

from .credentials import CheckResult, fail, issue_credential, issuer_id, ok, verify_credential
from .identity import Identity

MIN_BITS = 131_072  # 16 KB, the spec's minimum for herd privacy


def encode_bitstring(bits: bytes) -> str:
    compressed = gzip.compress(bits, mtime=0)
    return "u" + base64.urlsafe_b64encode(compressed).decode().rstrip("=")


def decode_bitstring(encoded: str) -> bytes:
    if not encoded.startswith("u"):
        raise ValueError("encodedList must be multibase base64url (prefix 'u')")
    body = encoded[1:]
    return gzip.decompress(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def _bit(bits: bytes | bytearray, index: int) -> bool:
    return bool(bits[index // 8] & (0x80 >> (index % 8)))  # index 0 = left-most bit


class StatusList:
    def __init__(self, issuer: Identity, url: str, *, purpose: str = "revocation", size: int = MIN_BITS):
        if size < MIN_BITS or size % 8:
            raise ValueError(f"status list needs at least {MIN_BITS} bits")
        self.issuer, self.url, self.purpose = issuer, url, purpose
        self.bits = bytearray(size // 8)
        self._used: set[int] = set()

    def allocate(self) -> int:
        """Random index (spec recommendation), so issuance order isn't leaked."""
        while True:
            idx = secrets.randbelow(len(self.bits) * 8)
            if idx not in self._used:
                self._used.add(idx)
                return idx

    def entry(self, index: int) -> dict:
        return {
            "id": f"{self.url}#{index}",
            "type": "BitstringStatusListEntry",
            "statusPurpose": self.purpose,
            "statusListIndex": str(index),
            "statusListCredential": self.url,
        }

    def is_set(self, index: int) -> bool:
        return _bit(self.bits, index)

    def revoke(self, index: int) -> None:
        self.bits[index // 8] |= 0x80 >> (index % 8)

    def reinstate(self, index: int) -> None:
        """Clear the bit. Meaningful for a 'suspension' list; revocation is normally final."""
        self.bits[index // 8] &= ~(0x80 >> (index % 8)) & 0xFF

    def to_credential(self, *, now: datetime | None = None) -> dict:
        return issue_credential(
            self.issuer,
            subject_did=f"{self.url}#list",
            types=["BitstringStatusListCredential"],
            claims={
                "type": "BitstringStatusList",
                "statusPurpose": self.purpose,
                "encodedList": encode_bitstring(bytes(self.bits)),
            },
            credential_id=self.url,
            now=now,
        )


class StatusRegistry:
    """Where verifiers fetch status lists. In production this is an HTTPS GET of the URL."""

    def __init__(self) -> None:
        self._lists: dict[str, dict] = {}

    def publish(self, status_credential: dict) -> None:
        self._lists[status_credential["id"]] = status_credential

    def get(self, url: str) -> dict | None:
        return self._lists.get(url)

    def check(self, entry: dict, expected_issuer: str, now: datetime) -> CheckResult:
        name = "status"
        if entry.get("type") != "BitstringStatusListEntry":
            return fail(name, f"unsupported status type {entry.get('type')!r}")
        url = entry.get("statusListCredential", "")
        status_vc = self.get(url)
        if status_vc is None:
            return fail(name, f"status list {url} unavailable, failing closed")

        list_checks = verify_credential(status_vc, now=now)
        bad = [c for c in list_checks if not c.passed]
        if bad:
            return fail(name, f"status list is not trustworthy ({bad[0].name}: {bad[0].detail})")
        if issuer_id(status_vc) != expected_issuer:
            return fail(name, "status list was not published by the credential's issuer")

        subject = status_vc.get("credentialSubject", {})
        if subject.get("statusPurpose") != entry.get("statusPurpose"):
            return fail(name, "status purpose mismatch")
        try:
            bits = decode_bitstring(subject["encodedList"])
            index = int(entry["statusListIndex"])
        except (KeyError, ValueError) as exc:
            return fail(name, f"malformed status data: {exc}")
        if len(bits) * 8 < MIN_BITS or not 0 <= index < len(bits) * 8:
            return fail(name, "status index out of range")
        if _bit(bits, index):
            return fail(name, f"{entry.get('statusPurpose')}: credential was revoked by its issuer")
        return ok(name, f"not revoked (checked signed list {url})")
