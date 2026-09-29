from __future__ import annotations

import os
import signal
import subprocess
import threading
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
    """Execute a parsed Brain workflow with bounded processes and cancellation."""

    def __init__(
        self,
        workspace: Path,
        logs: RunLog | None = None,
        artifacts: ArtifactStore | None = None,
        cancel_event: threading.Event | None = None,
    ):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logs = logs
        self.artifacts = artifacts
        self.cancel_event = cancel_event or threading.Event()

    def run_step(self, name: str, command: list[str], timeout: int = 900) -> StepResult:
        if not command or any(not isinstance(x, str) or not x for x in command):
            raise ValueError("command must be a non-empty string list")
        if timeout < 1:
            raise ValueError("timeout must be positive")
        if self.cancel_event.is_set():
            return StepResult(name, " ".join(command), 130, "", "cancelled")

        env = os.environ.copy()
        env["BRAIN_RUNNER_WORKSPACE"] = str(self.workspace)
        try:
            p = subprocess.Popen(
                command,
                cwd=self.workspace,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                env=env,
            )
        except OSError as exc:
            return StepResult(name, " ".join(command), 127, "", str(exc))

        try:
            elapsed = 0.0
            while p.poll() is None:
                if self.cancel_event.wait(0.25):
                    try:
                        os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        p.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(p.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        p.wait()
                    return StepResult(name, " ".join(command), 130, "", "cancelled")
                elapsed += 0.25
                if elapsed >= timeout:
                    try:
                        os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        p.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(p.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        p.wait()
                    return StepResult(name, " ".join(command), 124, "", "timeout")

            stdout, stderr = p.communicate()
            return StepResult(name, " ".join(command), p.returncode, stdout, stderr)
        finally:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

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
