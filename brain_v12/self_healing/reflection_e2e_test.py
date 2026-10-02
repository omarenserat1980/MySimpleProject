#!/usr/bin/env python3
"""End-to-end proof: QUESTION -> ACTION -> RESULT -> EVIDENCE -> VERIFY."""
from __future__ import annotations

import sys

from brain_v12.self_healing.reflection_agent import ReflectionAgent
from brain_v12.self_healing.reflection_actions import ActionResult, ReflectionActionRegistry, command_action
from brain_v12.self_healing.reflection_executor import ReflectionExecutor


def main() -> int:
    agent = ReflectionAgent(max_turns=2)
    registry = ReflectionActionRegistry()
    registry.register("inspect", lambda: ActionResult("inspect", True, 0, "INSPECT=PASS", ""))
    registry.register(
        "verify",
        command_action(
            "verify",
            [sys.executable, "-c", "print('VERIFY=PASS')"],
            timeout=30,
        ),
    )
    executor = ReflectionExecutor(
        agent,
        registry,
        {
            agent.questions[0]: "inspect",
            agent.questions[1]: "verify",
        },
    )
    executions = executor.run()

    print("REFLECTION_E2E_QUESTION")
    for item in executions:
        print(f"QUESTION: {item.question}")
        print(f"ACTION: {item.action_id}")
        print(f"EXECUTION: {'PASS' if item.result.ok else 'FAIL'}")
        print(f"EVIDENCE: {item.result.output or item.result.error}")

    assert len(executions) == 2
    assert executions[0].result.ok
    assert executions[1].result.ok
    assert executions[1].result.output.strip() == "VERIFY=PASS"
    print("REFLECTION_E2E=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
