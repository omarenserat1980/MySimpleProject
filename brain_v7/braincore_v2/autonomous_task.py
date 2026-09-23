"""V10.2 bounded autonomous task loop.

Turns a goal into observable steps, records each observation, and chooses the
next registered action from the current state. It never creates shell commands
or expands Agent permissions on its own.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .agent_executor import execute_action
from .terminal_bridge import terminal_bridge
from .revenue_engine import rank_opportunities, record_outcome

MAX_STEPS = 12
MAX_RUNTIME = 180
JOURNAL_PATH = Path(os.getenv("BRAIN_TASK_JOURNAL", "task_journal.json"))


class AutonomousTask:
    def __init__(self) -> None:
        self.current: dict[str, Any] = {"status": "IDLE"}
        self._load_last()

    def _load_last(self) -> None:
        try:
            if JOURNAL_PATH.is_file():
                data = json.loads(JOURNAL_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.current = data
        except Exception:
            pass

    def _save(self) -> None:
        try:
            JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            JOURNAL_PATH.write_text(
                json.dumps(self.current, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    @staticmethod
    def _next_action(objective: str, completed: list[str], observations: list[dict[str, Any]]) -> str | None:
        t = objective.lower()
        done = set(completed)

        # Always establish the execution context first.
        if "inspect" not in done:
            return "inspect"
        if "termux_pwd" not in done:
            return "termux_pwd"
        if ("ملف" in t or "مشروع" in t or "workspace" in t or "كود" in t) and "workspace_tree" not in done:
            return "workspace_tree"
        if ("اختبار" in t or "test" in t) and "pytest_collect" not in done:
            return "pytest_collect"
        if ("git" in t or "مستودع" in t or "كود" in t) and "git_status" not in done:
            return "git_status"
        if ("فيديو" in t or "video" in t or "wan" in t) and "video_generate" not in done:
            return "video_generate"
        if ("مال" in t or "ربح" in t or "earning" in t or "revenue" in t) and "revenue_rank" not in done:
            return "revenue_rank"
        if "python_version" not in done and ("python" in t or "بايثون" in t):
            return "python_version"

        # After the requested observations, use the registered inspection
        # action once more as a final verification pass.
        if "final_verify" not in done:
            return "inspect"
        return None

    def run(self, objective: str, timeout: int = 30, max_steps: int = MAX_STEPS) -> dict[str, Any]:
        objective = str(objective).strip()
        if not objective:
            return {"status": "EMPTY", "reason": "OBJECTIVE_REQUIRED"}

        started = time.time()
        task_id = uuid.uuid4().hex[:12]
        completed: list[str] = []
        observations: list[dict[str, Any]] = []
        steps: list[dict[str, Any]] = []

        self.current = {
            "task_id": task_id,
            "status": "RUNNING",
            "objective": objective,
            "started_at": time.time(),
            "steps": steps,
        }
        self._save()

        for index in range(1, max(1, min(int(max_steps), MAX_STEPS)) + 1):
            if time.time() - started > MAX_RUNTIME:
                self.current["status"] = "TIMEOUT"
                self.current["reason"] = "MAX_RUNTIME"
                break

            action = self._next_action(objective, completed, observations)
            if action is None:
                self.current["status"] = "COMPLETED"
                break

            if action == "revenue_rank":
                ranked = rank_opportunities()
                result = {"status": "EXECUTED", "action": action, "result": {"opportunities": ranked, "note": "Ranking is a decision aid; it is not proof of income."}}
            else:
                result = execute_action(action, {"timeout": max(1, min(int(timeout), 60)), "objective": objective, "video_prompt": objective})
            observation = {
                "step": index,
                "action": action,
                "status": result.get("status"),
                "result": result,
            }
            observations.append(observation)
            steps.append(observation)

            if result.get("status") == "EXECUTED":
                completed.append(action)
                if action == "revenue_rank" and steps:
                    self.current["revenue_candidates"] = result.get("result", {}).get("opportunities", [])
                # The second inspection is a final verification marker.
                if action == "inspect" and "inspect" in completed and len(completed) > 1:
                    completed.append("final_verify")
            else:
                self.current["status"] = "FAILED"
                self.current["failed_action"] = action
                self.current["reason"] = (
                    result.get("error")
                    or (result.get("result") or {}).get("stderr")
                    or (result.get("result") or {}).get("error")
                    or "ACTION_FAILED"
                )
                break

            self._save()

        if self.current.get("status") == "RUNNING":
            self.current["status"] = "STEP_LIMIT"
        self.current["completed_steps"] = len(steps)
        self.current["completed_actions"] = completed
        self.current["duration_seconds"] = round(time.time() - started, 3)
        self.current["finished_at"] = time.time()
        self._save()
        return self.current

    def status(self) -> dict[str, Any]:
        return self.current


autonomous_task = AutonomousTask()
