"""Economic autonomy governor.

A single deterministic governor for the economic path. It never submits
applications, moves money, or invents revenue.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .economic_control import EconomicBudget


class GovernorAction(str, Enum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    STOP = "STOP"


@dataclass(frozen=True)
class EconomicSignal:
    verified: bool
    expected_value: float
    execution_cost: float
    risk_score: float
    stale: bool = False


@dataclass(frozen=True)
class GovernorDecision:
    action: GovernorAction
    reason: str


def govern(signal: EconomicSignal, budget: EconomicBudget) -> GovernorDecision:
    if signal.stale:
        return GovernorDecision(GovernorAction.STOP, "STALE_OPPORTUNITY")
    if not signal.verified:
        return GovernorDecision(GovernorAction.HOLD, "NOT_VERIFIED")
    if signal.expected_value < 0 or signal.execution_cost < 0:
        return GovernorDecision(GovernorAction.STOP, "INVALID_ECONOMIC_VALUES")
    if signal.risk_score > budget.risk_score:
        return GovernorDecision(GovernorAction.STOP, "RISK_BUDGET_EXCEEDED")
    if signal.expected_value <= signal.execution_cost:
        return GovernorDecision(GovernorAction.HOLD, "VALUE_NOT_ABOVE_COST")
    return GovernorDecision(GovernorAction.ALLOW, "ECONOMICALLY_ELIGIBLE")
