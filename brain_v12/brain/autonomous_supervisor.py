from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AutonomousStep:
    name: str
    tool: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"
    result: Optional[Dict[str, Any]] = None


class BrainAutonomousSupervisor:
    """Governed discover→execute→verify→repair loop over BrainAI tools."""

    def __init__(self, brain, max_steps: int = 8):
        self.brain = brain
        self.max_steps = max(1, int(max_steps))

    def run(self, plan: List[Dict[str, Any]], approved: bool = False) -> Dict[str, Any]:
        steps: List[AutonomousStep] = []
        for item in plan[: self.max_steps]:
            step = AutonomousStep(
                name=str(item.get("name") or item.get("tool") or "step"),
                tool=str(item.get("tool", "")),
                params=item.get("params") if isinstance(item.get("params"), dict) else {},
            )
            if not step.tool:
                step.status = "FAILED"
                step.result = {"ok": False, "status": "INVALID_PLAN"}
                steps.append(step)
                continue
            outcome = self.brain.execute_tool(step.tool, step.params, approved=approved)
            step.result = outcome
            step.status = "SUCCESS" if self.brain._verify_tool_outcome(outcome) else str(outcome.get("status", "FAILED"))
            steps.append(step)
            if step.status in {"WAITING_APPROVAL", "WAITING_PERMISSION"}:
                break
        ok = bool(steps) and all(s.status == "SUCCESS" for s in steps)
        return {
            "ok": ok,
            "status": "VERIFIED_COMPLETED" if ok else "AUTONOMOUS_RUN_INCOMPLETE",
            "steps": [s.__dict__ for s in steps],
            "evidence": [{"tool": s.tool, "status": s.status, "verified": s.status == "SUCCESS"} for s in steps],
        }

    def discover_and_run(self, query: str, approved: bool = False) -> Dict[str, Any]:
        discovery = self.brain.execute_tool("github.discover", {"query": query})
        if not discovery.get("ok"):
            return {"ok": False, "status": "DISCOVERY_FAILED", "discovery": discovery}
        candidates = discovery.get("candidates") or []
        if not candidates:
            return {"ok": False, "status": "NO_TOOL_FOUND", "discovery": discovery}
        selected = candidates[0]
        return self.run([{"name": "discovered", "tool": selected["brain_tool"], "params": {}}], approved=approved) | {"discovery": discovery}
