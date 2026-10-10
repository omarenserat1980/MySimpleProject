"""Cost-gated cloud capacity planning for Electronic Brain.

This module plans cloud-backed virtual hardware; it deliberately does not
create billable resources. Provisioning must be implemented by a provider
adapter and must pass the explicit cost/eligibility gate first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class Component(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"


class Provider(str, Enum):
    AZURE = "azure"
    GENERIC = "generic"


@dataclass(frozen=True)
class HardwareRequest:
    """Minimum virtual hardware requested by a Brain workload."""
    cpu_cores: int = 2
    memory_gib: float = 4.0
    storage_gib: int = 64
    network_required: bool = True
    gpu_required: bool = False

    def validate(self) -> None:
        if self.cpu_cores < 1 or self.memory_gib <= 0 or self.storage_gib < 1:
            raise ValueError("INVALID_HARDWARE_REQUEST")


@dataclass(frozen=True)
class CloudCapacity:
    """A provider SKU/capacity offer, not a claim that it is currently available."""
    provider: Provider
    sku: str
    cpu_cores: int
    memory_gib: float
    storage_gib: int
    network: bool = True
    gpu: bool = False
    free_eligible: bool = False
    region: str | None = None
    estimated_monthly_cost: float | None = None
    currency: str = "USD"


@dataclass(frozen=True)
class CostPolicy:
    """Fail-closed policy: no paid provisioning without explicit approval."""
    allow_paid: bool = False
    free_entitlement_verified: bool = False
    max_monthly_cost: float = 0.0
    currency: str = "USD"


@dataclass
class CapacityPlan:
    status: str
    selected: CloudCapacity | None = None
    reasons: list[str] = field(default_factory=list)
    provisioning_allowed: bool = False

    def to_dict(self) -> dict:
        selected = None
        if self.selected:
            selected = {
                "provider": self.selected.provider.value,
                "sku": self.selected.sku,
                "cpu_cores": self.selected.cpu_cores,
                "memory_gib": self.selected.memory_gib,
                "storage_gib": self.selected.storage_gib,
                "region": self.selected.region,
                "estimated_monthly_cost": self.selected.estimated_monthly_cost,
                "currency": self.selected.currency,
            }
        return {
            "status": self.status,
            "selected": selected,
            "reasons": list(self.reasons),
            "provisioning_allowed": self.provisioning_allowed,
        }


def _fits(request: HardwareRequest, capacity: CloudCapacity) -> bool:
    return (
        capacity.cpu_cores >= request.cpu_cores
        and capacity.memory_gib >= request.memory_gib
        and capacity.storage_gib >= request.storage_gib
        and (not request.network_required or capacity.network)
        and (not request.gpu_required or capacity.gpu)
    )


def plan_capacity(
    request: HardwareRequest,
    offers: Iterable[CloudCapacity],
    policy: CostPolicy,
) -> CapacityPlan:
    """Choose a suitable offer without deploying anything.

    Free offers are eligible only when the account's free entitlement is
    verified. Paid offers require explicit approval, a known estimate, the
    same currency as policy, and a cost within the configured ceiling.
    """
    request.validate()
    offers = [offer for offer in offers if _fits(request, offer)]
    if not offers:
        return CapacityPlan("BLOCKED_NO_CAPACITY", reasons=["NO_OFFER_MATCHES_REQUEST"])

    eligible: list[CloudCapacity] = []
    blocked: list[str] = []
    for offer in offers:
        if offer.free_eligible:
            if policy.free_entitlement_verified:
                eligible.append(offer)
            else:
                blocked.append(f"FREE_ENTITLEMENT_UNVERIFIED:{offer.provider.value}:{offer.sku}")
            continue
        if not policy.allow_paid:
            blocked.append(f"PAID_PROVISIONING_NOT_APPROVED:{offer.provider.value}:{offer.sku}")
            continue
        if offer.estimated_monthly_cost is None:
            blocked.append(f"COST_ESTIMATE_MISSING:{offer.provider.value}:{offer.sku}")
            continue
        if offer.currency != policy.currency:
            blocked.append(f"CURRENCY_MISMATCH:{offer.provider.value}:{offer.sku}")
            continue
        if offer.estimated_monthly_cost > policy.max_monthly_cost:
            blocked.append(f"COST_LIMIT_EXCEEDED:{offer.provider.value}:{offer.sku}")
            continue
        eligible.append(offer)

    if not eligible:
        return CapacityPlan("BLOCKED_COST_OR_ENTITLEMENT_GATE", reasons=blocked or ["NO_ELIGIBLE_OFFER"])

    # Prefer free eligible offers, then smallest RAM/CPU footprint and cost.
    eligible.sort(key=lambda x: (
        not x.free_eligible,
        x.memory_gib,
        x.cpu_cores,
        x.estimated_monthly_cost if x.estimated_monthly_cost is not None else 0.0,
    ))
    selected = eligible[0]
    return CapacityPlan(
        "PLAN_READY_NOT_PROVISIONED",
        selected=selected,
        reasons=["CAPACITY_MATCHED", "NO_CLOUD_RESOURCES_CREATED"],
        provisioning_allowed=False,
    )
