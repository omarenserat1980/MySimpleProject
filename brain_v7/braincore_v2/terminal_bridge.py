"""Bounded Terminal Bridge V10.

Turns a small allowlisted action plan into Agent calls, observes each result,
performs limited recovery, and stops on repeated failure. It never accepts raw
shell strings and never expands permissions automatically.
"""
from typing import Any
from .agent_executor import execute_action

MAX_STEPS = 8
MAX_ATTEMPTS = 2


class TerminalBridge:
    def __init__(self):
        self.last_run: dict[str, Any] = {
            "status": "IDLE",
            "steps": [],
        }

    def plan(self, actions: list[str], objective: str = "") -> dict[str, Any]:
        clean = [str(a).strip() for a in actions if str(a).strip()]
        clean = clean[:MAX_STEPS]
        return {
            "status": "PLANNED",
            "objective": objective,
            "actions": clean,
            "max_steps": MAX_STEPS,
            "max_attempts": MAX_ATTEMPTS,
        }

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
        actions: list[str],
        objective: str = "",
        timeout: int = 30,
        stop_on_failure: bool = True,
    ) -> dict[str, Any]:
        plan = self.plan(actions, objective)
        if not plan["actions"]:
            self.last_run = {"status": "EMPTY", "objective": objective, "steps": []}
            return self.last_run

        results = []
        for index, action in enumerate(plan["actions"], start=1):
            attempts = []
            final = None

            for attempt in range(1, MAX_ATTEMPTS + 1):
                final = execute_action(action, {"timeout": timeout})
                attempts.append({
                    "attempt": attempt,
                    "status": final.get("status"),
                    "diagnosis": None if final.get("status") == "EXECUTED" else self._diagnose(final),
                    "result": final,
                })
                if final.get("status") == "EXECUTED":
                    break

            step = {
                "step": index,
                "action": action,
                "status": final.get("status") if final else "FAILED",
                "attempts": attempts,
            }
            results.append(step)

            if step["status"] != "EXECUTED" and stop_on_failure:
                self.last_run = {
                    "status": "FAILED",
                    "objective": objective,
                    "completed_steps": index - 1,
                    "failed_step": index,
                    "steps": results,
                }
                return self.last_run

        self.last_run = {
            "status": "COMPLETED",
            "objective": objective,
            "completed_steps": len(results),
            "steps": results,
        }
        return self.last_run

    def status(self) -> dict[str, Any]:
        return self.last_run


terminal_bridge = TerminalBridge()
