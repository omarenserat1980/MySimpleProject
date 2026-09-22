"""Goal-driven Terminal Bridge V10.1.

Converts a natural-language objective into a conservative sequence of registered
actions, executes it through the Agent, observes outputs, and performs limited
recovery. It never invents shell commands or expands permissions.
"""
from typing import Any
from .agent_executor import execute_action

MAX_STEPS = 8
MAX_REPLANS = 2


class TerminalBridge:
    def __init__(self):
        self.last_run: dict[str, Any] = {"status": "IDLE", "steps": []}

    def plan(self, actions: list[str], objective: str = "") -> dict[str, Any]:
        clean = [str(a).strip() for a in actions if str(a).strip()][:MAX_STEPS]
        return {
            "status": "PLANNED",
            "objective": objective,
            "actions": clean,
            "max_steps": MAX_STEPS,
            "max_replans": MAX_REPLANS,
        }

    def auto_plan(self, objective: str) -> dict[str, Any]:
        t = objective.lower()
        actions = ["inspect", "termux_pwd", "termux_list"]
        if "اختبار" in t or "test" in t:
            actions.append("pytest_collect")
        if "git" in t or "مستودع" in t or "كود" in t:
            actions.append("git_status")
        if "ملفات" in t or "مشروع" in t or "project" in t:
            actions.append("workspace_tree")
        return self.plan(actions, objective)

    @staticmethod
    def _diagnose(result: dict[str, Any]) -> str:
        if result.get("error"):
            return str(result["error"])[:500]
        nested = result.get("result") or {}
        if isinstance(nested, dict):
            return str(
                nested.get("stderr")
                or nested.get("error")
                or nested.get("stdout")
                or "unknown execution failure"
            )[:500]
        return "unknown execution failure"

    def run(
        self,
        actions: list[str] | None = None,
        objective: str = "",
        timeout: int = 30,
        stop_on_failure: bool = True,
    ) -> dict[str, Any]:
        plan = self.auto_plan(objective) if not actions else self.plan(actions, objective)
        if not plan["actions"]:
            self.last_run = {"status": "EMPTY", "objective": objective, "steps": []}
            return self.last_run

        results = []
        replans = 0
        for index, action in enumerate(plan["actions"], start=1):
            final = execute_action(action, {"timeout": timeout})
            step = {
                "step": index,
                "action": action,
                "status": final.get("status"),
                "result": final,
                "diagnosis": None if final.get("status") == "EXECUTED" else self._diagnose(final),
            }
            results.append(step)

            if step["status"] != "EXECUTED":
                if replans < MAX_REPLANS and action != "inspect":
                    replans += 1
                    recovery = execute_action("inspect", {"timeout": timeout})
                    results.append({
                        "step": index,
                        "action": "inspect",
                        "status": recovery.get("status"),
                        "result": recovery,
                        "replan_for": action,
                    })
                    if recovery.get("status") == "EXECUTED":
                        continue
                if stop_on_failure:
                    self.last_run = {
                        "status": "FAILED",
                        "objective": objective,
                        "completed_steps": index - 1,
                        "failed_step": index,
                        "replans": replans,
                        "steps": results,
                    }
                    return self.last_run

        self.last_run = {
            "status": "COMPLETED",
            "objective": objective,
            "completed_steps": len(plan["actions"]),
            "replans": replans,
            "steps": results,
        }
        return self.last_run

    def status(self) -> dict[str, Any]:
        return self.last_run


terminal_bridge = TerminalBridge()
