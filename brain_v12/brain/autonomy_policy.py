"""Brain-first execution policy.

The Brain should prefer repairing and using its own maintained capabilities first,
then diversify across independent free/open-source executors, and only use paid
providers when commercial funding and explicit authorization are available.

This policy never creates permission to perform an external side effect.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BRAIN_OWNED = "BRAIN_OWNED"
FREE_DIVERSE = "FREE_DIVERSE"
PAID_EXTERNAL = "PAID_EXTERNAL"


@dataclass(frozen=True)
class AutonomyPolicy:
    allow_paid: bool = False
    allow_external_side_effects: bool = False
    prefer_brain_owned: bool = True
    require_independent_free_fallback: bool = True


def executor_tier(spec: Any) -> str:
    return str(spec.metadata.get("tier", FREE_DIVERSE))


def executor_allowed(
    spec: Any,
    *,
    policy: AutonomyPolicy,
    required_permissions: set[str] | None = None,
) -> bool:
    required = required_permissions or set()
    if not required.issubset(spec.permissions):
        return False

    metadata = spec.metadata
    if metadata.get("side_effect") and not policy.allow_external_side_effects:
        return False

    tier = executor_tier(spec)
    if tier == PAID_EXTERNAL and not policy.allow_paid:
        return False

    return True


def rank_key(spec: Any) -> tuple:
    tier_order = {
        BRAIN_OWNED: 0,
        FREE_DIVERSE: 1,
        PAID_EXTERNAL: 2,
    }
    return (
        tier_order.get(executor_tier(spec), 1),
        spec.priority,
        spec.cost_class,
        spec.executor_id,
    )
