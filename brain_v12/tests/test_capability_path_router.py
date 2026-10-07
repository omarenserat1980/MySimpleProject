"""Tests for capability-aware path routing."""
from brain_v12.brain.capability_registry import CapabilityRegistry
from brain_v12.brain.capability_path_router import CapabilityPathRouter, RouteDecision

class FakePath:
    path_id="PATH-TERMUX-BRAIN"

class FakePaths:
    def best(self, goal):
        return FakePath() if goal == "connectivity" else None

def test_router_selects_authorized_worker():
    caps=CapabilityRegistry()
    caps.register("redmi3-01", {"python","device-task"})
    decision=CapabilityPathRouter(FakePaths(), caps).choose("connectivity", {"python"})
    assert isinstance(decision, RouteDecision)
    assert decision.executor_id == "redmi3-01"

def test_router_does_not_invent_permission():
    caps=CapabilityRegistry()
    caps.register("redmi3-01", {"python"})
    decision=CapabilityPathRouter(FakePaths(), caps).choose("connectivity", {"shell"})
    assert decision.executor_id is None
