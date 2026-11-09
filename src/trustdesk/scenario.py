"""The Souq Bloom demo world: every identity, credential and status list.

Keys are seeded, so DIDs are stable across runs (handy for screenshots and
docs). Each `build_world()` call is a fresh, independent world, so UI sessions
and tests never interfere with each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .agents.assistant import AssistantAgent
from .agents.courier import CourierAgent
from .agents.support import HandleResult, SupportAgent, Supervisor
from .credentials import issue_credential, utcnow
from .delegation import Scope, delegate
from .identity import Identity
from .parser import ParsedRequest, parse
from .policy import Policy
from .status_list import StatusList, StatusRegistry

POLICY_PATH = Path(__file__).resolve().parents[2] / "policies" / "support_agent.yaml"
MERCHANT_STATUS = "https://souqbloom.example/credentials/status/1"
LAYLA_STATUS = "https://layla.example/delegations/status/1"


def _id(name: str) -> Identity:
    return Identity.from_seed(name, f"trustdesk-demo:{name}".encode())


@dataclass
class World:
    now: datetime
    merchant: Identity
    layla: Identity
    supervisor: Supervisor
    support: SupportAgent
    assistant: AssistantAgent
    courier: CourierAgent
    registry: StatusRegistry
    merchant_list: StatusList
    layla_list: StatusList
    policy: Policy
    credentials: dict[str, dict]
    status_index: dict[str, int]
    names: dict[str, str] = field(default_factory=dict)  # did -> display name

    # ---------------------------------------------------------------- trust management
    def publish(self) -> None:
        self.registry.publish(self.merchant_list.to_credential(now=self.clock()))
        self.registry.publish(self.layla_list.to_credential(now=self.clock()))

    def clock(self) -> datetime:
        return max(self.now, utcnow()) if self.now.tzinfo else self.now

    def revoke(self, key: str) -> None:
        """key: 'delegation' (Layla revokes her assistant) or 'support_authority' (merchant revokes its agent)."""
        lst = self.layla_list if key == "delegation" else self.merchant_list
        lst.revoke(self.status_index[key])
        self.publish()

    def reinstate(self, key: str) -> None:
        lst = self.layla_list if key == "delegation" else self.merchant_list
        lst.reinstate(self.status_index[key])
        self.publish()

    def is_revoked(self, key: str) -> bool:
        lst = self.layla_list if key == "delegation" else self.merchant_list
        return lst.is_set(self.status_index[key])

    def redelegate(self, *, max_amount: float, orders: list[str], days: int = 7) -> dict:
        """Layla re-scopes her assistant: a new delegation replaces the old one."""
        idx = self.layla_list.allocate()
        new = delegate(
            self.layla, parent=self.credentials["customer"], delegate_did=self.assistant.did,
            scope=Scope(actions=["refund.request", "order.lookup"], orders=orders, max_amount=max_amount, currency="AED"),
            valid_until=self.now + timedelta(days=days), status=self.layla_list.entry(idx), now=self.now,
        )
        self.layla_list.revoke(self.status_index["delegation"])  # old one stops working
        self.credentials["delegation"], self.status_index["delegation"] = new, idx
        self.assistant.authority = [self.credentials["customer"], new]
        self.publish()
        return new

    # ---------------------------------------------------------------- interactions
    def ask(self, text: str, *, parsed: ParsedRequest | None = None, include_evidence: bool = True,
            now: datetime | None = None) -> tuple[ParsedRequest, dict, HandleResult]:
        """Layla's assistant sends `text` to the support agent; returns (parsed, envelope, result)."""
        parsed = parsed or parse(text)
        env = self.assistant.request(self.support.did, text=text, parsed=parsed,
                                     include_evidence=include_evidence, now=now or self.clock())
        return parsed, env, self.support.handle(env, now=now or self.clock())

    def decide(self, escalation_id: str, *, approved: bool, note: str = ""):
        approval = self.supervisor.sign_decision(escalation_id, approved=approved, note=note, now=self.clock())
        return self.support.resolve(escalation_id, approval, self.supervisor.credential, now=self.clock())

    def name_of(self, did: str) -> str:
        return self.names.get(did, f"unknown ({did[:20]}…)")


def build_world(now: datetime | None = None) -> World:
    now = now or utcnow()
    merchant, layla = _id("Souq Bloom"), _id("Layla")
    support_id, assistant_id = _id("Souq Bloom Support Agent"), _id("Layla's Assistant")
    courier_id, supervisor_id = _id("SwiftDrop Courier"), _id("Noura (Supervisor)")

    registry = StatusRegistry()
    merchant_list = StatusList(merchant, MERCHANT_STATUS)
    layla_list = StatusList(layla, LAYLA_STATUS)
    index: dict[str, int] = {}
    creds: dict[str, dict] = {}

    index["support_authority"] = merchant_list.allocate()
    creds["support_authority"] = issue_credential(
        merchant, subject_did=support_id.did, types=["AuthorityCredential"], name="Customer support authority",
        claims={"role": "customer-support", "scope": Scope(
            actions=["refund.issue", "order.lookup"], orders=["*"], max_amount=300, currency="AED").to_dict()},
        valid_until=now + timedelta(days=90), status=merchant_list.entry(index["support_authority"]), now=now,
    )
    index["supervisor"] = merchant_list.allocate()
    creds["supervisor"] = issue_credential(
        merchant, subject_did=supervisor_id.did, types=["SupervisorCredential"], name="Refund supervisor",
        claims={"role": "refund-supervisor", "scope": Scope(
            actions=["refund.issue"], orders=["*"], max_amount=5000, currency="AED").to_dict()},
        valid_until=now + timedelta(days=365), status=merchant_list.entry(index["supervisor"]), now=now,
    )
    index["customer"] = merchant_list.allocate()
    creds["customer"] = issue_credential(
        merchant, subject_did=layla.did, types=["CustomerCredential"], name="Souq Bloom customer: orders",
        claims={"scope": Scope(actions=["refund.request", "order.lookup"], orders=["1042", "1043"],
                               max_amount=420, currency="AED").to_dict(),
                "orders": [{"id": "1042", "item": "Ceramic vase set + peonies", "total": 420},
                           {"id": "1043", "item": "Oud candle gift box", "total": 185}]},
        valid_until=now + timedelta(days=365), status=merchant_list.entry(index["customer"]), now=now,
    )
    index["delegation"] = layla_list.allocate()
    creds["delegation"] = delegate(
        layla, parent=creds["customer"], delegate_did=assistant_id.did,
        scope=Scope(actions=["refund.request", "order.lookup"], orders=["1042"], max_amount=400, currency="AED"),
        valid_until=now + timedelta(days=7), status=layla_list.entry(index["delegation"]), now=now,
    )

    courier = CourierAgent(courier_id)
    creds["attestation"] = courier.attest("1042", "delivered_damaged", photo=b"demo-photo-of-broken-vase", now=now)

    directory = {"souq_bloom": merchant.did, "swiftdrop": courier_id.did}
    policy = Policy.load(POLICY_PATH, directory)
    support = SupportAgent(support_id, authority=creds["support_authority"], policy=policy, status_registry=registry)
    assistant = AssistantAgent(assistant_id, authority=[creds["customer"], creds["delegation"]],
                               merchant_did=merchant.did, status_registry=registry)
    assistant.evidence = [creds["attestation"]]

    world = World(
        now=now, merchant=merchant, layla=layla, supervisor=Supervisor(supervisor_id, creds["supervisor"]),
        support=support, assistant=assistant, courier=courier, registry=registry,
        merchant_list=merchant_list, layla_list=layla_list, policy=policy, credentials=creds, status_index=index,
    )
    world.names = {i.did: i.name for i in (merchant, layla, support_id, assistant_id, courier_id, supervisor_id)}
    world.publish()
    return world
