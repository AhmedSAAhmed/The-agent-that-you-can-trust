# 01_crypto_core - keys, DIDs, credentials, revocation

One job: Build signing identities and W3C Verifiable Credentials that verify, and fail loudly when tampered with.

## Inputs
- Reference (every run): `PLAN.md` (sections 2 and 3)

Do NOT load: other stages' notes, or later stages' code.

## Process
1. If an input is missing, or the previous `check.md` is not `pass`, stop and say which.
2. `src/trustdesk/identity.py`: Ed25519 keys, `did:key` encode/decode, DID Document
3. `src/trustdesk/credentials.py`: issue/verify VC 2.0 with Data Integrity `eddsa-jcs-2022`; Verifiable Presentations
4. `src/trustdesk/status_list.py`: Bitstring Status List issue, revoke, check
5. Tests first: round-trip, tamper (one changed byte fails), wrong key fails, revoked fails, expired fails

## Outputs
- Code under `src/trustdesk/` and `tests/` (see AGENTS.md, deliberate break)
- `output/notes.md`: decisions made, anything cut

## Check
Run `uv run pytest tests/test_identity.py tests/test_credentials.py tests/test_status_list.py -q`. Write `output/check.md`: first line `pass` or `fail: <why>`.
