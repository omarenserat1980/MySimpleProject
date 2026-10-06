"""Request-driven capability evolution planner.

The planner converts a new request into the smallest capability delta needed to
fulfil it. It never creates a script/app/adapter merely because a depth exists.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class CapabilityEvolutionPlanner:
    schema = "brain-capability-evolution/v1"

    def __init__(self, state_path: str | Path = ".brain/state/capability_evolution.json"):
        self.path = Path(state_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": self.schema, "capabilities": {}, "evolution": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema": self.schema, "capabilities": {}, "evolution": []}

    def plan(self, request: str, required: list[str], depth: int) -> dict[str, Any]:
        state = self.load()
        known = state.get("capabilities", {})
        delta = [cap for cap in required if cap not in known]
        actions = [
            {
                "capability": cap,
                "action": self._action_for(cap),
                "reason": "required_by_current_request",
                "depth": depth,
            }
            for cap in delta
        ]
        return {
            "schema": self.schema,
            "request": request[:2000],
            "depth": depth,
            "required": required,
            "new_capability_delta": delta,
            "actions": actions,
            "no_op_for_unused_capabilities": True,
        }

    @staticmethod
    def _action_for(capability: str) -> str:
        return {
            "script": "create_or_extend_script",
            "api": "create_or_extend_api",
            "app": "create_or_extend_application",
            "adapter": "create_or_extend_adapter",
            "diagnostics": "create_or_extend_diagnostics",
            "cloud": "create_or_extend_cloud_adapter",
            "media": "create_or_extend_media_capability",
            "agent": "create_or_extend_agent",
        }.get(capability, "create_or_extend_capability")

    def record(self, plan: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        for cap in plan["new_capability_delta"]:
            state.setdefault("capabilities", {})[cap] = {
                "status": "available_after_verification",
                "introduced_at_depth": plan["depth"],
            }
        state.setdefault("evolution", []).append({
            "timestamp": time.time(),
            "depth": plan["depth"],
            "delta": plan["new_capability_delta"],
        })
        state["evolution"] = state["evolution"][-100:]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        return state
