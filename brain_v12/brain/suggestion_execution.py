"""ChatGPT suggestion-to-execution policy for Electronic Brain.

Suggestions become executable only through registered Brain tools, validation,
permission checks, and post-execution evidence. This module never executes
arbitrary generated Python, shell, PowerShell, or remote commands.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping
import hashlib
import json
import time


SCHEMA = "brain.suggestion-execution.v1"


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    title: str
    rationale: str
    tool_name: str
    arguments: Mapping[str, Any]
    risk: str = "low"
    requires_approval: bool = False

    def public(self) -> dict[str, Any]:
        return asdict(self)


class BrainSuggestionExecutor:
    """Validates proposals and invokes only explicitly registered Brain tools."""

    def __init__(
        self,
        *,
        tool_registry: Mapping[str, Callable[..., Any]] | None = None,
        audit_sink: Callable[[dict[str, Any]], None] | None = None,
        dry_run: bool = True,
    ):
        self.tools = dict(tool_registry or {})
        self.audit_sink = audit_sink
        self.dry_run = bool(dry_run)
        self.history: list[dict[str, Any]] = []

    @staticmethod
    def proposal_id(title: str, tool_name: str, arguments: Mapping[str, Any]) -> str:
        payload = json.dumps(
            {"title": title, "tool_name": tool_name, "arguments": arguments},
            sort_keys=True, default=str, separators=(",", ":"),
        )
        return "proposal-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def propose(
        self, *, title: str, rationale: str, tool_name: str,
        arguments: Mapping[str, Any], risk: str = "low",
        requires_approval: bool = False,
    ) -> dict[str, Any]:
        if not title.strip() or not rationale.strip() or not tool_name.strip():
            return {"ok": False, "status": "INVALID_PROPOSAL"}
        if tool_name not in self.tools:
            return {"ok": False, "status": "TOOL_NOT_REGISTERED",
                    "tool_name": tool_name, "reality": "POLICY"}
        proposal = ActionProposal(
            proposal_id=self.proposal_id(title, tool_name, arguments),
            title=title, rationale=rationale, tool_name=tool_name,
            arguments=dict(arguments), risk=risk,
            requires_approval=bool(requires_approval),
        )
        return {"ok": True, "status": "PROPOSED", "schema": SCHEMA,
                "proposal": proposal.public(), "dry_run": self.dry_run}

    def execute(
        self, proposal: Mapping[str, Any], *,
        approved: bool = False, allow_mutation: bool = False,
    ) -> dict[str, Any]:
        p = dict(proposal)
        required = {"proposal_id", "title", "rationale", "tool_name", "arguments"}
        if not required.issubset(p):
            return {"ok": False, "status": "INVALID_PROPOSAL_SHAPE"}
        tool_name = str(p["tool_name"])
        tool = self.tools.get(tool_name)
        if tool is None:
            return {"ok": False, "status": "TOOL_NOT_REGISTERED",
                    "tool_name": tool_name}
        risk = str(p.get("risk", "low")).lower()
        if risk not in {"low", "medium", "high", "critical"}:
            return {"ok": False, "status": "INVALID_RISK"}
        if p.get("requires_approval") and not approved:
            return {"ok": False, "status": "APPROVAL_REQUIRED",
                    "proposal_id": p["proposal_id"]}
        if risk in {"high", "critical"} and not approved:
            return {"ok": False, "status": "APPROVAL_REQUIRED",
                    "proposal_id": p["proposal_id"]}
        if self.dry_run:
            return {"ok": True, "status": "DRY_RUN", "proposal_id": p["proposal_id"],
                    "tool_name": tool_name, "executed": False}
        if risk in {"medium", "high", "critical"} and not allow_mutation:
            return {"ok": False, "status": "MUTATION_GATE_BLOCKED",
                    "proposal_id": p["proposal_id"]}
        started = time.time()
        try:
            result = tool(**dict(p["arguments"]))
            record = {
                "ok": True, "status": "EXECUTED", "schema": SCHEMA,
                "proposal_id": p["proposal_id"], "tool_name": tool_name,
                "started_at": started, "finished_at": time.time(),
                "result": result, "evidence_required": True,
            }
        except Exception as exc:
            record = {
                "ok": False, "status": "EXECUTION_FAILED", "schema": SCHEMA,
                "proposal_id": p["proposal_id"], "tool_name": tool_name,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500], "finished_at": time.time(),
            }
        self.history.append(record)
        if self.audit_sink:
            self.audit_sink(dict(record))
        return record

    def verify(self, execution: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
        if execution.get("status") != "EXECUTED" or not execution.get("ok"):
            return {"ok": False, "status": "EXECUTION_NOT_SUCCESSFUL"}
        if not evidence or not evidence.get("verified"):
            return {"ok": False, "status": "EVIDENCE_REQUIRED",
                    "proposal_id": execution.get("proposal_id")}
        return {"ok": True, "status": "VERIFIED", "proposal_id": execution.get("proposal_id"),
                "evidence": dict(evidence)}

    def status(self) -> dict[str, Any]:
        return {
            "ok": True, "schema": SCHEMA, "mode": "DRY_RUN" if self.dry_run else "REGISTERED_TOOLS_ONLY",
            "registered_tools": sorted(self.tools), "history_count": len(self.history),
            "arbitrary_code_execution": False,
            "approval_for_high_risk": True,
        }
