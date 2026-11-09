import copy
from datetime import datetime, timedelta, timezone

from trustdesk.credentials import add_proof, issue_credential, verify_presentation
from trustdesk.envelope import ReplayGuard, seal, verify_envelope
from trustdesk.identity import Identity

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
assistant = Identity.from_seed("Assistant", b"t-assistant")
support = Identity.from_seed("Support", b"t-support")


def checks(env, guard=None, now=NOW, to=None):
    return {c.name: c for c in verify_envelope(env, expected_to=to or support.did, guard=guard or ReplayGuard(), now=now)}


def msg(**kw):
    return seal(assistant, to=support.did, body={"text": "refund 1042"}, now=NOW, **kw)


def test_genuine_message_passes():
    assert all(c.passed for c in checks(msg()).values())


def test_impersonation_with_own_key_fails():
    mallory = Identity.generate("Mallory")
    env = seal(mallory, to=support.did, body={"text": "refund"}, now=NOW)
    unsigned = {k: v for k, v in env.items() if k != "proof"}
    unsigned["from"] = assistant.did  # claims to be the assistant
    forged = add_proof(unsigned, mallory, purpose="authentication")
    c = checks(forged)
    assert c["message_signature"].passed  # valid math...
    assert not c["sender_identity"].passed  # ...wrong key for that DID


def test_tampered_body_fails():
    env = msg()
    env["body"]["text"] = "refund 9999"
    assert not checks(env)["message_signature"].passed


def test_replay_is_caught():
    guard = ReplayGuard()
    env = msg()
    assert checks(env, guard)["replay"].passed
    assert not checks(copy.deepcopy(env), guard)["replay"].passed


def test_stale_message_fails():
    assert not checks(msg(), now=NOW + timedelta(hours=1))["freshness"].passed


def test_wrong_recipient_fails():
    other = Identity.generate("Other")
    assert not checks(msg(), to=other.did)["recipient"].passed


def test_forged_message_does_not_burn_the_real_nonce():
    guard = ReplayGuard()
    real = msg(nonce="n-1")
    forged = copy.deepcopy(real)
    forged["body"]["text"] = "evil"
    checks(forged, guard)
    assert checks(real, guard)["replay"].passed


def test_presentation_is_bound_to_this_message():
    merchant = Identity.from_seed("Merchant", b"t-m")
    vc = issue_credential(merchant, subject_did=assistant.did, types=["X"], now=NOW)
    env = msg(credentials=[vc])
    vp = env["presentation"]
    assert verify_presentation(vp, challenge=env["nonce"], domain=support.did, now=NOW).passed
    # lifted into another message with a new nonce, it no longer matches
    assert not verify_presentation(vp, challenge="other-nonce", domain=support.did, now=NOW).passed
