#!/usr/bin/env python3
"""End-to-end proof: QUESTION -> ACTION -> RESULT -> EVIDENCE -> VERIFY.

Also proves that a controlled known failure pattern can be converted into a
deterministic improvement proposal without granting the reflection layer any
free-form command execution.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from brain_v12.self_healing.reflection_agent import ReflectionAgent
from brain_v12.self_healing.reflection_actions import ActionResult, ReflectionActionRegistry, command_action
from brain_v12.self_healing.reflection_executor import ReflectionExecutor

ROOT = Path(__file__).resolve().parents[2]


def proposal_discovery_probe() -> None:
    """Inject a temporary, harmless finding and require a matching proposal."""
    probe = ROOT / "scripts" / f".brain_reflection_probe_{uuid.uuid4().hex}.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        'import subprocess\n'
        'subprocess.run(["python", "brain_v12/self_healing/example.py"])\n',
        encoding="utf-8",
    )
    try:
        env = os.environ.copy()
        env["BRAIN_REVIEW_ROOTS"] = "scripts"
        p = subprocess.run(
            [sys.executable, "-m", "brain_v12.self_healing.improvement_engine"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert p.returncode == 0, p.stderr
        proposal_path = ROOT / ".brain" / "state" / "current_improvement.json"
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        matches = [
            c for c in proposal.get("candidates", [])
            if c.get("file") == str(probe.relative_to(ROOT))
        ]
        assert matches, "KNOWN_FAILURE_PROBE_NOT_CONVERTED_TO_PROPOSAL"
        print("REFLECTION_PROPOSAL_DISCOVERY=PASS")
    finally:
        probe.unlink(missing_ok=True)


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

    proposal_discovery_probe()

    print("REFLECTION_E2E=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
