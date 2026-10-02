#!/usr/bin/env python3
"""Bounded Brain -> ChatGPT -> action -> evidence loop."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping, Protocol

from brain_v12.self_healing.reflection_agent import ReflectionAgent
from brain_v12.self_healing.reflection_actions import ReflectionActionRegistry
from brain_v12.self_healing.chatgpt_reasoner import ChatGPTReasoner


class Reasoner(Protocol):
    def plan(self, question: str, context: Mapping[str, object]) -> dict: ...


@dataclass(frozen=True)
class BrainCycle:
    question: str
    answer: str
    action_id: str
    execution_ok: bool
    exit_code: int
    evidence: str
    reason: str


class BrainReasoningLoop:
    """The Brain owns the loop; ChatGPT supplies reasoning, never execution."""

    def __init__(
        self,
        agent: ReflectionAgent,
        registry: ReflectionActionRegistry,
        reasoner: Reasoner | None = None,
        max_cycles: int | None = None,
    ) -> None:
        self.agent = agent
        self.registry = registry
        self.reasoner = reasoner or ChatGPTReasoner()
        self.max_cycles = max_cycles or agent.max_turns

    def run(self, context: Mapping[str, object] | None = None) -> list[BrainCycle]:
        state = dict(context or {})
        state["allowed_actions"] = list(self.registry.ids())
        cycles: list[BrainCycle] = []

        questions = list(self.agent.questions)
        index = 0
        while index < self.max_cycles and index < len(questions):
            question = questions[index]
            plan = self.reasoner.plan(question, state)
            if not isinstance(plan, dict):
                plan = {"answer": "", "action_id": "none", "reason": "INVALID_PLAN"}
            action_id = str(plan.get("action_id", "none"))
            if action_id not in self.registry.ids():
                plan = dict(plan)
                plan["action_id"] = "none"
                plan["reason"] = "ACTION_NOT_ALLOWLISTED"
            action_id = str(plan["action_id"])
            execution = self.registry.execute(action_id)
            evidence = execution.output or execution.error

            cycle = BrainCycle(
                question=question,
                answer=str(plan.get("answer", "")),
                action_id=action_id,
                execution_ok=execution.ok,
                exit_code=execution.exit_code,
                evidence=evidence[-4000:],
                reason=str(plan.get("reason", "")),
            )
            cycles.append(cycle)

            print(f"BRAIN_QUESTION: {cycle.question}")
            print(f"CHATGPT_ANSWER: {cycle.answer}")
            print(f"CHATGPT_ACTION: {cycle.action_id}")
            print(f"BRAIN_EXECUTION: {'PASS' if cycle.execution_ok else 'FAIL'}")
            print(f"BRAIN_EVIDENCE: {cycle.evidence}")
            state.update(
                last_question=cycle.question,
                last_answer=cycle.answer,
                last_action=cycle.action_id,
                last_ok=cycle.execution_ok,
                last_evidence=cycle.evidence,
                last_exit_code=cycle.exit_code,
            )

            # A failed execution becomes the next Brain-generated question.
            # This keeps the loop focused on the actual failure instead of
            # blindly advancing through a fixed checklist.
            if not execution.ok and index + 1 < self.max_cycles:
                follow_up = self.agent.next_question(
                    index + 1,
                    str(plan.get("answer", "")),
                    [evidence] if evidence else [],
                )
                if follow_up not in questions[index + 1:]:
                    questions.insert(index + 1, follow_up)
            index += 1
        return cycles


def self_test() -> None:
    from brain_v12.self_healing.reflection_actions import ActionResult

    agent = ReflectionAgent(max_turns=2)
    registry = ReflectionActionRegistry()
    registry.register("inspect", lambda: ActionResult("inspect", True, 0, "INSPECT=PASS", ""))
    registry.register("verify", lambda: ActionResult("verify", True, 0, "VERIFY=PASS", ""))

    class FakeChatGPT:
        def plan(self, question: str, context: Mapping[str, object]) -> dict:
            action = "inspect" if not context.get("last_action") else "verify"
            return {
                "ok": True,
                "answer": "تحليل الدليل ثم التحقق.",
                "action_id": action,
                "reason": "bounded test plan",
                "expected_evidence": ["PASS"],
                "risk": "low",
            }

    cycles = BrainReasoningLoop(agent, registry, FakeChatGPT()).run()
    assert [c.action_id for c in cycles] == ["inspect", "verify"]
    assert all(c.execution_ok for c in cycles)
    assert cycles[0].evidence == "INSPECT=PASS"
    assert cycles[1].evidence == "VERIFY=PASS"
    assert cycles[1].exit_code == 0

    failing_agent = ReflectionAgent(
        max_turns=3,
        questions=("What should I inspect?", "What should I verify?"),
    )
    failing_registry = ReflectionActionRegistry()
    failing_registry.register(
        "inspect", lambda: ActionResult("inspect", False, 2, "", "INSPECT=FAIL")
    )
    failing_registry.register(
        "verify", lambda: ActionResult("verify", True, 0, "VERIFY=PASS", "")
    )

    class FailureAwareChatGPT:
        def plan(self, question: str, context: Mapping[str, object]) -> dict:
            if context.get("last_ok") is False:
                return {
                    "answer": "Investigate the failed evidence before continuing.",
                    "action_id": "verify",
                    "reason": "failure follow-up",
                }
            return {"answer": "Inspect.", "action_id": "inspect", "reason": "initial"}

    failure_cycles = BrainReasoningLoop(
        failing_agent, failing_registry, FailureAwareChatGPT()
    ).run()
    assert failure_cycles[0].execution_ok is False
    assert failure_cycles[1].question == "What concrete evidence can verify that answer?"
    assert failure_cycles[1].execution_ok is True


if __name__ == "__main__":
    self_test()
    print("BRAIN_REASONING_LOOP=PASS")
