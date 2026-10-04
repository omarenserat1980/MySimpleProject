"""Unified BRAIN commercial readiness gate.

The gate reports facts only. It never activates providers or claims revenue.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from brain.provider_hub.evidence import CommercialEvidenceGate
from brain.provider_hub.lifecycle import ProviderRecord


@dataclass(frozen=True)
class CommercialReadiness:
    public_api: bool
    auth_verified: bool
    trial_enforced: bool
    order_flow_verified: bool
    payment_provider_active: bool
    payment_verification_live: bool
    delivery_verified: bool
    evidence_generated: bool
    status: str
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate(
    *,
    public_api: bool,
    auth_verified: bool,
    trial_enforced: bool,
    order_flow_verified: bool,
    payment_provider: ProviderRecord | None,
    payment_verification_live: bool,
    delivery_verified: bool,
    evidence_gate: CommercialEvidenceGate,
    order_id: str,
) -> CommercialReadiness:
    blockers: list[str] = []
    payment_active = bool(payment_provider and payment_provider.state == "ACTIVE")
    evidence_generated = bool(evidence_gate.for_order(order_id))

    checks = {
        "PUBLIC_API_NOT_VERIFIED": public_api,
        "AUTH_NOT_VERIFIED": auth_verified,
        "TRIAL_NOT_ENFORCED": trial_enforced,
        "ORDER_FLOW_NOT_VERIFIED": order_flow_verified,
        "PAYMENT_PROVIDER_NOT_ACTIVE": payment_active,
        "PAYMENT_VERIFICATION_NOT_LIVE": payment_verification_live,
        "DELIVERY_NOT_VERIFIED": delivery_verified,
        "EVIDENCE_NOT_GENERATED": evidence_generated,
    }
    blockers.extend(name for name, ok in checks.items() if not ok)

    status = "COMMERCIAL_READY" if not blockers else "COMMERCIAL_LAUNCH_BLOCKED"
    return CommercialReadiness(
        public_api=public_api,
        auth_verified=auth_verified,
        trial_enforced=trial_enforced,
        order_flow_verified=order_flow_verified,
        payment_provider_active=payment_active,
        payment_verification_live=payment_verification_live,
        delivery_verified=delivery_verified,
        evidence_generated=evidence_generated,
        status=status,
        blockers=tuple(blockers),
    )
