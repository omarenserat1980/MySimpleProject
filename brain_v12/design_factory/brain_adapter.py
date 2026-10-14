"""Plan and bounded-step adapter for Brain's CognitiveLoop."""
from __future__ import annotations

from .plan import prepare_design_plan
from .execution import initialize_execution, execute_next_step
from .simulator import simulate_step

TOOL_CATALOG_ITEM = {
    "id": "design.plan",
    "name": "Prepare governed engineering design plan",
    "risk": "low",
    "permission": None,
    "execution_mode": "plan_only",
}


class DesignFactoryAdapter:
    """Expose side-effect-free planning and a fail-closed one-step ledger."""

    tool_catalog_item = TOOL_CATALOG_ITEM

    def execute(self, params: dict | None = None) -> dict:
        params = params if isinstance(params, dict) else {}
        mode = params.get("mode", "plan")
        if mode == "step":
            return self._step(params)
        if mode != "plan":
            return {
                "ok": False, "status": "BLOCKED", "tool": TOOL_CATALOG_ITEM["id"],
                "error": "UNSUPPORTED_MODE", "data": None,
            }

        task = params.get("task", params.get("goal", ""))
        if not isinstance(task, str) or not task.strip():
            return {
                "ok": False, "status": "BLOCKED", "tool": TOOL_CATALOG_ITEM["id"],
                "error": "TASK_DESCRIPTION_REQUIRED", "data": None,
            }
        try:
            plan = prepare_design_plan(task)
            ledger = initialize_execution(plan)
        except (ValueError, OSError) as exc:
            return {
                "ok": False, "status": "BLOCKED", "tool": TOOL_CATALOG_ITEM["id"],
                "error": str(exc), "data": None,
            }
        return {
            "ok": True,
            "status": "PLANNED",
            "tool": TOOL_CATALOG_ITEM["id"],
            "data": plan,
            "execution_ledger": ledger,
            "execution_started": False,
        }

    def _step(self, params: dict) -> dict:
        """Advance one step. Simulation requires explicit mode and authorization."""
        state = params.get("execution_ledger")
        if not isinstance(state, dict):
            return {
                "ok": False, "status": "BLOCKED", "tool": TOOL_CATALOG_ITEM["id"],
                "error": "EXECUTION_LEDGER_REQUIRED", "data": None,
            }

        dry_run = params.get("dry_run", True) is not False
        authorize = params.get("authorize") is True
        executor_mode = params.get("executor_mode", "none")
        executor = None
        if not dry_run and authorize and executor_mode == "simulation":
            executor = simulate_step
        elif executor_mode not in {"none", "simulation"}:
            return {
                "ok": False, "status": "BLOCKED", "tool": TOOL_CATALOG_ITEM["id"],
                "error": "UNSUPPORTED_EXECUTOR_MODE", "data": None,
            }

        result = execute_next_step(
            state,
            executor=executor,
            authorize=authorize,
            dry_run=dry_run,
        )
        status = result.get("status", "BLOCKED")
        return {
            "ok": status not in {"BLOCKED", "FAILED"},
            "status": status,
            "tool": TOOL_CATALOG_ITEM["id"],
            "execution_ledger": result,
            "execution_started": bool(result.get("execution_started")),
        }
