from brain_v12.economics.economic_control import EconomicBudget
from brain_v12.economics.economic_governor import (
    EconomicSignal,
    GovernorAction,
    govern,
)


def test_govern_allows_positive_verified_value():
    d = govern(
        EconomicSignal(True, 10, 2, 0.2),
        EconomicBudget(2, 3, 0.5),
    )
    assert d.action == GovernorAction.ALLOW


def test_govern_stops_stale_opportunity():
    d = govern(
        EconomicSignal(True, 10, 2, 0.2, stale=True),
        EconomicBudget(2, 3, 0.5),
    )
    assert d.action == GovernorAction.STOP


def test_govern_holds_unverified_opportunity():
    d = govern(
        EconomicSignal(False, 10, 2, 0.2),
        EconomicBudget(2, 3, 0.5),
    )
    assert d.action == GovernorAction.HOLD
