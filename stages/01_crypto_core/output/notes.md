# 01_crypto_core - notes

## Built
- `src/trustdesk/identity.py`: Ed25519 `Identity`, `did:key` encode/resolve, DID Document (Multikey). `from_seed` gives a deterministic demo world; `from_secret_multibase` loads the W3C test key.
- `src/trustdesk/credentials.py`: VC 2.0 issue/verify, Data Integrity `eddsa-jcs-2022` (`add_proof` / `verify_proof`), Verifiable Presentations with challenge + domain. Every verifier returns named `CheckResult(name, passed, detail)`, which the UI trace will use.
- `src/trustdesk/status_list.py`: Bitstring Status List v1.0 (131,072-bit minimum, GZIP + multibase base64url, random index allocation). `StatusRegistry.check` fails closed and rejects lists not signed by the credential's own issuer.

## Credential check names (stable API for later stages)
`structure`, `proof`, `issuer_binding`, `validity_period`, `status`; presentations add `holder_binding`, `challenge`, `domain`.

## Decisions
- Custom claims use the W3C examples context (`credentials/examples/v2`, has `@vocab`) instead of hosting our own JSON-LD context. JCS doesn't need JSON-LD processing.
- `proof` checks the math; `issuer_binding` checks the key belongs to the issuer. These are separate, so the UI can show "valid signature, wrong signer" (the forged-credential attack).
- A credential with no `credentialStatus` passes `status` as "not revocable". Policy (stage 02) decides whether revocability is required.

## Cut
None.
