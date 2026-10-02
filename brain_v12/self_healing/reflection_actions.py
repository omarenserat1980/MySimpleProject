"""Allowlisted executable actions for Brain reflection loops.

Generated reflection text is never treated as a shell command. Only registered
action IDs can execute, with bounded timeouts and explicit audit records.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, asdict
from typing import Callable, Sequence

@dataclass(frozen=True)
class ActionResult:
    action_id: str
    ok: bool
    exit_code: int
    output: str
    error: str

class ReflectionActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, Callable[[], ActionResult]] = {}
        self._descriptions: dict[str, str] = {}

    def register(
        self,
        action_id: str,
        action: Callable[[], ActionResult],
        description: str = "",
    ) -> None:
        if not action_id or action_id in self._actions:
            raise ValueError("invalid_or_duplicate_action_id")
        self._actions[action_id] = action
        self._descriptions[action_id] = str(description)

    def execute(self, action_id: str) -> ActionResult:
        action = self._actions.get(action_id)
        if action is None:
            return ActionResult(action_id, False, 127, "", "ACTION_NOT_ALLOWED")
        return action()

    def ids(self) -> list[str]:
        return sorted(self._actions)

    def descriptions(self) -> dict[str, str]:
        return {key: self._descriptions.get(key, "") for key in self.ids()}

def command_action(action_id: str, argv: Sequence[str], timeout: int = 120, env: dict[str, str] | None = None) -> Callable[[], ActionResult]:
    if not argv or timeout < 1 or timeout > 900:
        raise ValueError("invalid_action_configuration")
    frozen = tuple(argv)
    def run() -> ActionResult:
        try:
            p = subprocess.run(frozen, capture_output=True, text=True, timeout=timeout, check=False, env=env or None)
            return ActionResult(action_id, p.returncode == 0, p.returncode, p.stdout[-12000:], p.stderr[-12000:])
        except subprocess.TimeoutExpired as exc:
            return ActionResult(action_id, False, 124, str(exc.stdout or "")[-12000:], "TIMEOUT")
    return run

def workflow_dispatch_action(
    action_id: str,
    repo: str,
    workflow_id: str,
    ref: str = "main",
    inputs: dict[str, str] | None = None,
    timeout: int = 60,
) -> Callable[[], ActionResult]:
    """Create a fixed, allowlisted workflow dispatch action without shell execution."""
    import sys
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / "ci" / "dispatch_workflow.py"
    argv = [sys.executable, str(script), "--repo", repo, "--workflow", workflow_id, "--ref", ref]
    for key, value in sorted((inputs or {}).items()):
        argv.extend(["--input", f"{key}={value}"])
    return command_action(action_id, argv, timeout)


def self_test() -> None:
    reg = ReflectionActionRegistry()
    reg.register("safe-test", lambda: ActionResult("safe-test", True, 0, "PASS", ""), "Run the safe action self-test.")
    assert reg.execute("safe-test").ok
    assert reg.descriptions()["safe-test"] == "Run the safe action self-test."
    denied = reg.execute("not-registered")
    assert denied.error == "ACTION_NOT_ALLOWED"
    assert asdict(denied)["action_id"] == "not-registered"

if __name__ == "__main__":
    self_test()
    print("REFLECTION_ACTIONS=PASS")