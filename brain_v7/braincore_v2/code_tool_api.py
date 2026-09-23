"""High-level code tool for the Electronic Brain.

The Brain decides what source change is needed; this tool performs the bounded
mechanics: inspect -> preview -> checkpoint -> validate -> apply -> test ->
optionally persist to GitHub. It never accepts shell commands or credentials.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from .code_workspace_tool import CodeChange, CodeWorkspaceTool
from .code_tool_engineering_team import CodeToolEngineeringTeam


class CodeTool:
    """Single safe interface between Brain reasoning and source-code changes."""

    def __init__(self, workspace: CodeWorkspaceTool, team: CodeToolEngineeringTeam) -> None:
        self.workspace = workspace
        self.team = team

    def inspect(self, path: str) -> dict:
        content = self.workspace.read(path)
        return {
            "status": "OK",
            "path": path,
            "content": content,
            "sha256": self.workspace._sha256(content.encode("utf-8")),
        }

    def preview(self, changes: Iterable[CodeChange]) -> dict:
        changes = list(changes)
        return {
            "dry_run": self.team.validate_change(changes),
            "diff": self.workspace.diff(changes),
        }

    def execute(
        self,
        changes: Iterable[CodeChange],
        *,
        reason: str,
        commit_message: str,
        persist_to_github: bool = True,
    ) -> dict:
        changes = list(changes)
        if not changes:
            return {"status": "NO_CHANGES", "results": []}
        return self.team.execute_autonomous_change(
            changes,
            reason=reason,
            commit_message=commit_message,
            remote=persist_to_github,
        )

    def verify(self, paths: Iterable[str] = ()) -> dict:
        return self.workspace.verify(paths)

    def snapshot(self) -> dict:
        return {
            "interface": "BRAIN_CODE_TOOL",
            "inspect": True,
            "preview_diff": True,
            "checkpoint": True,
            "atomic_local_apply": True,
            "syntax_validation": True,
            "regression_tests": True,
            "rollback": True,
            "github_persistence": self.team.remote.configured,
            "shell_execution": False,
            "credential_access": False,
            "money_movement": False,
        }
