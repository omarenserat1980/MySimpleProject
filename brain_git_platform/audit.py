from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

from .service import ROOT


class AuditLog:
    def __init__(self, root: Path | None = None):
        self.path = (root or ROOT) / "audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _previous_hash(self) -> str:
        if not self.path.exists():
            return ""
        with self.path.open("rb") as handle:
            last = b""
            for line in handle:
                if line.strip():
                    last = line.strip()
        return hashlib.sha256(last).hexdigest() if last else ""

    def record(self, actor: str, action: str, resource: str, outcome: str = "success", metadata: dict | None = None):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "resource": resource,
            "outcome": outcome,
            "metadata": metadata or {},
            "previous_hash": self._previous_hash(),
        }
        encoded = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        event["event_hash"] = hashlib.sha256(encoded).hexdigest()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event
