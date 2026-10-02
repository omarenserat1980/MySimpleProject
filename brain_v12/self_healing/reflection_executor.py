#!/usr/bin/env python3
"""Execute Reflection Agent questions through explicit allowlisted actions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from brain_v12.self_healing.reflection_agent import ReflectionAgent
from brain_v12.self_healing.reflection_actions import ActionResult, ReflectionActionRegistry


@dataclass(frozen=True)
class ReflectionExecution:
    question: str
    action_id: str
    result: ActionResult


class ReflectionExecutor:
    """Maps questions to registered action IDs; never executes question text."""

    def __init__(self, agent: ReflectionAgent, registry: ReflectionActionRegistry,
                 question_actions: Mapping[str, str]) -> None:
        self.agent = agent
        self.registry = registry
        self.question_actions = dict(question_actions)

    def execute_question(self, question: str) -> ReflectionExecution:
        action_id = self.question_actions.get(question)
        if action_id is None:
            result = ActionResult("none", False, 127, "", "NO_ACTION_MAPPING")
            return ReflectionExecution(question, "none", result)
        result = self.registry.execute(action_id)
        return ReflectionExecution(question, action_id, result)

    def run(self) -> list[ReflectionExecution]:
        executions: list[ReflectionExecution] = []
        for question in self.agent.questions[:self.agent.max_turns]:
            executions.append(self.execute_question(question))
        return executions


def self_test() -> None:
    from brain_v12.self_healing.reflection_actions import ActionResult

    agent = ReflectionAgent(max_turns=2)
    registry = ReflectionActionRegistry()
    registry.register("verify", lambda: ActionResult("verify", True, 0, "VERIFY=PASS", ""))
    registry.register("inspect", lambda: ActionResult("inspect", True, 0, "INSPECT=PASS", ""))
    executor = ReflectionExecutor(agent, registry, {
        agent.questions[0]: "verify",
        agent.questions[1]: "inspect",
    })
    results = executor.run()
    assert [x.action_id for x in results] == ["verify", "inspect"]
    assert all(x.result.ok for x in results)
    assert results[0].result.output == "VERIFY=PASS"


if __name__ == "__main__":
    self_test()
    print("REFLECTION_EXECUTOR=PASS")
