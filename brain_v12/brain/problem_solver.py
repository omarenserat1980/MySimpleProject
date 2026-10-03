"""Problem-solving engine for Electronic Brain V12.

Turns a goal into explicit, traceable solution candidates and runs a bounded
observe -> understand -> analyze -> plan -> choose -> execute -> verify -> learn
cycle. It never treats a proposal as an executed external action.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import hashlib
import json
from .solution_engine import Alternative, AlternativeRegistry, Problem, SolutionEngine, SourceType


class ProblemSolver:
    MAX_RETRIES = 2  # retained for callers; this allows three total attempts

    def __init__(self, cognitive_loop, solution_engine=None,
                 alternative_executors=None, alternative_verifier=None,
                 supervisor=None):
        self.cognitive = cognitive_loop
        self.solution_engine = solution_engine or SolutionEngine()
        self.alternative_executors = dict(alternative_executors or {})
        self.alternative_verifier = alternative_verifier
        self.supervisor = supervisor

    @staticmethod
    def _tool_params(tool_id, action):
        if tool_id == "code.inspect":
            return {"path": "brain_v12/app.py"}
        if tool_id == "code.verify":
            return {"paths": []}
        if tool_id == "tasks.create":
            return {"title": action or "تنفيذ الحل"}
        return {}

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

    def solve(self, goal):
        goal = (goal or "").strip()
        if not goal:
            return {"ok": False, "status": "EMPTY_GOAL"}

        run_id = "PS-" + uuid4().hex[:12]
        self.cognitive._state("PERCEIVE", goal=goal, run_id=run_id)
        self.cognitive.events.publish("PROBLEM_SOLVING_STARTED", {"run_id": run_id, "goal": goal})

        memories = self.cognitive.store.memories()[-12:]
        supervisor_job = None
        if self.supervisor is not None:
            supervisor_job = self.supervisor.create(goal, steps=[
                "discover", "plan", "select_backend", "execute",
                "verify", "repair", "retry", "deliver",
            ])
            supervisor_job = self.supervisor.transition(
                supervisor_job, "discover", details={"memory_count": len(memories)}
            )
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
        if supervisor_job is not None:
            supervisor_job = self.supervisor.transition(
                supervisor_job, "plan", details={"candidate_count": len(solutions)}
            )
            supervisor_job = self.supervisor.transition(
                supervisor_job, "select_backend", details={
                    "selected_tool": selected.get("tool_id"),
                    "decision_status": decision.get("status"),
                }
            )
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

        # Translate existing decision options into safe built-in alternatives.
        # Risky actions stay behind the existing permission/approval path; the
        # fallback chain may continue through other authorized low/medium-risk tools.
        option_by_tool = {}
        alternatives = []
        grants = self.cognitive.permissions.grants
        for option in options:
            tool = option.get("tool_id")
            requirements = set(option.get("requirements", []))
            risk = str(option.get("risk", "low")).lower()
            if not tool or tool in option_by_tool or risk not in {"low", "medium"}:
                continue
            if not requirements.issubset(grants):
                continue
            option_by_tool[tool] = option
            alternatives.append(Alternative(
                id=tool, name=str(option.get("expected", option.get("action", tool))),
                source_type=SourceType.BUILT_IN, cost=0,
                security_approved=True, risk=risk,
                quality=float(option.get("confidence", 0.5)),
            ))

        registry = AlternativeRegistry(self.solution_engine.registry.list())
        for alternative in alternatives:
            if registry.get(alternative.id) is None:
                registry.register(alternative)
        engine = SolutionEngine(registry, self.solution_engine.analyzer,
                                max_attempts=min(self.MAX_RETRIES + 1,
                                                 self.solution_engine.max_attempts))
        tool_outputs = {}
        executors = {}
        for key, callback in self.alternative_executors.items():
            def capture_external(_problem, _alternative, cb=callback, alt_id=key):
                output = cb(_problem, _alternative)
                tool_outputs[alt_id] = output
                return output
            executors[key] = capture_external
        for tool, option in option_by_tool.items():
            def execute_builtin(_problem, _alternative, t=tool, o=option):
                output = self.cognitive.execute_tool(t, self._tool_params(t, o.get("action")))
                tool_outputs[t] = output
                if not isinstance(output, dict) or output.get("ok") is not True:
                    reason = output.get("status", "tool execution failed") if isinstance(output, dict) else "invalid tool result"
                    raise RuntimeError(str(reason))
                return output
            executors.setdefault(tool, execute_builtin)

        self.cognitive._state("EXECUTE", goal=goal, run_id=run_id)
        if supervisor_job is not None:
            supervisor_job = self.supervisor.transition(
                supervisor_job, "execute", details={"run_id": run_id}
            )
        if decision.get("status") == "WAITING_APPROVAL" and not alternatives:
            solution_run = {
                "ok": False, "status": "WAITING_APPROVAL",
                "run_id": "SOL-" + uuid4().hex[:12], "selected": None,
                "fallback_chain": [], "attempts": [], "evidence_ref": None,
                "audit": [{"event": "WAITING_APPROVAL",
                           "missing_permissions": decision.get("missing_permissions", [])}],
            }
        else:
            def verify_solution(output, problem, alternative):
                if alternative.source_type != SourceType.BUILT_IN:
                    if self.alternative_verifier is None:
                        return {"ok": False, "error": "EXPLICIT_VERIFIER_REQUIRED"}
                    return self.alternative_verifier(output, problem, alternative)
                if not isinstance(output, dict) or output.get("ok") is not True or output.get("status") != "COMPLETED":
                    return {"ok": False, "error": "BUILTIN_RESULT_NOT_COMPLETED"}
                digest = hashlib.sha256(json.dumps(
                    output, sort_keys=True, ensure_ascii=False, default=str,
                ).encode("utf-8")).hexdigest()
                evidence_ref = f"tool://{run_id}/{alternative.id}/{digest}"
                self.cognitive.events.publish("SOLUTION_VERIFICATION_EVIDENCE", {
                    "run_id": run_id, "alternative_id": alternative.id,
                    "evidence_ref": evidence_ref, "sha256": digest,
                    "tool_status": output.get("status"),
                })
                return {"ok": True, "evidence_ref": evidence_ref,
                        "evidence": {"sha256": digest, "tool_status": output.get("status")}}

            solution_run = engine.solve(
                Problem(description=goal), executors, verify_solution,
            )
        raw_attempts = solution_run["attempts"]
        attempts = []
        for index, item in enumerate(raw_attempts, start=1):
            verified = item.get("status") == "VERIFIED"
            attempts.append({
                "attempt": index,
                "alternative_id": item.get("alternative_id"),
                "execution_status": "FAILED" if item.get("status") == "FAILED" else "COMPLETED",
                "verification": "VERIFIED" if verified else "NOT_VERIFIED",
                "status": item.get("status"),
                "error": item.get("error"),
                "evidence": item.get("evidence"),
            })
        actual_tool = solution_run.get("selected")
        selected_solution = next((item for item in solutions
                                  if item.get("tool_id") == actual_tool), selected_solution)
        chosen_action = (option_by_tool.get(actual_tool) or selected).get("action", "observe")
        tool_id = actual_tool or selected.get("tool_id")
        decision = {**decision, "selected": option_by_tool.get(actual_tool, selected),
                    "solution_run_id": solution_run["run_id"],
                    "fallback_chain": solution_run["fallback_chain"]}
        self.cognitive.events.publish("SOLUTION_FALLBACK_SELECTED", {
            "run_id": run_id, "solution_run_id": solution_run["run_id"],
            "alternative_id": actual_tool, "status": solution_run["status"],
        })
        self.cognitive._state("VERIFY", goal=goal, run_id=run_id,
                              solution_run_id=solution_run["run_id"])
        is_verified = solution_run["status"] == "VERIFIED"
        selected_attempt = next((item for item in solution_run.get("attempts", [])
                                 if item.get("alternative_id") == actual_tool
                                 and item.get("status") == "VERIFIED"), None)
        verifier_result = (selected_attempt or {}).get("verification", {})
        objective_verified = bool(
            isinstance(verifier_result, dict)
            and verifier_result.get("objective_verified") is True
        )
        objective_status = (
            "VERIFIED" if objective_verified else
            "IN_PROGRESS" if is_verified else
            "WAITING_APPROVAL" if solution_run["status"] == "WAITING_APPROVAL" else
            "NOT_VERIFIED"
        )
        if is_verified and decision.get("status") == "WAITING_APPROVAL":
            decision["status"] = "DECIDED"
            decision["reason"] = "verified_safe_alternative"
        verification = {
            "status": "VERIFIED" if is_verified else "NOT_VERIFIED",
            "evidence": solution_run.get("evidence_ref") if is_verified else "لا يوجد بديل اجتاز التحقق.",
            "tool_status": "COMPLETED" if is_verified else "FAILED",
            "scope": "selected_action",
            "objective_verified": objective_verified,
            "objective_status": objective_status,
        }
        execution = {
            "status": ("COMPLETED" if is_verified else
                       "WAITING_APPROVAL" if solution_run["status"] == "WAITING_APPROVAL" else "FAILED"),
            "attempt": len(attempts), "action": chosen_action, "tool": tool_id,
            "tool_result": tool_outputs.get(actual_tool),
            "solution_run": solution_run,
        }
        if supervisor_job is not None:
            supervisor_job = self.supervisor.transition(
                supervisor_job, "verify", details={
                    "run_id": run_id,
                    "solution_run_id": solution_run["run_id"],
                    "action_verified": is_verified,
                    "objective_verified": objective_verified,
                    "evidence_ref": solution_run.get("evidence_ref"),
                }
            )
            if objective_verified:
                supervisor_job = self.supervisor.transition(
                    supervisor_job, "deliver", status="completed", details={
                        "objective_verified": True,
                        "evidence_ref": solution_run.get("evidence_ref"),
                    }
                )
                self.supervisor.snapshot(supervisor_job, {
                    "verified": True, "evidence_ref": solution_run.get("evidence_ref"),
                })
            else:
                reason = objective_status
                supervisor_job = self.supervisor.transition(
                    supervisor_job, "blocked", status="blocked", details={
                        "reason": reason,
                        "action_verified": is_verified,
                        "objective_verified": False,
                        "evidence_ref": solution_run.get("evidence_ref"),
                    }
                )
                self.supervisor.snapshot(supervisor_job, {
                    "verified": False,
                    "action_verified": is_verified,
                    "reason": reason,
                    "evidence_ref": solution_run.get("evidence_ref"),
                })
        for index, attempt in enumerate(attempts, start=1):
            self.cognitive.events.publish("PROBLEM_SOLUTION_VERIFIED", {
                "run_id": run_id, "attempt": index,
                "status": attempt["verification"],
                "alternative_id": attempt["alternative_id"],
            })
            if index < len(attempts):
                self.cognitive.events.publish("PROBLEM_RETRY", {
                    "run_id": run_id, "attempt": index + 1,
                    "reason": attempt.get("error") or attempt["verification"],
                })
        if not is_verified:
            self.cognitive.events.publish("PROBLEM_RETRY_EXHAUSTED", {
                "run_id": run_id, "attempts": len(attempts),
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
            "status": objective_status,
            "objective_verified": objective_verified,
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
            "supervisor_job": supervisor_job,
            "verification": verification,
            "attempts": attempts,
            "learning": {"status": "RECORDED", "lesson": lesson},
            "external_action": "NOT_CLAIMED",
        }
