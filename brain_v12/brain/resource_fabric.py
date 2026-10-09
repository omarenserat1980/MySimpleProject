from __future__ import annotations

"""Composable resource fabric with strict resource-state normalization."""

from dataclasses import dataclass, field
from enum import Enum
from time import time
from uuid import uuid4


class ResourceKind(str, Enum):
    COMPUTE = "compute"
    MEMORY = "memory"
    ACCELERATOR = "accelerator"
    STORAGE = "storage"
    NETWORK = "network"
    SECURITY = "security"


class ResourceState(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    ATTACHED = "ATTACHED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


def normalize_resource_state(value: ResourceState | str) -> ResourceState:
    if isinstance(value, ResourceState):
        return value
    try:
        return ResourceState(str(value).upper())
    except ValueError as exc:
        raise ValueError("INVALID_RESOURCE_STATE") from exc


@dataclass(frozen=True)
class ResourceSpec:
    resource_id: str
    kind: ResourceKind
    provider_id: str
    capacity: int
    unit: str
    attributes: dict[str, object] = field(default_factory=dict)
    state: ResourceState = ResourceState.AVAILABLE

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", normalize_resource_state(self.state))
        if self.capacity < 0:
            raise ValueError("RESOURCE_CAPACITY_MUST_BE_NONNEGATIVE")

    def public(self) -> dict:
        return {"resource_id": self.resource_id, "kind": self.kind.value,
                "provider_id": self.provider_id, "capacity": self.capacity,
                "unit": self.unit, "attributes": dict(self.attributes),
                "state": self.state.value}


@dataclass(frozen=True)
class ResourceRequest:
    kind: ResourceKind
    amount: int
    unit: str
    attributes: dict[str, object] = field(default_factory=dict)
    required: bool = True
    co_locate_key: str | None = None

    def public(self) -> dict:
        return {"kind": self.kind.value, "amount": self.amount, "unit": self.unit,
                "attributes": dict(self.attributes), "required": self.required,
                "co_locate_key": self.co_locate_key}


@dataclass(frozen=True)
class ResourceReservation:
    reservation_id: str
    intent_id: str
    allocations: dict[str, int]
    created_at: float
    expires_at: float
    status: str = "RESERVED"

    @property
    def resource_ids(self) -> tuple[str, ...]:
        return tuple(self.allocations)

    def public(self) -> dict:
        return {"reservation_id": self.reservation_id, "intent_id": self.intent_id,
                "resource_ids": list(self.allocations),
                "allocations": dict(self.allocations), "created_at": self.created_at,
                "expires_at": self.expires_at, "status": self.status}


class ResourceFabric:
    """Deterministic control-plane model for composable Brain resources."""

    def __init__(self, lease_seconds: int = 300):
        self.lease_seconds = max(1, int(lease_seconds))
        self.resources: dict[str, ResourceSpec] = {}
        self.reservations: dict[str, ResourceReservation] = {}
        self.intents: dict[str, dict] = {}

    def register(self, spec: ResourceSpec) -> dict:
        spec = ResourceSpec(spec.resource_id, spec.kind, spec.provider_id, spec.capacity,
                            spec.unit, dict(spec.attributes), normalize_resource_state(spec.state))
        self.resources[spec.resource_id] = spec
        return {"ok": True, "status": "REGISTERED", "resource": spec.public()}

    def register_many(self, specs: list[ResourceSpec]) -> dict:
        for spec in specs:
            self.register(spec)
        return {"ok": True, "status": "REGISTERED", "count": len(specs)}

    def unregister(self, resource_id: str) -> dict:
        if any(resource_id in r.resource_ids and r.status == "RESERVED"
               for r in self.reservations.values()):
            return {"ok": False, "status": "RESOURCE_RESERVED", "resource_id": resource_id}
        existed = self.resources.pop(resource_id, None) is not None
        return {"ok": existed, "status": "UNREGISTERED" if existed else "NOT_FOUND",
                "resource_id": resource_id}

    @staticmethod
    def _matches(spec: ResourceSpec, request: ResourceRequest) -> bool:
        if spec.kind != request.kind or spec.unit != request.unit:
            return False
        if spec.state not in {ResourceState.AVAILABLE, ResourceState.DEGRADED}:
            return False
        if spec.capacity < request.amount:
            return False
        for key, wanted in request.attributes.items():
            actual = spec.attributes.get(key)
            if isinstance(wanted, (int, float)) and isinstance(actual, (int, float)):
                if actual < wanted:
                    return False
            elif wanted != actual:
                return False
        return True

    def _reserved_amount(self, resource_id: str) -> int:
        return sum(
            reservation.allocations.get(resource_id, 0)
            for reservation in self.reservations.values()
            if reservation.status == "RESERVED"
        )

    def discover(self, request: ResourceRequest) -> list[ResourceSpec]:
        self.reap_expired()
        return [spec for spec in self.resources.values()
                if self._matches(spec, request)
                and spec.capacity - self._reserved_amount(spec.resource_id) >= request.amount]

    def plan(self, intent_id: str, requests: list[ResourceRequest]) -> dict:
        selected: list[dict[str, int]] = []
        used: set[str] = set()
        failures: list[dict] = []
        placements: dict[str, str] = {}
        for request in requests:
            candidates = [spec for spec in self.discover(request) if spec.resource_id not in used]
            if request.co_locate_key:
                existing_provider = placements.get(request.co_locate_key)
                if existing_provider is not None:
                    candidates = [s for s in candidates
                                  if s.attributes.get("blade_id", s.provider_id) == existing_provider]
            candidates.sort(key=lambda s: (0 if s.state == ResourceState.AVAILABLE else 1,
                                           s.capacity - request.amount, s.resource_id))
            if not candidates:
                if request.required:
                    failures.append({"request": request.public(), "status": "NO_MATCH"})
                continue
            chosen = candidates[0]
            selected.append({"resource_id": chosen.resource_id, "amount": request.amount})
            used.add(chosen.resource_id)
            if request.co_locate_key:
                placements[request.co_locate_key] = chosen.attributes.get(
                    "blade_id", chosen.provider_id)
        return {"ok": not failures, "status": "PLAN_READY" if not failures else "PLAN_BLOCKED",
                "intent_id": intent_id, "allocations": selected,
                "resource_ids": [x["resource_id"] for x in selected],
                "placements": placements, "failures": failures}

    def reserve(self, intent_id: str, resource_ids: list[str] | None = None,
                ttl_seconds: int | None = None, allocations: list[dict] | None = None) -> dict:
        self.reap_expired()
        if allocations is None:
            allocations = [{"resource_id": rid, "amount": self.resources[rid].capacity}
                           for rid in (resource_ids or [])]
        normalized: dict[str, int] = {}
        for item in allocations:
            rid = str(item["resource_id"])
            amount = int(item["amount"])
            if rid not in self.resources:
                return {"ok": False, "status": "RESOURCE_NOT_FOUND", "missing": [rid]}
            if amount <= 0:
                return {"ok": False, "status": "INVALID_ALLOCATION", "resource_id": rid}
            normalized[rid] = normalized.get(rid, 0) + amount
        for rid, amount in normalized.items():
            available = self.resources[rid].capacity - self._reserved_amount(rid)
            if amount > available:
                return {"ok": False, "status": "RESOURCE_BUSY",
                        "resource_id": rid, "requested": amount, "available": available}
        now = time()
        reservation = ResourceReservation(
            reservation_id=f"rsv-{uuid4().hex[:12]}", intent_id=intent_id,
            allocations=normalized, created_at=now,
            expires_at=now + max(1, int(ttl_seconds or self.lease_seconds)))
        self.reservations[reservation.reservation_id] = reservation
        self.intents[intent_id] = {"intent_id": intent_id, "resource_ids": list(normalized),
                                   "allocations": dict(normalized), "status": "RESERVED",
                                   "updated_at": now}
        return {"ok": True, "status": "RESERVED", "reservation": reservation.public()}

    def release(self, reservation_id: str) -> dict:
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            return {"ok": False, "status": "RESERVATION_NOT_FOUND",
                    "reservation_id": reservation_id}
        if reservation.status != "RESERVED":
            return {"ok": True, "status": reservation.status, "reservation_id": reservation_id}
        self.reservations[reservation_id] = ResourceReservation(
            reservation.reservation_id, reservation.intent_id, reservation.allocations,
            reservation.created_at, reservation.expires_at, "RELEASED")
        if reservation.intent_id in self.intents:
            self.intents[reservation.intent_id]["status"] = "RELEASED"
            self.intents[reservation.intent_id]["updated_at"] = time()
        return {"ok": True, "status": "RELEASED", "reservation_id": reservation_id}

    def reap_expired(self, now: float | None = None) -> list[str]:
        now = time() if now is None else now
        expired = []
        for rid, reservation in list(self.reservations.items()):
            if reservation.status == "RESERVED" and reservation.expires_at <= now:
                self.reservations[rid] = ResourceReservation(
                    reservation.reservation_id, reservation.intent_id, reservation.allocations,
                    reservation.created_at, reservation.expires_at, "EXPIRED")
                if reservation.intent_id in self.intents:
                    self.intents[reservation.intent_id]["status"] = "EXPIRED"
                    self.intents[reservation.intent_id]["updated_at"] = now
                expired.append(rid)
        return expired

    def compose(self, intent_id: str, requests: list[ResourceRequest],
                ttl_seconds: int | None = None) -> dict:
        plan = self.plan(intent_id, requests)
        if not plan["ok"]:
            self.intents[intent_id] = {"intent_id": intent_id, "status": "BLOCKED",
                                       "resource_ids": [], "allocations": [], "failures": plan["failures"],
                                       "updated_at": time()}
            return plan
        reservation = self.reserve(intent_id, ttl_seconds=ttl_seconds, allocations=plan["allocations"])
        if not reservation["ok"]:
            return {"ok": False, "status": "COMPOSITION_RACE", "plan": plan, "reservation": reservation}
        self.intents[intent_id]["status"] = "COMPOSED"
        self.intents[intent_id]["updated_at"] = time()
        return {"ok": True, "status": "COMPOSED", "intent_id": intent_id,
                "resource_ids": plan["resource_ids"], "allocations": plan["allocations"],
                "reservation": reservation["reservation"]}

    def federated_capacity(self, *, include_degraded: bool = True) -> dict:
        self.reap_expired()
        totals: dict[str, dict[str, int]] = {}
        providers: dict[str, dict] = {}
        for spec in self.resources.values():
            key = f"{spec.kind.value}:{spec.unit}"
            row = totals.setdefault(key, {"capacity": 0, "reserved": 0, "available": 0})
            reserved = self._reserved_amount(spec.resource_id)
            row["capacity"] += int(spec.capacity)
            row["reserved"] += reserved
            if spec.state == ResourceState.AVAILABLE or (include_degraded and spec.state == ResourceState.DEGRADED):
                row["available"] += max(0, int(spec.capacity) - reserved)
            provider = providers.setdefault(spec.provider_id, {"resources": 0, "kinds": {}})
            provider["resources"] += 1
            provider["kinds"][spec.kind.value] = provider["kinds"].get(spec.kind.value, 0) + int(spec.capacity)
        return {"ok": True, "status": "READY", "real_capacity": totals, "providers": providers,
                "resource_count": len(self.resources),
                "reserved_resource_count": sum(r.status == "RESERVED" for r in self.reservations.values())}

    def provider_capacity(self, provider_id: str) -> dict:
        rows = [s for s in self.resources.values() if s.provider_id == provider_id]
        if not rows:
            return {"ok": False, "status": "PROVIDER_NOT_FOUND", "provider_id": provider_id}
        return self._capacity_for_specs(rows, provider_id)

    def _capacity_for_specs(self, specs: list[ResourceSpec], provider_id: str) -> dict:
        totals: dict[str, dict[str, int]] = {}
        for spec in specs:
            key = f"{spec.kind.value}:{spec.unit}"
            reserved = self._reserved_amount(spec.resource_id)
            row = totals.setdefault(key, {"capacity": 0, "reserved": 0, "available": 0})
            row["capacity"] += int(spec.capacity)
            row["reserved"] += reserved
            if spec.state in {ResourceState.AVAILABLE, ResourceState.DEGRADED}:
                row["available"] += max(0, int(spec.capacity) - reserved)
        return {"ok": True, "status": "READY", "provider_id": provider_id, "real_capacity": totals}

    def inspect(self) -> dict:
        self.reap_expired()
        by_kind: dict[str, int] = {}
        for spec in self.resources.values():
            by_kind[spec.kind.value] = by_kind.get(spec.kind.value, 0) + 1
        return {"ok": True, "status": "READY", "resource_count": len(self.resources),
                "reservation_count": sum(r.status == "RESERVED" for r in self.reservations.values()),
                "intent_count": len(self.intents), "by_kind": by_kind,
                "resources": [r.public() for r in self.resources.values()],
                "reservations": [r.public() for r in self.reservations.values() if r.status == "RESERVED"],
                "intents": list(self.intents.values())}
