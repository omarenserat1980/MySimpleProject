from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import socket

from brain_v12.runner_policy_guard import RunnerPolicyGuard, RunnerPolicyViolation


@dataclass(frozen=True)
class ExecutionAuthority:
    executor_id: str
    owner: str
    persistent: bool
    heartbeat_path: str
    capabilities: tuple[str, ...]


class BrainExecutionAuthority:
    """Single fail-closed authority describing the Brain-owned executor."""

    def __init__(
        self,
        *,
        executor_id: str | None = None,
        heartbeat_path: str | Path | None = None,
        capabilities: tuple[str, ...] = ("ci", "python", "media", "filesystem"),
        max_heartbeat_age_seconds: float = 30.0,
    ) -> None:
        self.executor_id = executor_id or os.environ.get("BRAIN_WORKER_ID", "brain-local-01")
        self.heartbeat_path = Path(
            heartbeat_path or os.environ.get(
                "BRAIN_EXECUTOR_HEARTBEAT",
                "brain6_artifacts/local_worker/heartbeat.json",
            )
        )
        self.capabilities = tuple(capabilities)
        self.max_heartbeat_age_seconds = float(max_heartbeat_age_seconds)
        self.runner_policy_guard = RunnerPolicyGuard()

    def heartbeat(self) -> dict[str, object]:
        self.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "executor_id": self.executor_id,
            "owner": "brain",
            "persistent": True,
            "host": socket.gethostname(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": list(self.capabilities),
        }
        self.heartbeat_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return payload

    def descriptor(self) -> ExecutionAuthority:
        return ExecutionAuthority(
            self.executor_id, "brain", True, str(self.heartbeat_path), self.capabilities
        )

    def readiness(self, required_capability: str = "ci") -> dict[str, object]:
        try:
            policy = self.runner_policy_guard.assert_ready()
        except RunnerPolicyViolation as exc:
            return {"ready": False, "reason": "runner_policy_blocked", "policy_error": str(exc)}
        if not self.heartbeat_path.exists():
            return {"ready": False, "reason": "brain_executor_heartbeat_missing"}
        try:
            payload = json.loads(self.heartbeat_path.read_text(encoding="utf-8"))
            timestamp = datetime.fromisoformat(str(payload["timestamp"]))
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            valid = (
                payload.get("owner") == "brain"
                and payload.get("persistent") is True
                and payload.get("executor_id") == self.executor_id
                and required_capability in payload.get("capabilities", [])
                and age <= self.max_heartbeat_age_seconds
            )
            return {
                "ready": valid,
                "executor": asdict(self.descriptor()),
                "heartbeat_age_seconds": round(age, 3),
                "reason": None if valid else "brain_executor_not_ready",
                "runner_policy": policy,
            }
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return {"ready": False, "reason": "brain_executor_heartbeat_invalid"}


__all__ = ["BrainExecutionAuthority", "ExecutionAuthority"]
