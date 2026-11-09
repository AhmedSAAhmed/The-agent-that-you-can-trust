import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app  # noqa: E402


def test_app_builds():
    assert app.build() is not None


def test_live_desk_flow():
    world, chat, panel, *_ = app.init()
    assert "verified me" in chat[0]["content"]
    out = app.send(world, app.EXAMPLES[0], "1042", 250, True, chat)
    world, chat, panel = out[0], out[1], out[2]
    assert "ACCEPT" in panel and "checks passed" in panel
    out = app.send(world, app.EXAMPLES[1], "1042", 380, True, chat)
    assert "ESCALATE" in out[2]
    esc_id = next(iter(world.support.escalations))
    world, html, *_ = app.decide(world, esc_id, "ok", True)
    assert "approved" in html


def test_default_amount_field_does_not_override_parsed_amount():
    """Regression: the empty Number field (0) once turned 'AED 380' into a refund of 0."""
    world, chat, *_ = app.init()
    out = app.send(world, "Refund AED 380 for order 1042", None, 0, True, chat, False)
    assert "ESCALATE" in out[2]
    out = app.send(world, "Refund AED 380 for order 1042", "1042", 120, True, out[1], True)  # user edited the field
    assert "ACCEPT" in out[2] and "AED 120" in out[2]


def test_injection_is_shown_as_ignored():
    world, chat, *_ = app.init()
    out = app.send(world, app.EXAMPLES[3], None, None, True, chat)
    assert "treated as data" in out[2]
    assert "REFUSE" in out[2]


def test_controls_and_verify():
    world, *_ = app.init()
    world, msg, *_ = app.control(world, "redelegate", 600, ["1042"], 7)
    assert "Refused" in msg  # cannot exceed Layla's own AED 420
    world, msg, *_ = app.control(world, "revoke_delegation")
    world, js = app.example_credential(world, "tampered")
    world, html = app.verify_pasted(world, js)
    assert "does NOT verify" in html
    world, js = app.example_credential(world, "delegation")
    world, html = app.verify_pasted(world, js)
    assert "revoked" in html


def test_attack_lab():
    assert "defended" in app.attack(list(app.ATTACK_TITLES)[0])
    assert app.attack_all().count("🛡️") == 9
