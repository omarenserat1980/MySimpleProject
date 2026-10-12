"""Provider adapter contracts for BRAIN.

Adapters implement this interface; the core never imports vendor SDKs directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class HealthResult:
    provider_id: str
    healthy: bool
    checked_at: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentResult:
    provider_id: str
    status: str
    provider_reference: str | None
    evidence: dict[str, Any]


class ProviderAdapter(Protocol):
    provider_id: str

    def health_check(self) -> HealthResult: ...

    def create_checkout(self, order_id: str, amount: str, currency: str) -> PaymentResult: ...

    def verify_payment(self, provider_reference: str) -> PaymentResult: ...


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, adapter: ProviderAdapter) -> None:
        if adapter.provider_id in self._adapters:
            raise ValueError(f"DUPLICATE_PROVIDER:{adapter.provider_id}")
        self._adapters[adapter.provider_id] = adapter

    def get(self, provider_id: str) -> ProviderAdapter:
        try:
            return self._adapters[provider_id]
        except KeyError as exc:
            raise KeyError(f"UNKNOWN_PROVIDER:{provider_id}") from exc

    def health(self) -> list[HealthResult]:
        return [adapter.health_check() for adapter in self._adapters.values()]
