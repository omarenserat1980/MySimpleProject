"""Fail-closed economics gate for Brain workloads.

This is a decision gate only: it never purchases capacity, sends money, mines, or
promotes estimated revenue into a realized-revenue ledger entry.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Mapping, Any


DEFAULT_REQUIRED_COSTS = ("electricity", "pool_fees", "hosting", "network", "other")


@dataclass(frozen=True)
class ProfitDecision:
    status: str
    allowed: bool
    expected_revenue: float | None
    total_cost: float | None
    expected_net: float | None
    reasons: tuple[str, ...]
    truth_level: str
    revenue_verified: bool = False


class ProfitGate:
    """Evaluate an economic workload without treating estimates as settlement."""

    def __init__(self, required_costs: tuple[str, ...] = DEFAULT_REQUIRED_COSTS) -> None:
        if not required_costs or any(not str(key).strip() for key in required_costs):
            raise ValueError("REQUIRED_COSTS_MUST_BE_NAMED")
        self.required_costs = tuple(dict.fromkeys(str(key) for key in required_costs))

    @staticmethod
    def _valid_number(value: Any) -> bool:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value)) and float(value) >= 0

    def evaluate(
        self,
        *,
        execution_mode: str,
        truth_level: str,
        expected_revenue: float | None,
        costs: Mapping[str, float | None] | None,
        provider_verified: bool,
        evidence_verified: bool,
        workload_is_economic: bool = True,
    ) -> dict[str, Any]:
        mode = str(execution_mode).upper()
        truth = str(truth_level).upper()
        reasons: list[str] = []
        revenue = expected_revenue
        costs = dict(costs or {})
        if not workload_is_economic:
            decision = ProfitDecision("UNKNOWN", False, None, None, None, ("NON_ECONOMIC_WORKLOAD_REQUIRES_SEPARATE_POLICY",), truth)
            return asdict(decision)
        if mode == "SIMULATOR" or truth == "SIMULATED":
            reasons.append("SIMULATION_IS_NOT_REVENUE")
        if not provider_verified:
            reasons.append("PROVIDER_NOT_VERIFIED")
        if truth not in {"DEVICE_ATTESTED", "EXTERNALLY_VERIFIED", "FINANCIALLY_SETTLED"}:
            reasons.append("TRUTH_LEVEL_NOT_VERIFIED_FOR_ECONOMICS")
        if not evidence_verified:
            reasons.append("INSUFFICIENT_VERIFIED_EVIDENCE")
        if revenue is None or not self._valid_number(revenue):
            reasons.append("EXPECTED_REVENUE_MISSING_OR_INVALID")
        missing = [key for key in self.required_costs if key not in costs or costs[key] is None or not self._valid_number(costs[key])]
        if missing:
            reasons.extend(f"COST_MISSING_OR_INVALID:{key}" for key in missing)
        if reasons:
            decision = ProfitDecision("BLOCKED", False, float(revenue) if self._valid_number(revenue) else None, None, None, tuple(reasons), truth)
            return asdict(decision)
        total_cost = sum(float(costs[key]) for key in self.required_costs)
        net = float(revenue) - total_cost
        if net <= 0:
            status = "LOSS"
            allowed = False
            reasons.append("NON_POSITIVE_EXPECTED_NET")
        else:
            status = "PROFITABLE"
            allowed = True
        decision = ProfitDecision(status, allowed, float(revenue), round(total_cost, 8), round(net, 8), tuple(reasons), truth)
        return asdict(decision)

    def kill_switch_required(self, decision: Mapping[str, Any], *, stale: bool = False, unsafe: bool = False) -> dict[str, Any]:
        status = str(decision.get("status", "UNKNOWN")).upper()
        stop = stale or unsafe or status in {"LOSS", "UNKNOWN", "BLOCKED", "NEEDS_MANUAL_REVIEW"}
        reasons = []
        if stale:
            reasons.append("RESOURCE_OR_TELEMETRY_STALE")
        if unsafe:
            reasons.append("UNSAFE_STATE")
        if status in {"LOSS", "UNKNOWN", "BLOCKED", "NEEDS_MANUAL_REVIEW"}:
            reasons.append(f"ECONOMIC_STATE_{status}")
        return {"stop": stop, "action": "STOP_PRESERVE_EVIDENCE_RELEASE_RESOURCE" if stop else "CONTINUE_GATED", "reasons": reasons}
