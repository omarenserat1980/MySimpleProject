"""Capability-aware path selection.

Bridges PathEvolutionRegistry with CapabilityRegistry without granting permissions.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class RouteDecision:
    path_id: str
    executor_id: str | None
    reason: str

class CapabilityPathRouter:
    def __init__(self, paths, capabilities):
        self.paths = paths
        self.capabilities = capabilities

    def choose(self, goal: str, required_capabilities: Iterable[str] = ()) -> RouteDecision | None:
        path = self.paths.best(goal)
        if path is None:
            return None
        required = set(required_capabilities)
        if not required:
            return RouteDecision(path.path_id, None, "best verified path")
        candidates = self.capabilities.select(required)
        if not candidates:
            return RouteDecision(path.path_id, None, "path selected; no authorized worker currently satisfies capabilities")
        return RouteDecision(path.path_id, candidates[0].executor_id, "best path + authorized capability match")
