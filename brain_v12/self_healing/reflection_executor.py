#!/usr/bin/env python3
"""Brain self-question -> planner -> allowlisted execution -> evidence loop."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping
from brain_v12.self_healing.reflection_agent import ReflectionAgent
from brain_v12.self_healing.reflection_actions import ActionResult, ReflectionActionRegistry

@dataclass(frozen=True)
class ReflectionExecution:
    question: str
    action_id: str
    result: ActionResult

class ReflectionExecutor:
    """Executes only action IDs returned by an explicit planner."""

    def __init__(self, agent: ReflectionAgent, registry: ReflectionActionRegistry,
                 question_actions: Mapping[str, str] | None = None,
                 planner: Callable[[str, Mapping[str, object]], str] | None = None) -> None:
        self.agent = agent
        self.registry = registry
        self.question_actions = dict(question_actions or {})
        self.planner = planner

    def choose_action(self, question: str, context: Mapping[str, object]) -> str:
        if self.planner is not None:
            action_id = self.planner(question, context)
            return action_id if isinstance(action_id, str) else "none"
        return self.question_actions.get(question, "none")

    def execute_question(self, question: str,
                         context: Mapping[str, object] | None = None) -> ReflectionExecution:
        action_id = self.choose_action(question, context or {})
        return ReflectionExecution(question, action_id, self.registry.execute(action_id))

    def run(self) -> list[ReflectionExecution]:
        executions: list[ReflectionExecution] = []
        context: dict[str, object] = {}
        for question in self.agent.questions[:self.agent.max_turns]:
            execution = self.execute_question(question, context)
            executions.append(execution)
            context.update(last_question=question, last_action=execution.action_id,
                           last_ok=execution.result.ok,
                           last_evidence=execution.result.output or execution.result.error)
            print(f"BRAIN_QUESTION: {question}")
            print(f"BRAIN_ACTION: {execution.action_id}")
            print(f"BRAIN_EXECUTION: {'PASS' if execution.result.ok else 'FAIL'}")
            print(f"BRAIN_EVIDENCE: {execution.result.output[-2000:] or execution.result.error[-2000:]}")
        return executions

def self_test() -> None:
    agent = ReflectionAgent(max_turns=2)
    registry = ReflectionActionRegistry()
    registry.register("verify", lambda: ActionResult("verify", True, 0, "VERIFY=PASS", ""))
    registry.register("inspect", lambda: ActionResult("inspect", True, 0, "INSPECT=PASS", ""))

    def planner(question: str, _context: Mapping[str, object]) -> str:
        return "verify" if question == agent.questions[0] else "inspect"

    results = ReflectionExecutor(agent, registry, planner=planner).run()
    assert [x.action_id for x in results] == ["verify", "inspect"]
    assert all(x.result.ok for x in results)
    assert results[0].result.output == "VERIFY=PASS"

if __name__ == "__main__":
    self_test()
    print("REFLECTION_EXECUTOR=PASS")
