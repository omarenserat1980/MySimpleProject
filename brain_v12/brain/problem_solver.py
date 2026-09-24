"""Problem-solving engine for Electronic Brain V12.

Turns a goal into explicit, traceable solution candidates and runs a bounded
observe -> understand -> analyze -> plan -> choose -> execute -> verify -> learn
cycle. It never treats a proposal as an executed external action.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


class ProblemSolver:
    MAX_RETRIES = 2

    def __init__(self, cognitive_loop):
        self.cognitive = cognitive_loop

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _solution_candidates(self, goal, options):
        candidates = []
        for option in options:
            action = option.get("action", "observe")
            tool = option.get("tool_id")
            risk = option.get("risk", "low")
            confidence = float(option.get("confidence", 0.5))
            candidates.append({
                "solution_id": "SOL-" + uuid4().hex[:10],
                "action": action,
                "tool_id": tool,
                "description": option.get("expected", option.get("action", "")),
                "risk": risk,
                "confidence": confidence,
                "reversible": bool(option.get("reversible", True)),
                "requirements": option.get("requirements", []),
                "evidence_needed": option.get("evidence", []),
                "status": "PROPOSED",
            })
        return candidates

    def _verify(self, execution):
        result = execution.get("tool_result") or {}
        if execution.get("status") != "COMPLETED":
            return {"status": "NOT_VERIFIED", "evidence": "التنفيذ لم يكتمل؛ لا يوجد نجاح يمكن اعتماده."}
        if result.get("ok") is not True:
            return {"status": "NOT_VERIFIED", "evidence": "نتيجة الأداة لا تثبت النجاح."}
        return {
            "status": "VERIFIED",
            "evidence": "نتيجة الأداة الداخلية أعادت ok=true.",
            "tool_status": result.get("status"),
        }

    def solve(self, goal):
        goal = (goal or "").strip()
        if not goal:
            return {"ok": False, "status": "EMPTY_GOAL"}

        run_id = "PS-" + uuid4().hex[:12]
        self.cognitive._state("PERCEIVE", goal=goal, run_id=run_id)
        self.cognitive.events.publish("PROBLEM_SOLVING_STARTED", {"run_id": run_id, "goal": goal})

        memories = self.cognitive.store.memories()[-12:]
        self.cognitive._state("UNDERSTAND", goal=goal, run_id=run_id)
        self.cognitive.events.publish("PROBLEM_UNDERSTOOD", {
            "run_id": run_id, "goal": goal, "memory_count": len(memories)
        })

        self.cognitive._state("ANALYZE", goal=goal, run_id=run_id)
        options = self.cognitive.decisions.generate(goal)
        solutions = self._solution_candidates(goal, options)
        self.cognitive.events.publish("SOLUTIONS_GENERATED", {
            "run_id": run_id, "count": len(solutions),
            "solutions": [{"solution_id": x["solution_id"], "action": x["action"],
                           "confidence": x["confidence"]} for x in solutions]
        })

        self.cognitive._state("PLAN", goal=goal, run_id=run_id)
        decision = self.cognitive.decisions.choose(goal, options, self.cognitive.permissions.grants)
        selected = decision.get("selected") or {}
        selected_solution = next(
            (x for x in solutions if x["action"] == selected.get("action")), None
        )
        self.cognitive.events.publish("SOLUTION_SELECTED", {
            "run_id": run_id,
            "solution_id": (selected_solution or {}).get("solution_id"),
            "action": selected.get("action"),
            "reason": decision.get("reason"),
            "alternatives": len(decision.get("alternatives", [])),
        })

        attempts = []
        verification = {"status": "NOT_RUN"}
        execution = {"status": "NOT_RUN"}
        chosen_action = selected.get("action", "observe")
        tool_id = selected.get("tool_id")

        for attempt in range(1, self.MAX_RETRIES + 2):
            self.cognitive._state("EXECUTE", goal=goal, run_id=run_id,
                                  attempt=attempt, solution_id=(selected_solution or {}).get("solution_id"))
            if decision.get("status") == "WAITING_APPROVAL":
                execution = {
                    "status": "WAITING_APPROVAL",
                    "attempt": attempt,
                    "action": chosen_action,
                    "tool": tool_id,
                    "reason": decision.get("reason"),
                    "missing_permissions": decision.get("missing_permissions", []),
                }
            elif tool_id:
                params = {}
                if tool_id == "code.inspect":
                    params = {"path": "brain_v12/app.py"}
                elif tool_id == "code.verify":
                    params = {"paths": []}
                elif tool_id == "tasks.create":
                    params = {"title": selected.get("action", "تنفيذ الحل")}
                execution_result = self.cognitive.execute_tool(tool_id, params)
                execution = {
                    "status": "COMPLETED" if execution_result.get("ok") else execution_result.get("status", "FAILED"),
                    "attempt": attempt,
                    "action": chosen_action,
                    "tool": tool_id,
                    "tool_result": execution_result,
                }
            else:
                execution = {
                    "status": "NO_EXECUTABLE_TOOL",
                    "attempt": attempt,
                    "action": chosen_action,
                }

            self.cognitive._state("VERIFY", goal=goal, run_id=run_id, attempt=attempt)
            verification = self._verify(execution)
            attempts.append({
                "attempt": attempt,
                "execution_status": execution.get("status"),
                "verification": verification.get("status"),
            })
            self.cognitive.events.publish("PROBLEM_SOLUTION_VERIFIED", {
                "run_id": run_id, "attempt": attempt,
                "status": verification["status"],
            })
            if verification["status"] == "VERIFIED":
                break
            if attempt <= self.MAX_RETRIES:
                self.cognitive.events.publish("PROBLEM_RETRY", {
                    "run_id": run_id, "attempt": attempt + 1,
                    "reason": verification.get("evidence"),
                })

        self.cognitive._state("LEARN", status="READY", goal=goal, run_id=run_id)
        lesson = (
            "الحل نُفذ وتحقق منه بنتيجة فعلية."
            if verification["status"] == "VERIFIED"
            else "الحل لم يُثبت نجاحه؛ سُجلت المحاولة وسبب عدم التحقق."
        )
        self.cognitive.store.save_memory(
            "problem_solver.last_run",
            f"{run_id} | {goal} | {verification['status']} | {self._now()}",
        )
        self.cognitive.events.publish("PROBLEM_LEARNED", {
            "run_id": run_id, "lesson": lesson,
            "verification": verification["status"],
        })

        return {
            "ok": verification["status"] == "VERIFIED",
            "run_id": run_id,
            "goal": goal,
            "pipeline": [
                "PERCEIVE", "UNDERSTAND", "ANALYZE", "PLAN",
                "DECIDE", "EXECUTE", "VERIFY", "LEARN"
            ],
            "memory_count": len(memories),
            "solutions": solutions,
            "decision": decision,
            "selected_solution": selected_solution,
            "execution": execution,
            "verification": verification,
            "attempts": attempts,
            "learning": {"status": "RECORDED", "lesson": lesson},
            "external_action": "NOT_CLAIMED",
        }
