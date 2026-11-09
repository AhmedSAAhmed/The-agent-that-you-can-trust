"""Command-line walkthrough: `uv run python -m trustdesk.demo` (add `--verbose` for full traces)."""

from __future__ import annotations

import sys

from .attacks import run_all
from .policy import Decision
from .scenario import build_world

ICON = {"ACCEPT": "✅ ACCEPT", "REFUSE": "⛔ REFUSE", "ESCALATE": "🧑‍💼 ESCALATE", "BLOCKED": "🛡️ BLOCKED"}


def show(decision: Decision, verbose: bool) -> None:
    print(f"   → {ICON.get(decision.outcome, decision.outcome)}: {decision.reason}")
    rows = decision.trace if verbose else decision.failed
    for c in rows:
        print(f"      {'✔' if c.passed else '✘'} {c.name}: {c.detail}")
    if not verbose:
        print(f"      ({sum(c.passed for c in decision.trace)} checks passed)")


def main(argv: list[str] | None = None) -> int:
    verbose = "--verbose" in (argv if argv is not None else sys.argv[1:])
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    w = build_world()
    print("TrustDesk · Souq Bloom demo\n")
    for label, did in [("Merchant (trust anchor)", w.merchant.did), ("Support agent", w.support.did),
                       ("Layla's assistant", w.assistant.did), ("SwiftDrop courier", w.courier.did)]:
        print(f"  {label:<24} {did}")

    print("\n1) Layla's assistant checks it is really talking to Souq Bloom")
    checks = w.assistant.verify_counterparty(w.support.introduce(w.assistant.did))
    print(f"   → {'verified' if all(c.passed for c in checks) else 'NOT verified'} ({len(checks)} checks)")

    scenes = [
        ("2) Small refund with courier evidence", "Hi, I'm Layla's assistant. Order 1042 arrived with broken vases, please refund AED 250."),
        ("3) Larger refund, above the agent's own limit", "Refund AED 380 for order 1042 please, both vases were shattered."),
    ]
    escalation = None
    for title, text in scenes:
        print(f"\n{title}\n   \"{text}\"")
        parsed, _, res = w.ask(text)
        print(f"   {parsed.understood()}")
        show(res.decision, verbose)
        print(f"   reply: {res.reply['body']['text']}")
        escalation = res.escalation or escalation

    if escalation:
        print(f"\n4) Supervisor approves {escalation.id} with a signed decision")
        esc, checks, receipt = w.decide(escalation.id, approved=True, note="photo confirms damage")
        print(f"   → {esc.status} ({sum(c.passed for c in checks)}/{len(checks)} checks), receipt {receipt['outcome'] if receipt else '-'}")

    print("\n5) Layla revokes her assistant, then it tries again")
    w.revoke("delegation")
    _, _, res = w.ask("Refund AED 250 for order 1042")
    show(res.decision, verbose)

    print("\n6) Attack Lab")
    for r in run_all():
        mark = "🛡️" if r.defended else "⚠️"
        print(f"   {mark} {r.title:<44} {r.outcome:<9} caught by {r.caught_by}")
        if verbose:
            print(f"        {r.detail}")

    print(f"\nSupport agent history: {len(w.support.ledger.receipts)} signed receipts, chain head {w.support.ledger.head[:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
