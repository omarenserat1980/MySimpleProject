"""Download-Manager-style parallel stage scheduler for Brain.

Parallelizes only dependency-ready stages. Each stage gets an independent
checkpoint/evidence record and verified cache entry. Execution success never
implies verification success.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class Stage:
    id: str
    depends_on: tuple[str, ...] = ()
    resource: str | None = None
    input_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


Executor = Callable[[Stage], dict[str, Any]]
Verifier = Callable[[Stage, dict[str, Any]], dict[str, Any] | bool]


class ParallelStageScheduler:
    """Dependency-aware bounded scheduler with verified stage caching."""

    def __init__(self, stages: list[Stage], state_dir: str | Path,
                 max_workers: int = 4, retry_limit: int = 1) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if retry_limit < 0:
            raise ValueError("retry_limit must be >= 0")
        self.stages = {s.id: s for s in stages}
        if len(self.stages) != len(stages):
            raise ValueError("duplicate stage id")
        missing = {d for s in stages for d in s.depends_on if d not in self.stages}
        if missing:
            raise ValueError(f"missing dependencies: {sorted(missing)}")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.retry_limit = retry_limit
        self._validate_acyclic()

    def _validate_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(stage_id: str) -> None:
            if stage_id in visiting:
                raise ValueError(f"cyclic dependency involving: {stage_id}")
            if stage_id in visited:
                return
            visiting.add(stage_id)
            for dep in self.stages[stage_id].depends_on:
                visit(dep)
            visiting.remove(stage_id)
            visited.add(stage_id)

        for stage_id in self.stages:
            visit(stage_id)

    def _record_path(self, stage: Stage) -> Path:
        return self.state_dir / f"{stage.id.replace('/', '_')}.json"

    def _fingerprint(self, stage: Stage) -> str:
        payload = {"id": stage.id, "depends_on": stage.depends_on,
                   "input_fingerprint": stage.input_fingerprint}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _read_verified_cache(self, stage: Stage) -> dict[str, Any] | None:
        path = self._record_path(stage)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if (data.get("status") == "VERIFIED_COMPLETED"
                and data.get("fingerprint") == self._fingerprint(stage)
                and data.get("evidence_ref")):
            return data
        return None

    def _write(self, stage: Stage, data: dict[str, Any]) -> None:
        self._record_path(stage).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def ready(self, completed: set[str], running: set[str]) -> list[Stage]:
        return [s for s in self.stages.values()
                if s.id not in completed and s.id not in running
                and all(d in completed for d in s.depends_on)]

    def run(self, executor: Executor, verifier: Verifier) -> dict[str, Any]:
        completed, blocked, evidence = set(), set(), {}
        running: dict[Any, Stage] = {}
        attempts = {sid: 0 for sid in self.stages}

        for stage in self.stages.values():
            cached = self._read_verified_cache(stage)
            if cached:
                completed.add(stage.id)
                evidence[stage.id] = cached

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while len(completed) + len(blocked) < len(self.stages):
                candidates = self.ready(completed, {s.id for s in running.values()})
                used_resources = {s.resource for s in running.values() if s.resource}

                for stage in candidates:
                    if len(running) >= self.max_workers:
                        continue
                    if stage.resource and stage.resource in used_resources:
                        continue
                    attempts[stage.id] += 1
                    if stage.resource:
                        used_resources.add(stage.resource)
                    running[pool.submit(executor, stage)] = stage

                if not running:
                    unresolved = sorted(set(self.stages) - completed - blocked)
                    blocked_now = [
                        sid for sid in unresolved
                        if any(dep in blocked for dep in self.stages[sid].depends_on)
                    ]
                    if blocked_now:
                        for sid in blocked_now:
                            blocked.add(sid)
                            stage = self.stages[sid]
                            self._write(stage, {
                                "stage_id": sid,
                                "status": "BLOCKED_DEPENDENCY",
                                "fingerprint": self._fingerprint(stage),
                                "depends_on": list(stage.depends_on),
                            })
                        continue
                    raise RuntimeError("SCHEDULER_DEADLOCK_OR_CYCLE:" + ",".join(unresolved))

                future = next(as_completed(list(running)))
                stage = running.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"ok": False, "error": f"EXECUTOR_ERROR:{type(exc).__name__}:{exc}"}

                verification = verifier(stage, result)
                verified = bool(verification) if isinstance(verification, bool) else bool(
                    verification.get("verified"))
                if verified:
                    record = {
                        "stage_id": stage.id, "status": "VERIFIED_COMPLETED",
                        "fingerprint": self._fingerprint(stage),
                        "attempt": attempts[stage.id], "result": result,
                        "verification": verification,
                        "evidence_ref": (verification.get("evidence_ref")
                                         if isinstance(verification, dict) else None)
                                         or f"stage://{stage.id}/verified",
                    }
                    self._write(stage, record)
                    evidence[stage.id] = record
                    completed.add(stage.id)
                elif attempts[stage.id] <= self.retry_limit:
                    continue
                else:
                    blocked.add(stage.id)
                    self._write(stage, {
                        "stage_id": stage.id, "status": "FAILED",
                        "fingerprint": self._fingerprint(stage),
                        "attempt": attempts[stage.id], "result": result,
                        "verification": verification,
                    })

        return {
            "status": "VERIFIED_COMPLETED" if len(completed) == len(self.stages) else "BLOCKED",
            "total": len(self.stages), "completed": sorted(completed),
            "blocked": sorted(blocked), "attempts": attempts,
            "evidence": evidence, "max_workers": self.max_workers,
        }
