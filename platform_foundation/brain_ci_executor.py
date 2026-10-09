from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
import hashlib
import json
import subprocess
import sys
import time
import uuid

from .execution_policy import BrainExecutionPolicy, ExecutorDecision, ExecutorDescriptor
from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class BrainCIResult:
    run_id: str
    status: str
    executor_id: str | None
    exit_code: int | None
    duration_seconds: float
    evidence_path: str | None
    evidence_sha256: str | None
    error: str | None = None


class BrainCIExecutor:
    """Fail-closed CI executor owned by Brain.

    It runs only predefined test profiles and never falls back to GitHub Actions.
    """

    STATE_KEY = "brain.ci.last_run"

    PROFILES = {
        "runner_policy": ("tests/test_execution_policy.py", "tests/test_runner_policy_audit.py"),
        "foundation": ("tests/test_platform_foundation.py", "tests/test_brain_supervisor_bridge.py"),
        "autonomous_pipeline": ("tests/test_autonomous_pipeline.py", "tests/test_autonomous_pipeline_execution_health.py"),
    }

    def __init__(
        self,
        store: SQLiteStateStore,
        *,
        root: str | Path = ".",
        executor_id: str = "brain-ci-01",
        persistent: bool = True,
        runner: Callable[[list[str], Path], tuple[int, str, str]] | None = None,
    ) -> None:
        self.store = store
        self.root = Path(root)
        self.executor = ExecutorDescriptor(
            executor_id, "brain", persistent, frozenset({"python", "pytest"})
        )
        self.policy = BrainExecutionPolicy()
        self._runner = runner or self._run_local

    @classmethod
    def from_local_worker(cls, store: SQLiteStateStore, *, root: str | Path = "."):
        """Construct the Brain-owned executor using the local Brain runtime."""
        return cls(store, root=root, executor_id="brain-local-ci", persistent=True)

    def run_profile(self, profile: str, *, commit_sha: str | None = None, run_id: str | None = None) -> BrainCIResult:
        """Explicit Brain runtime entrypoint; never delegates to GitHub Actions."""
        return self.execute(profile, commit_sha=commit_sha, run_id=run_id)

    def readiness(self) -> dict[str, Any]:
        """Fail-closed readiness check for the Brain-owned execution path."""
        decision = self.policy.select(
            [self.executor],
            required_capabilities={"python", "pytest"},
        )
        return {
            "ready": decision.decision is ExecutorDecision.ALLOWED,
            "decision": decision.decision.value,
            "executor_id": self.executor.executor_id if decision.decision is ExecutorDecision.ALLOWED else None,
            "reason": decision.reason,
            "owner": self.executor.owner,
            "persistent": self.executor.persistent,
        }

    def _run_local(self, command: list[str], root: Path) -> tuple[int, str, str]:
        p = subprocess.run(command, cwd=root, capture_output=True, text=True)
        return p.returncode, p.stdout[-12000:], p.stderr[-12000:]

    def execute(self, profile: str, *, commit_sha: str | None = None, run_id: str | None = None) -> BrainCIResult:
        if profile not in self.PROFILES:
            raise ValueError(f"unknown_ci_profile:{profile}")

        rid = run_id or f"brain-ci-{uuid.uuid4().hex}"
        decision = self.policy.select([self.executor], required_capabilities={"python", "pytest"})
        if decision.decision is not ExecutorDecision.ALLOWED:
            result = BrainCIResult(rid, "BLOCKED", None, None, 0.0, None, None, decision.reason)
            self.store.set(self.STATE_KEY, asdict(result))
            return result

        tests = [str(self.root / item) for item in self.PROFILES[profile]]
        command = [sys.executable, "-m", "pytest", "-q", *tests]
        started = time.monotonic()
        exit_code, stdout, stderr = self._runner(command, self.root)
        duration = round(time.monotonic() - started, 6)

        evidence = {
            "run_id": rid, "profile": profile, "commit_sha": commit_sha,
            "executor_id": self.executor.executor_id, "owner": "brain",
            "persistent": self.executor.persistent, "command": command,
            "exit_code": exit_code, "duration_seconds": duration,
            "stdout": stdout, "stderr": stderr,
            "status": "VERIFIED" if exit_code == 0 else "FAILED",
        }
        out = self.root / "brain6_artifacts" / "ci_evidence"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{rid}.json"
        encoded = json.dumps(evidence, indent=2, sort_keys=True).encode("utf-8")
        path.write_bytes(encoded)
        digest = hashlib.sha256(encoded).hexdigest()

        result = BrainCIResult(
            rid, evidence["status"], self.executor.executor_id, exit_code,
            duration, str(path), digest,
            None if exit_code == 0 else "brain_ci_tests_failed",
        )
        self.store.set(self.STATE_KEY, asdict(result))
        return result

    def evidence(self, run_id: str | None = None) -> dict[str, Any] | None:
        last = self.store.get(self.STATE_KEY)
        if not last:
            return None
        if run_id is not None and last.get("run_id") != run_id:
            return None
        path = last.get("evidence_path")
        if not path:
            return None
        evidence_path = Path(path)
        if not evidence_path.exists():
            return None
        return json.loads(evidence_path.read_text(encoding="utf-8"))

    def health(self) -> dict[str, Any]:
        return {
            "healthy": self.executor.persistent and self.policy.is_brain_owned(self.executor),
            "executor_id": self.executor.executor_id,
            "owner": self.executor.owner,
            "persistent": self.executor.persistent,
            "capabilities": sorted(self.executor.capabilities),
            "last_run": self.store.get(self.STATE_KEY),
        }


__all__ = ["BrainCIExecutor", "BrainCIResult"]
