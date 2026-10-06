"""Unified request-to-capability evolution pipeline.

This is the single entry point for request-driven Brain growth. It advances the
request depth, computes the capability delta, and returns an execution plan.
It does not build anything until the request actually requires it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from brain_v12.self_healing.request_depth_controller import RequestDepthController
from brain_v12.self_healing.capability_evolution_planner import CapabilityEvolutionPlanner


@dataclass(frozen=True)
class GrowthPlan:
    request_number: int
    depth: int
    required_capabilities: tuple[str, ...]
    new_capabilities: tuple[str, ...]
    actions: tuple[dict[str, Any], ...]


class RequestDrivenGrowth:
    def __init__(
        self,
        depth_controller: RequestDepthController | None = None,
        capability_planner: CapabilityEvolutionPlanner | None = None,
    ) -> None:
        self.depth_controller = depth_controller or RequestDepthController()
        self.capability_planner = capability_planner or CapabilityEvolutionPlanner()

    def plan(self, request: str) -> GrowthPlan:
        decision = self.depth_controller.decide(request)
        plan = self.capability_planner.plan(
            request,
            list(decision.required_capabilities),
            decision.depth,
        )
        return GrowthPlan(
            request_number=decision.request_number,
            depth=decision.depth,
            required_capabilities=tuple(decision.required_capabilities),
            new_capabilities=tuple(plan["new_capability_delta"]),
            actions=tuple(plan["actions"]),
        )

    def commit(self, request: str, growth: GrowthPlan) -> dict[str, Any]:
        decision = self.depth_controller.decide(request)
        # Commit the exact request/depth pair rather than trusting a later
        # re-classification to produce the same result.
        decision = type(decision)(
            growth.request_number,
            decision.previous_depth,
            growth.depth,
            decision.reason,
            growth.required_capabilities,
            growth.new_capabilities,
        )
        self.depth_controller.commit(request, decision)
        plan = self.capability_planner.plan(
            request, list(growth.required_capabilities), growth.depth
        )
        return self.capability_planner.record(plan)
