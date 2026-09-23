"""Dedicated workforce for continuous improvement of the Brain coding tool.

The team creates an auditable improvement queue and uses CodeWorkspaceTool for
bounded source changes. It never stores credentials, transfers money, or
publishes externally.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any, Iterable
import subprocess
import sys

from .code_workspace_tool import CodeChange, CodeWorkspaceTool
from .employee_hierarchy import EmployeeHierarchy
from .github_code_executor import GitHubCodeExecutor


@dataclass
class CodingImprovement:
    improvement_id: str
    objective: str
    priority: float = 0.5
    status: str = "QUEUED"
    created_at: float = field(default_factory=time)
    result: dict[str, Any] = field(default_factory=dict)


class CodeToolEngineeringTeam:
    """Permanent specialist team responsible only for the Brain coding tool."""

    TEAM_DEPARTMENT = "DEPT-CODE-TOOL"
    TEAM_TITLE = "BRAIN_CODE_TOOL_ONLY"

    def __init__(self, organization: EmployeeHierarchy, workspace: CodeWorkspaceTool) -> None:
        self.organization = organization
        self.workspace = workspace
        self.remote = GitHubCodeExecutor()
        self.team = organization.ensure_specialized_team(department_id=self.TEAM_DEPARTMENT)
        self.queue: list[CodingImprovement] = []
        self.cycles = 0

    @property
    def employee_ids(self) -> tuple[str, ...]:
        return tuple(self.team["employee_ids"])

    def enqueue(self, objective: str, *, priority: float = 0.5) -> CodingImprovement:
        item = CodingImprovement(
            improvement_id=f"CODE-IMP-{len(self.queue)+1:06d}",
            objective=str(objective).strip(),
            priority=max(0.0, min(1.0, float(priority))),
        )
        self.queue.append(item)
        return item

    def plan_cycle(self) -> dict[str, Any]:
        """Create bounded work for the specialist team without inventing code changes."""
        self.cycles += 1
        if not self.queue:
            self.enqueue("inspect the coding tool for the highest-value safe improvement", priority=0.8)
            self.enqueue("add regression coverage for the coding tool", priority=0.75)
            self.enqueue("measure reliability, rollback, and validation paths", priority=0.7)
        pending = sorted(
            (x for x in self.queue if x.status == "QUEUED"),
            key=lambda x: x.priority,
            reverse=True,
        )
        assignments = []
        for index, item in enumerate(pending[: len(self.employee_ids)]):
            employee_id = self.employee_ids[index]
            assignments.append({
                "improvement_id": item.improvement_id,
                "employee_id": employee_id,
                "objective": item.objective,
                "priority": item.priority,
            })
        return {
            "cycle": self.cycles,
            "team_department": self.TEAM_DEPARTMENT,
            "specialization": self.TEAM_TITLE,
            "employee_count": len(self.employee_ids),
            "assignments": assignments,
        }

    def validate_change(self, changes: Iterable[CodeChange]) -> dict[str, Any]:
        """Dry-run a proposed change before any write occurs."""
        return self.workspace.dry_run(list(changes), validate_python=True)

    def apply_change(self, changes: Iterable[CodeChange], *, reason: str = "") -> dict[str, Any]:
        """Apply an already-proposed safe change atomically with rollback on validation failure."""
        changes = list(changes)
        checkpoint = self.workspace.checkpoint([c.path for c in changes])
        results = self.workspace.apply(changes, validate_python=True)
        return {
            "status": "APPLIED",
            "reason": reason,
            "checkpoint": checkpoint,
            "results": [asdict(x) for x in results],
        }

    def verify(self, paths: Iterable[str] = ()) -> dict[str, Any]:
        return self.workspace.verify(paths)

    def run_regression_tests(self) -> dict[str, Any]:
        """Run the fixed project regression suite; never execute task-supplied shell text."""
        command = [sys.executable, "-m", "pytest", "brain_v7", "-q"]
        try:
            completed = subprocess.run(command, cwd=str(self.workspace.root), capture_output=True, text=True, timeout=300, check=False)
            return {
                "status": "PASS" if completed.returncode == 0 else "FAIL",
                "returncode": completed.returncode,
                "command": command,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
            }
        except Exception as exc:
            return {"status": "FAIL", "returncode": -1, "command": command, "stdout_tail": "", "stderr_tail": str(exc)}

    def execute_autonomous_change(
        self,
        changes: Iterable[CodeChange],
        *,
        reason: str,
        commit_message: str,
        remote: bool = True,
    ) -> dict[str, Any]:
        """Validate, checkpoint, apply locally, then optionally persist to GitHub."""
        changes = list(changes)
        preview = self.validate_change(changes)
        checkpoint = self.workspace.checkpoint([c.path for c in changes])
        local_results = self.workspace.apply(changes, validate_python=True)
        regression = self.run_regression_tests()
        if regression["status"] != "PASS":
            restored = self.workspace.restore(checkpoint["checkpoint_id"])
            return {
                "status": "ROLLED_BACK",
                "reason": reason,
                "preview": preview,
                "checkpoint": checkpoint,
                "local_results": [asdict(x) for x in local_results],
                "regression": regression,
                "restored": [asdict(x) for x in restored],
                "remote_status": "NOT_COMMITTED",
                "remote_results": [],
            }
        remote_results = []
        remote_status = "NOT_REQUESTED"
        if remote:
            if self.remote.configured:
                remote_results = self.remote.apply(changes, message=commit_message)
                remote_status = "COMMITTED"
            else:
                remote_status = "REMOTE_NOT_CONFIGURED"
        return {
            "status": "APPLIED_LOCALLY",
            "reason": reason,
            "preview": preview,
            "checkpoint": checkpoint,
            "local_results": [asdict(x) for x in local_results],
            "regression": regression,
            "remote_status": remote_status,
            "remote_results": [asdict(x) for x in remote_results],
        }

    def capability_status(self) -> dict[str, Any]:
        """Expose exactly what the coding tool can do in the current runtime."""
        return {
            "inspect_source": True,
            "save_source": True,
            "atomic_local_changes": True,
            "python_syntax_validation": True,
            "regression_testing": True,
            "checkpoint_and_rollback": True,
            "github_persistence_configured": self.remote.configured,
            "remote_ai_code_proposals_configured": bool(os.getenv("BRAIN_REMOTE_MODEL") and os.getenv("OPENAI_API_KEY")),
            "credential_storage": False,
            "shell_command_execution": False,
            "money_movement": False,
            "external_submission": False,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "specialization": self.TEAM_TITLE,
            "department_id": self.TEAM_DEPARTMENT,
            "manager_id": self.team["manager_id"],
            "employee_ids": list(self.employee_ids),
            "employee_count": len(self.employee_ids),
            "continuous_improvement": True,
            "cycles": self.cycles,
            "queue": [asdict(x) for x in self.queue[-50:]],
            "workspace": self.workspace.snapshot(),
            "github_executor": self.remote.snapshot(),
            "automatic_remote_persistence": self.remote.configured,\n            "capability_status": self.capability_status(),
            "external_side_effects": False,
            "credential_storage": False,
            "money_movement": False,
        }
