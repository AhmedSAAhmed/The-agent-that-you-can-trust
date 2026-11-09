"""HTML renderers for the Gradio UI. Pure functions: data in, escaped HTML out."""

from __future__ import annotations

import html
import json

from .credentials import CheckResult, issuer_id, verify_credential
from .delegation import scope_of
from .ledger import summarize, verify_history
from .policy import Decision

from .theme import CSS  # noqa: E402,F401  (re-exported for app.py)

ICON = {"ACCEPT": "✅ ACCEPT", "REFUSE": "⛔ REFUSE", "ESCALATE": "🧑‍💼 ESCALATE TO HUMAN", "BLOCKED": "🛡️ BLOCKED"}

GROUPS = [
    ("reader", "0 · Reading the message", "AI or rule-based reader; every number must be found in the message"),
    ("message", "1 · Identity", "Is the sender who they claim? Signed, fresh, not replayed"),
    ("presentation", "2 · Credentials", "Presented by their holder, bound to this exact message"),
    ("authority_chain", "3 · Authority", "Traced back to Souq Bloom; can only narrow at each hand-off"),
    ("evidence", "4 · Evidence", "Delivery attestation from a courier we trust"),
    ("policy", "5 · Policy decision", "Rules from policies/support_agent.yaml"),
    ("approval", "Signed supervisor decision", "Genuine signature, right person, right escalation, not reused"),
    ("authority", "Authority of the other agent", "Is it authorized by Souq Bloom?"),
    ("supervisor", "Supervisor authority", "Merchant-issued SupervisorCredential"),
]

PRETTY = {
    "message_signature": "message signature", "sender_identity": "sender owns this DID", "recipient": "addressed to us",
    "freshness": "freshness", "replay": "not a replay", "proof": "signature", "holder_binding": "signed by holder",
    "challenge": "bound to this message", "domain": "bound to recipient", "holder_is_sender": "holder is sender",
    "trust_anchor": "rooted in a trust anchor", "chain_links": "chain links", "attenuation": "authority only narrows",
    "holder_is_delegate": "presenter is the delegate", "structure": "well-formed VC 2.0", "issuer_binding": "signed by issuer",
    "validity_period": "within validity period", "status": "not revoked", "scope": "within delegated scope",
    "own_authority": "within my own authority", "delivery_evidence": "delivery evidence", "attester_trusted": "attester trusted",
    "attestation_valid": "attestation valid", "action": "action permitted",
    "mode": "reader", "understood": "understood as", "order_grounded": "order found in the message",
    "amount_grounded": "amount found in the message", "instructions_ignored": "instructions treated as data",
    "request_complete": "request complete", "handoff": "handed to a person",
}


def e(s) -> str:
    return html.escape(str(s))


def _pretty(name: str) -> str:
    parts = name.split(".")
    tail = PRETTY.get(parts[-1], parts[-1].replace("_", " "))
    prefix = " ".join(p for p in parts[1:-1])
    return f"{prefix} · {tail}" if prefix else tail


def checklist(trace: list[CheckResult], *, open_all: bool = False) -> str:
    buckets: dict[str, list[CheckResult]] = {}
    for c in trace:
        buckets.setdefault(c.name.split(".")[0], []).append(c)
    known = [g for g, *_ in GROUPS]
    order = [g for g in known if g in buckets] + [g for g in buckets if g not in known]
    meta = {g: (t, h) for g, t, h in GROUPS}
    out = []
    for g in order:
        items = buckets[g]
        passed = sum(c.passed for c in items)
        failed = len(items) - passed
        title, hint = meta.get(g, (g, ""))
        is_open = open_all or failed or g == "policy"
        tally = f"<span class='td-pill {'bad' if failed else 'ok'}'>{passed}/{len(items)} passed</span>"
        rows = "".join(
            f"<li><span class='{'td-pass' if c.passed else 'td-fail'}'>{'✔' if c.passed else '✘'} {e(_pretty(c.name))}</span>"
            f" · {e(c.detail)} <span class='td-name'>[{e(c.name)}]</span></li>"
            for c in items
        )
        out.append(f"<details class='td-group' {'open' if is_open else ''}><summary>{e(title)} {tally}"
                   f" <span class='td-hint'>{e(hint)}</span></summary><ul>{rows}</ul></details>")
    return "".join(out)


VERB = {"ACCEPT": "Accepted", "REFUSE": "Refused", "ESCALATE": "Escalated to a human", "BLOCKED": "Blocked"}

TILES = [  # (label, title, groups it covers)
    ("01", "Identity", ("message",)),
    ("02", "Credentials", ("presentation",)),
    ("03", "Authority", ("authority_chain",)),
    ("04", "Decision", ("reader", "evidence", "policy")),
]


def tiles(trace: list[CheckResult]) -> str:
    out = []
    for num, title, groups in TILES:
        items = [c for c in trace if c.name.split(".")[0] in groups]
        if not items:
            continue
        failed = [c for c in items if not c.passed]
        status = f"{len(failed)} failed" if failed else "passed"
        sub = failed[0].detail if failed else f"{len(items)} checks passed"
        out.append(f"<div class='td-tile {'fail' if failed else ''}'><div class='top'><span>{num}</span>"
                   f"<span class='st {'fail' if failed else ''}'>{e(status)}</span></div>"
                   f"<div><div class='t'>{e(title)}</div><div class='s'>{e(sub[:110])}</div></div></div>")
    return f"<div class='td-tiles'>{''.join(out)}</div>"


def decision_panel(decision: Decision | None, *, extra: list[CheckResult] | None = None) -> str:
    if decision is None:
        return ("<div class='td-card'><div class='td-label'>Trust decision</div>"
                "<div class='td-h'>Waiting for a <em>signed</em> request</div>"
                "<div class='td-hint'>Send a message as Layla's assistant. The support agent's decision appears here, "
                "with every check it ran.</div></div>")
    trace = (extra or []) + decision.trace
    return (f"<div class='td-decision td-{decision.outcome}'><div class='td-badge'>/// {e(VERB.get(decision.outcome, decision.outcome))}</div>"
            f"<div class='td-reason'>{e(decision.reason)}</div><div class='td-req'>{e(decision.request.describe())} · "
            f"{sum(c.passed for c in trace)}/{len(trace)} checks passed · no scores, only evidence and policy</div></div>"
            + tiles(trace) + checklist(trace))


def outcome_banner(outcome: str, headline: str, sub: str = "") -> str:
    return (f"<div class='td-decision td-{e(outcome)}'><div class='td-badge'>/// {e(VERB.get(outcome, outcome))}</div>"
            f"<div class='td-reason'>{e(headline)}</div>{f'<div class=td-req>{e(sub)}</div>' if sub else ''}</div>")


def hero(repo: str) -> str:
    stats = [("10", "/10", "Attacks defended", "Each caught by a named check"),
             ("0", "", "Scores", "Evidence and policy only"),
             ("4", "", "W3C standards", "DID, VC 2.0, Data Integrity, Status List"),
             ("146", "", "Tests", "Including the W3C test vector")]
    cells = "".join(f"<div class='td-stat'><div class='n'>{n}<span>{u}</span></div><div class='l'>{e(l)}</div>"
                    f"<div class='d'>{e(d)}</div></div>" for n, u, l, d in stats)
    return (f"<div class='td-hero'><div class='td-nav'><span class='td-logo'>TRUSTDESK</span>"
            f"<span><a href='#how'>How it works</a><a href='{e(repo)}' target='_blank'>GitHub</a>"
            f"<a class='td-cta' href='{e(repo)}' target='_blank'>View source</a></span></div>"
            f"<h1>Agents that <em>earn</em> trust,<br>not scores</h1>"
            f"<p>A DOO-style support agent for Souq Bloom (a fictional gift shop) decides refund requests sent by other AI agents. "
            f"It accepts, refuses or escalates to a human using signed W3C credentials, revocation and scoped delegation.</p>"
            f"<div class='td-stats'>{cells}</div></div>")


# ---------------------------------------------------------------- profiles
def _cred_row(vc: dict, world) -> str:
    kind = next((t for t in vc.get("type", []) if t != "VerifiableCredential"), "Credential")
    checks = verify_credential(vc, now=world.clock(), status_registry=world.registry)
    good = all(c.passed for c in checks)
    bad = next((c for c in checks if not c.passed), None)
    sub = vc.get("credentialSubject", {})
    scope = f" · {e(scope_of(vc).describe())}" if "scope" in sub else ""
    extra = f" · order #{e(sub.get('order'))}: {e(sub.get('status'))}" if kind == "DeliveryAttestation" else ""
    pill = "<span class='td-pill ok'>valid</span>" if good else f"<span class='td-pill bad'>{e(bad.detail if bad else 'invalid')}</span>"
    return (f"<li><b>{e(kind)}</b> from {e(world.name_of(issuer_id(vc)))} {pill}<br>"
            f"<span class='td-hint'>{scope}{extra} · until {e(vc.get('validUntil', 'no expiry'))}</span></li>")


def _history(agent) -> str:
    h = verify_history(agent.ledger.receipts, agent.did)
    counts = summarize(agent.ledger.receipts)
    pills = "".join(f"<span class='td-pill'>{e(k)}: {v}</span>" for k, v in counts.items()) or "<span class='td-hint'>no actions yet</span>"
    ok_pill = f"<span class='td-pill {'ok' if h.passed else 'bad'}'>{e(h.detail)}</span>"
    rows = "".join(
        f"<tr><td>{r['seq']}</td><td>{e(r['action'])}</td><td>{e(r['outcome'])}</td>"
        f"<td class='td-did'>{e(r['prev'][:12])}…</td></tr>" for r in agent.ledger.receipts[-6:]
    )
    table = f"<table class='td-table'><tr><th>#</th><th>action</th><th>outcome</th><th>prev hash</th></tr>{rows}</table>" if rows else ""
    return f"<div><b>Action history</b> {ok_pill}<br>{pills}{table}</div>"


def profile_card(title: str, role: str, did: str, credentials: list[dict], world, agent=None, note: str = "") -> str:
    creds = "".join(_cred_row(vc, world) for vc in credentials) or "<li class='td-hint'>none</li>"
    return (f"<div class='td-card'><div style='font-size:1.1rem;font-weight:700'>{e(title)}</div>"
            f"<div class='td-hint'>{e(role)}</div><div class='td-did' title='{e(did)}'>{e(did)}</div>"
            f"{f'<div class=td-hint>{e(note)}</div>' if note else ''}"
            f"<div style='margin-top:8px'><b>Credentials held</b><ul>{creds}</ul></div>"
            f"{_history(agent) if agent else ''}</div>")


def profiles(world) -> str:
    c = world.credentials
    cards = [
        profile_card("Souq Bloom Support Agent", "DOO-style support agent · decides refunds", world.support.did,
                     [c["support_authority"]], world, world.support),
        profile_card("Layla's Assistant", "Personal AI agent acting for Layla", world.assistant.did,
                     world.assistant.authority + world.assistant.evidence, world, world.assistant),
        profile_card("Souq Bloom", "Merchant · trust anchor · issues and revokes credentials", world.merchant.did, [], world,
                     note="Publishes a signed revocation list (Bitstring Status List)."),
        profile_card("Layla", "Customer · delegates to her assistant", world.layla.did, [c["customer"]], world),
        profile_card("SwiftDrop Courier", "Trusted attester for deliveries", world.courier.did, [], world, world.courier),
        profile_card("Noura (Supervisor)", "Human who approves escalations", world.supervisor.did, [c["supervisor"]], world),
    ]
    return f"<div class='td-grid'>{''.join(cards)}</div>"


def pretty_json(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False)


ARCHITECTURE = """
<div id='how' class='td-label'>How it works</div>
<div class='td-h'>From a signed message to a <em>decision</em> you can explain</div>
<div class='td-steps'>
 <div><h3>Identity</h3><p>Every party has an Ed25519 key. Its W3C <code>did:key</code> <i>is</i> the public key, so anyone can verify a signature from the DID alone.</p></div>
 <div><h3>Claims</h3><p>Signed W3C Verifiable Credentials 2.0 (<code>eddsa-jcs-2022</code>): authority, orders, delegation, courier attestations, vouches, receipts.</p></div>
 <div><h3>Verification</h3><p>Signature valid, signer is the issuer, chain reaches a trust anchor, authority only narrows, not revoked, fresh and not replayed.</p></div>
 <div><h3>Policy</h3><p>A readable YAML file turns verified evidence into accept, refuse or escalate, with a full trace. No scores. No LLM in the decision.</p></div>
</div>
"""
