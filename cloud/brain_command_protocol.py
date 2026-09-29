"""Brain -> ChatGPT command protocol.

Brain may emit structured operational requests for ChatGPT. The protocol is
request-only: it does not grant Brain arbitrary execution authority. ChatGPT
or a connected executor must validate the command, permissions, scope, and
evidence before executing it.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "STATE" / "brain_commands"

ALLOWED_INTENTS = {
    "inspect",
    "test",
    "repair",
    "verify",
    "produce",
    "report",
    "benchmark",
}

@dataclass(frozen=True)
class BrainCommand:
    command_id: str
    intent: str
    task: str
    reason: str
    evidence_required: tuple[str, ...]
    priority: str = "normal"
    authorization_required: bool = True
    arbitrary_code: bool = False
    created_at: str = ""

    def validate(self) -> None:
        if self.intent not in ALLOWED_INTENTS:
            raise ValueError(f"unsupported Brain command intent: {self.intent}")
        if not self.task.strip():
            raise ValueError("Brain command task cannot be empty")
        if self.arbitrary_code:
            raise ValueError("Brain commands cannot request arbitrary code execution")
        if not self.evidence_required:
            raise ValueError("Brain commands must declare required evidence")


def issue_command(
    intent: str,
    task: str,
    reason: str,
    evidence_required: list[str],
    priority: str = "normal",
) -> dict[str, Any]:
    command = BrainCommand(
        command_id=f"brain-{uuid.uuid4().hex[:12]}",
        intent=intent,
        task=task,
        reason=reason,
        evidence_required=tuple(evidence_required),
        priority=priority,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    command.validate()
    STATE.mkdir(parents=True, exist_ok=True)
    payload = asdict(command)
    payload["evidence_required"] = list(command.evidence_required)
    payload["source"] = "Brain Cloud"
    payload["execution_authority"] = "ChatGPT_or_connected_executor"
    payload["status"] = "REQUESTED"
    path = STATE / f"{command.command_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (STATE / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def latest_command() -> dict[str, Any] | None:
    path = STATE / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
