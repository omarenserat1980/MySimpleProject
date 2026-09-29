from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..storage.artifacts import ArtifactStore
from ..workflow_manifest import Workflow
from .logs import RunLog


@dataclass(frozen=True)
class StepResult:
    name: str
    command: str
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class WorkflowResult:
    success: bool
    steps: tuple[StepResult, ...]


class BrainRunnerExecutor:
    """Execute a parsed Brain workflow inside its assigned workspace."""

    def __init__(self, workspace: Path, logs: RunLog | None = None, artifacts: ArtifactStore | None = None):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logs = logs
        self.artifacts = artifacts

    def run_step(self, name: str, command: list[str], timeout: int = 900) -> StepResult:
        if not command or any(not isinstance(x, str) or not x for x in command):
            raise ValueError("command must be a non-empty string list")
        try:
            p = subprocess.run(command, cwd=self.workspace, text=True, capture_output=True, timeout=timeout)
            return StepResult(name, " ".join(command), p.returncode, p.stdout, p.stderr)
        except subprocess.TimeoutExpired as exc:
            return StepResult(name, " ".join(command), 124, exc.stdout or "", exc.stderr or "timeout")

    def run_workflow(self, workflow: Workflow, run_id: int) -> WorkflowResult:
        results: list[StepResult] = []
        for step in workflow.steps:
            result = self.run_step(step.name, list(step.command))
            results.append(result)
            if self.logs:
                self.logs.append(run_id, "stdout", result.stdout)
                self.logs.append(run_id, "stderr", result.stderr)
            if result.returncode != 0:
                break

        success = bool(results) and all(item.returncode == 0 for item in results)
        if self.artifacts:
            payload = "\n".join(
                f"{item.name}: rc={item.returncode}\n{item.stdout}" for item in results
            ).encode("utf-8")
            self.artifacts.put(str(run_id), "workflow-result.txt", payload)
        return WorkflowResult(success, tuple(results))

    def run_python_tests(self) -> StepResult:
        return self.run_step(
            "unit-tests",
            ["python", "-m", "unittest", "discover", "-s", "brain_git_platform", "-p", "test_*.py"],
        )
