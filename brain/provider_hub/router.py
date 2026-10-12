"""BRAIN Provider Hub runtime router.

Pure routing policy: no credentials and no external network calls.
Real adapters plug into this contract and return evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ACTIVE_STATES = {"VERIFIED", "ACTIVE"}
FAIL_STATES = {"DEGRADED", "FAILED", "UNAVAILABLE"}


@dataclass(frozen=True)
class Provider:
    id: str
    status: str
    priority: int
    capabilities: tuple[str, ...] = ()


class ProviderRouter:
    def __init__(self, providers: list[Provider]):
        self.providers = providers

    def choose(self, capability: str) -> Provider:
        candidates = [
            p for p in self.providers
            if capability in p.capabilities and p.status in ACTIVE_STATES
        ]
        if not candidates:
            raise RuntimeError(f"NO_VERIFIED_PROVIDER:{capability}")
        return sorted(candidates, key=lambda p: p.priority)[0]

    def failover_order(self, capability: str, failed_id: str) -> list[Provider]:
        candidates = [
            p for p in self.providers
            if capability in p.capabilities
            and p.id != failed_id
            and p.status in ACTIVE_STATES
        ]
        return sorted(candidates, key=lambda p: p.priority)

    @staticmethod
    def payment_guard(
        *,
        order_id: str,
        payment_state: str,
        provider_reference: str | None,
        verified_evidence: dict[str, Any] | None,
    ) -> str:
        if payment_state == "PAYMENT_VERIFIED" and not verified_evidence:
            raise ValueError("PAYMENT_VERIFIED_REQUIRES_EVIDENCE")
        if payment_state == "PAYMENT_VERIFIED" and not provider_reference:
            raise ValueError("PAYMENT_VERIFIED_REQUIRES_PROVIDER_REFERENCE")
        return order_id
