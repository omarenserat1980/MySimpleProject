"""Small adapter contract for Brain runtimes to invoke the plan-only factory."""
from __future__ import annotations
from .plan import prepare_design_plan

TOOL_CATALOG_ITEM = {
    "id": "design.plan",
    "name": "Prepare governed engineering design plan",
    "risk": "low",
    "permission": None,
    "execution_mode": "plan_only",
}

class DesignFactoryAdapter:
    """Expose the factory as a typed, side-effect-free Brain tool."""

    tool_catalog_item = TOOL_CATALOG_ITEM

    def execute(self, params: dict | None = None) -> dict:
        params = params if isinstance(params, dict) else {}
        task = params.get("task", params.get("goal", ""))
        if not isinstance(task, str) or not task.strip():
            return {
                "ok": False,
                "status": "BLOCKED",
                "tool": TOOL_CATALOG_ITEM["id"],
                "error": "TASK_DESCRIPTION_REQUIRED",
                "data": None,
            }
        try:
            plan = prepare_design_plan(task)
        except (ValueError, OSError) as exc:
            return {
                "ok": False,
                "status": "BLOCKED",
                "tool": TOOL_CATALOG_ITEM["id"],
                "error": str(exc),
                "data": None,
            }
        return {
            "ok": True,
            "status": "PLANNED",
            "tool": TOOL_CATALOG_ITEM["id"],
            "data": plan,
            "execution_started": False,
        }
