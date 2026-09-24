"""Brain-directed coding agent for Electronic Brain V12.

It connects the reasoning model to the bounded CodeTool. The model may propose
complete file replacements, but the CodeTool remains the only write boundary.
No secrets are exposed to the model or browser.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from brain_v7.braincore_v2.code_workspace_tool import CodeChange, CodeWorkspaceTool
from brain_v7.braincore_v2.code_tool_api import CodeTool
from .openai_provider import OpenAIProvider


@dataclass
class BrainCodePlan:
    objective: str
    changes: list[CodeChange]
    explanation: str
    model: str = ""


class BrainCodeAgent:
    """Reason -> inspect -> propose -> validate -> execute through CodeTool."""

    def __init__(self, provider: OpenAIProvider, tool: CodeTool, workspace: CodeWorkspaceTool) -> None:
        self.provider = provider
        self.tool = tool
        self.workspace = workspace

    def _context(self, files: Iterable[str]) -> str:
        parts = []
        for path in files:
            content = self.workspace.read(path)
            if len(content) > 120_000:
                raise ValueError(f"FILE_TOO_LARGE_FOR_REASONING:{path}")
            parts.append(f"=== FILE: {path} ===\n{content}")
        return "\n\n".join(parts)

    def plan(self, objective: str, files: list[str]) -> dict[str, Any]:
        objective = objective.strip()
        if not objective:
            raise ValueError("EMPTY_OBJECTIVE")
        if not files:
            raise ValueError("NO_FILES")
        context = self._context(files)
        instructions = (
            "You are the coding/reasoning component of Electronic Brain V12. "
            "Return ONLY valid JSON with keys explanation and changes. "
            "changes must be an array of objects with path, content, reason. "
            "Return complete replacement file content, not a patch. "
            "Only modify files under brain_v7/. Do not create credentials, secrets, "
            "shell commands, destructive operations, or network calls. "
            "Prefer the smallest testable change. Never claim that a change was applied."
        )
        prompt = f"Objective: {objective}\n\n{context}"
        result = self.provider.respond(prompt, instructions=instructions)
        if not result.get("ok"):
            return {"status": "MODEL_ERROR", "error": result.get("error"), "detail": result.get("detail", "")}
        try:
            payload = json.loads(result.get("reply", ""))
            raw = payload.get("changes", [])
            changes = [
                CodeChange(str(item["path"]), str(item["content"]), str(item.get("reason", "")))
                for item in raw
            ]
        except (ValueError, TypeError, KeyError) as exc:
            return {"status": "INVALID_MODEL_JSON", "error": str(exc)}
        if not changes:
            return {"status": "NO_CHANGES_PROPOSED", "explanation": payload.get("explanation", "")}
        preview = self.tool.preview(changes)
        return {
            "status": "PLAN_READY",
            "objective": objective,
            "explanation": payload.get("explanation", ""),
            "model": result.get("model", ""),
            "changes": [{"path": c.path, "reason": c.reason} for c in changes],
            "preview": preview,
            "_changes": changes,
        }

    def execute_plan(
        self,
        plan: dict[str, Any],
        *,
        approved: bool,
        commit_message: str = "brain: validated self-improvement",
        persist_to_github: bool = True,
    ) -> dict[str, Any]:
        if not approved:
            return {"status": "EXPLICIT_APPROVAL_REQUIRED"}
        changes = plan.get("_changes", [])
        if not changes:
            return {"status": "NO_EXECUTABLE_PLAN"}
        result = self.tool.execute(
            changes,
            reason=str(plan.get("objective", "brain-directed improvement")),
            commit_message=commit_message,
            persist_to_github=persist_to_github,
        )
        return {"status": result.get("status"), "result": result}

    @staticmethod
    def public_plan(plan: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in plan.items() if k != "_changes"}
