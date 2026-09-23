"""Payment provider selection intelligence.

Selects among externally configured providers using capability and health data.
It never reads credentials, moves money, or treats an advertised capability as
proof that funds exist. Every provider must be injected by the deployment.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderSnapshot:
    name: str
    enabled: bool
    authenticated: bool
    supports_jod: bool
    supports_destination: bool
    available_balance_jod: float | None
    per_transaction_limit_jod: float | None
    daily_remaining_jod: float | None
    health: str = "UNKNOWN"


@dataclass(frozen=True)
class ProviderChoice:
    status: str
    provider: str | None
    reason: str
    candidates: list[str]


class ProviderSelector(Protocol):
    def snapshot(self) -> ProviderSnapshot:
        ...


def choose_provider(amount_jod: float, snapshots: list[ProviderSnapshot],
                    destination_ref: str) -> ProviderChoice:
    if amount_jod <= 0:
        return ProviderChoice("INVALID_AMOUNT", None, "Amount must be positive.", [])
    candidates = []
    for s in snapshots:
        if not (s.enabled and s.authenticated and s.supports_jod and s.supports_destination):
            continue
        if s.health.upper() not in {"HEALTHY", "OK"}:
            continue
        if s.available_balance_jod is not None and s.available_balance_jod < amount_jod:
            continue
        if s.per_transaction_limit_jod is not None and s.per_transaction_limit_jod < amount_jod:
            continue
        if s.daily_remaining_jod is not None and s.daily_remaining_jod < amount_jod:
            continue
        candidates.append(s)
    if not candidates:
        return ProviderChoice(
            "NO_EXECUTABLE_PROVIDER", None,
            "No externally configured provider passed all capability and funds checks.", []
        )
    candidates.sort(key=lambda x: (
        x.daily_remaining_jod is None,
        x.available_balance_jod is None,
        x.name,
    ))
    return ProviderChoice(
        "READY_FOR_PROVIDER_SELECTION", candidates[0].name,
        "Provider passed configured capability, health, limit and available-funds checks.",
        [x.name for x in candidates],
    )
