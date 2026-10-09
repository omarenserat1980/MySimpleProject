"""Conservative, side-effect-free capacity gate for real Hyper-V operations.

This module only decides whether a requested startup-memory amount fits a budget.
It never allocates memory, reserves capacity, or starts/stops a VM.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class CapacityDecision:
    status: str
    requested_bytes: int | None
    safe_budget_bytes: int | None
    available_bytes: int | None
    host_reserve_bytes: int | None
    existing_commitments_bytes: int | None
    telemetry_age_seconds: float | None
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reasons"] = list(self.reasons)
        return result


def evaluate_capacity(
    *,
    available_bytes: int | None,
    host_reserve_bytes: int | None,
    existing_commitments_bytes: int | None,
    requested_startup_bytes: int | None,
    telemetry_captured_at: str | None,
    now: datetime | None = None,
    max_age_seconds: int = 60,
) -> CapacityDecision:
    """Evaluate a fresh host-memory observation. Unknown input always blocks."""
    reasons: list[str] = []
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        return CapacityDecision("BLOCKED", requested_startup_bytes, None, available_bytes,
                                host_reserve_bytes, existing_commitments_bytes, None,
                                ("Decision clock must include timezone information.",))

    age: float | None = None
    if not telemetry_captured_at:
        reasons.append("Memory telemetry timestamp is missing.")
    else:
        try:
            captured = datetime.fromisoformat(telemetry_captured_at.replace("Z", "+00:00"))
            if captured.tzinfo is None:
                raise ValueError("timestamp has no timezone")
            age = (now.astimezone(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds()
            if age < 0:
                reasons.append("Memory telemetry timestamp is in the future.")
            elif age > max_age_seconds:
                reasons.append(f"Memory telemetry is stale ({age:.1f}s > {max_age_seconds}s).")
        except (TypeError, ValueError):
            reasons.append("Memory telemetry timestamp is invalid or lacks a timezone.")

    values = {
        "available_bytes": available_bytes,
        "host_reserve_bytes": host_reserve_bytes,
        "existing_commitments_bytes": existing_commitments_bytes,
        "requested_startup_bytes": requested_startup_bytes,
    }
    for name, value in values.items():
        if value is None:
            reasons.append(f"{name} is unknown.")
        elif not isinstance(value, int) or isinstance(value, bool) or value < 0:
            reasons.append(f"{name} must be a non-negative integer.")
    if requested_startup_bytes == 0:
        reasons.append("requested_startup_bytes must be greater than zero.")

    if reasons:
        return CapacityDecision("BLOCKED", requested_startup_bytes, None, available_bytes,
                                host_reserve_bytes, existing_commitments_bytes, age,
                                tuple(reasons))

    assert available_bytes is not None
    assert host_reserve_bytes is not None
    assert existing_commitments_bytes is not None
    assert requested_startup_bytes is not None
    budget = available_bytes - host_reserve_bytes - existing_commitments_bytes
    if budget < 0:
        return CapacityDecision("BLOCKED", requested_startup_bytes, budget, available_bytes,
                                host_reserve_bytes, existing_commitments_bytes, age,
                                ("Host reserve and existing commitments exceed available memory.",))
    if requested_startup_bytes > budget:
        return CapacityDecision("BLOCKED", requested_startup_bytes, budget, available_bytes,
                                host_reserve_bytes, existing_commitments_bytes, age,
                                ("Requested startup memory exceeds the safe available budget.",))
    return CapacityDecision("ALLOW", requested_startup_bytes, budget, available_bytes,
                            host_reserve_bytes, existing_commitments_bytes, age,
                            ("Fresh telemetry and configured memory budget permit the request; no resources were reserved.",))
