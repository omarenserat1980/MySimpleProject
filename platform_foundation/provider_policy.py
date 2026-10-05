"""Provider roles for Brain runtime and media execution.

The local Brain executor is authoritative. External services such as Render are
optional auxiliary providers for bounded, non-authoritative work. GitHub Actions
is an evidence/verification surface, not a runtime dependency.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ProviderRole(str, Enum):
    PRIMARY = "PRIMARY"
    OPTIONAL_AUXILIARY = "OPTIONAL_AUXILIARY"
    VERIFICATION_ONLY = "VERIFICATION_ONLY"


class ProviderDecision(str, Enum):
    ALLOWED = "ALLOWED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    role: ProviderRole
    paid: bool = False
    available: bool = True


@dataclass(frozen=True)
class ProviderSelection:
    decision: ProviderDecision
    provider_id: str | None
    reason: str


class BrainProviderPolicy:
    """Fail-closed boundary between internal authority and external helpers."""

    PRIMARY_PROVIDER = "brain-local"

    def select(self, providers: list[ProviderDescriptor], *, purpose: str = "media") -> ProviderSelection:
        primary = next(
            (p for p in providers
             if p.provider_id == self.PRIMARY_PROVIDER
             and p.role == ProviderRole.PRIMARY
             and p.available),
            None,
        )
        if primary:
            return ProviderSelection(
                ProviderDecision.ALLOWED,
                primary.provider_id,
                "brain-local is the authoritative primary provider",
            )

        return ProviderSelection(
            ProviderDecision.BLOCKED,
            None,
            "authoritative Brain provider unavailable; external providers cannot silently replace it",
        )

    @staticmethod
    def auxiliary_status(provider: ProviderDescriptor) -> dict[str, object]:
        if provider.role != ProviderRole.OPTIONAL_AUXILIARY:
            raise ValueError("provider_is_not_optional_auxiliary")
        return {
            "provider_id": provider.provider_id,
            "role": provider.role.value,
            "available": provider.available,
            "paid": provider.paid,
            "authoritative": False,
            "required_for_brain_autonomy": False,
        }

    @staticmethod
    def verification_status(provider: ProviderDescriptor) -> dict[str, object]:
        if provider.role != ProviderRole.VERIFICATION_ONLY:
            raise ValueError("provider_is_not_verification_only")
        return {
            "provider_id": provider.provider_id,
            "role": provider.role.value,
            "available": provider.available,
            "authoritative": False,
            "required_for_brain_autonomy": False,
        }


__all__ = [
    "ProviderRole",
    "ProviderDecision",
    "ProviderDescriptor",
    "ProviderSelection",
    "BrainProviderPolicy",
]
