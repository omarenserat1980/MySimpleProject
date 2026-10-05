"""Durable Brain-owned local task runtime.

The runtime survives process restarts through an append-only queue and state
snapshot. It has no GitHub dependency and refuses execution unless the
Brain-owned runner proves its required capability.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

from .execution_gateway import BrainExecutionGateway


class InternalTaskRuntime:
    def __init__(self, root: str | Path = ".brain/internal_runtime",
                 gateway: BrainExecutionGateway | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.queue = self.root / "queue.jsonl"
        self.state_file = self.root / "state.json"
        self.evidence_dir = self.root / "evidence"
        self.evidence_dir.mkdir(exist_ok=True)
        self.gateway = gateway or BrainExecutionGateway()

    def enqueue(self, task: str, argv: list[str], capability: str = "brain-internal-execution",
                metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        item = {
            "id": uuid.uuid4().hex,
            "task": task,
            "argv": list(argv),
            "capability": capability,
            "metadata": metadata or {},
            "created_at": time.time(),
            "state": "PENDING",
        }
        with self.queue.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item

    def pending(self) -> list[dict[str, Any]]:
        state = self._load_state()
        done = set(state.get("terminal_ids", []))
        items = []
        if self.queue.exists():
            for line in self.queue.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if item["id"] not in done:
                        items.append(item)
        return items

    def run_one(self, timeout: int | None = None) -> dict[str, Any]:
        items = self.pending()
        if not items:
            return {"ok": True, "state": "IDLE"}
        item = items[0]
        started = time.time()
        try:
            result = self.gateway.run(item["argv"], capability=item["capability"],
                                     timeout=timeout)
            state = "COMPLETED" if result["ok"] else "FAILED"
            evidence = {
                "task_id": item["id"],
                "task": item["task"],
                "state": state,
                "executor": result["executor"],
                "authority": result["authority"],
                "verified_executor": result["verified_executor"],
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "duration_seconds": round(time.time() - started, 3),
            }
        except Exception as exc:
            state = "BLOCKED"
            evidence = {
                "task_id": item["id"], "task": item["task"], "state": state,
                "error": f"{type(exc).__name__}:{exc}",
                "duration_seconds": round(time.time() - started, 3),
            }
        raw = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
        digest = hashlib.sha256(raw).hexdigest()
        evidence["sha256"] = digest
        ref = self.evidence_dir / f"{item['id']}.json"
        ref.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        state_data = self._load_state()
        terminal = set(state_data.get("terminal_ids", []))
        terminal.add(item["id"])
        state_data["terminal_ids"] = sorted(terminal)
        state_data["last_task_id"] = item["id"]
        state_data["last_state"] = state
        state_data["last_evidence"] = str(ref)
        self.state_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
        return {**evidence, "evidence_ref": str(ref)}

    def status(self) -> dict[str, Any]:
        state = self._load_state()
        return {
            "runtime": "brain-internal",
            "github_dependency": False,
            "pending": len(self.pending()),
            "last_task_id": state.get("last_task_id"),
            "last_state": state.get("last_state"),
            "last_evidence": state.get("last_evidence"),
        }

    def _load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {"terminal_ids": []}
        return json.loads(self.state_file.read_text(encoding="utf-8"))
