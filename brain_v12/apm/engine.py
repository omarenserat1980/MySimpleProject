from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import CommandSpec, PipelineState, StageResult, StageSpec


class APMError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def command_from(value: Any) -> CommandSpec:
    if not isinstance(value, dict) or not isinstance(value.get("command"), list) or not value["command"]:
        raise APMError("invalid command specification")
    if not all(isinstance(x, str) and x for x in value["command"]):
        raise APMError("command arguments must be non-empty strings")
    timeout = int(value.get("timeout_seconds", 900))
    if timeout < 1 or timeout > 3600:
        raise APMError("timeout_seconds must be between 1 and 3600")
    return CommandSpec(value["command"], timeout)


def load_pipeline(path: Path) -> tuple[str, list[StageSpec], CommandSpec | None]:
    data = load_json(path)
    if data.get("schema_version") != "apm-pipeline/v1":
        raise APMError("unsupported pipeline schema")
    pipeline_id = str(data.get("pipeline_id", "")).strip()
    if not pipeline_id:
        raise APMError("pipeline_id is required")
    raw = data.get("stages")
    if not isinstance(raw, list) or not raw:
        raise APMError("stages must be a non-empty list")
    stages: list[StageSpec] = []
    ids: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise APMError("each stage must be an object")
        sid = str(item.get("id", "")).strip()
        if not sid or sid in ids:
            raise APMError(f"invalid/duplicate stage id: {sid!r}")
        ids.add(sid)
        repair = tuple(command_from(x) for x in item.get("repair", []))
        max_retries = int(item.get("max_retries", 2))
        verify_wait_seconds = int(item.get("verify_wait_seconds", 0))
        if verify_wait_seconds < 0 or verify_wait_seconds > 300:
            raise APMError("verify_wait_seconds must be between 0 and 300")
        if max_retries < 0 or max_retries > 10:
            raise APMError("max_retries must be between 0 and 10")
        stages.append(StageSpec(
            id=sid, name=str(item.get("name", sid)),
            run=command_from(item["run"]), verify=command_from(item["verify"]),
            repair=repair,
            rollback=command_from(item["rollback"]) if item.get("rollback") else None,
            repair_allowed=bool(item.get("repair_allowed", False)),
            max_retries=max_retries,
            verify_wait_seconds=verify_wait_seconds,
            dependencies=tuple(str(x) for x in item.get("dependencies", [])),
            enabled=bool(item.get("enabled", True)),
        ))
    known = {s.id for s in stages}
    for stage in stages:
        missing = set(stage.dependencies) - known
        if missing:
            raise APMError(f"{stage.id}: missing dependencies: {sorted(missing)}")
    final_verify = command_from(data["final_verify"]) if data.get("final_verify") else None
    return pipeline_id, stages, final_verify


def topo_order(stages: list[StageSpec]) -> list[StageSpec]:
    active = [s for s in stages if s.enabled]
    by_id = {s.id: s for s in active}
    remaining = {s.id: set(s.dependencies) for s in active}
    result: list[StageSpec] = []
    while remaining:
        ready = sorted([sid for sid, deps in remaining.items() if not deps])
        if not ready:
            raise APMError("stage dependency cycle detected")
        for sid in ready:
            result.append(by_id[sid])
            remaining.pop(sid)
            for deps in remaining.values():
                deps.discard(sid)
    return result


class APMEngine:
    def __init__(self, pipeline_file: Path, state_dir: Path, commit_sha: str | None = None):
        self.pipeline_file = pipeline_file
        self.state_dir = state_dir
        self.state_file = state_dir / "checkpoint.json"
        self.evidence_dir = state_dir / "evidence"
        self.lock_file = state_dir / "orchestrator.lock"
        self.commit_sha = commit_sha or os.getenv("GITHUB_SHA", "unknown")

    def _acquire_lock(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {utc_now()}\n".encode())
            os.close(fd)
        except FileExistsError as exc:
            raise APMError("APM_ALREADY_RUNNING") from exc

    def _release_lock(self) -> None:
        self.lock_file.unlink(missing_ok=True)

    def _save_state(self, state: PipelineState) -> None:
        atomic_write_json(self.state_file, state.__dict__)

    def _load_state(self) -> PipelineState | None:
        if not self.state_file.exists():
            return None
        return PipelineState(**load_json(self.state_file))

    @staticmethod
    def _run(command: CommandSpec) -> dict[str, Any]:
        started = time.monotonic()
        try:
            p = subprocess.run(command.command, capture_output=True, text=True,
                               timeout=command.timeout_seconds, check=False,
                               env=os.environ.copy())
            return {"exit_code": p.returncode, "stdout": p.stdout[-12000:],
                    "stderr": p.stderr[-12000:],
                    "duration_seconds": round(time.monotonic() - started, 3)}
        except subprocess.TimeoutExpired as exc:
            return {"exit_code": 124,
                    "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
                    "stderr": (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
                    "timeout": True,
                    "duration_seconds": round(time.monotonic() - started, 3)}

    def _evidence(self, result: StageResult, verify_result: dict[str, Any]) -> Path:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        path = self.evidence_dir / f"{result.stage_id}_evidence.json"
        payload = {
            "schema_version": "apm-evidence/v1",
            "pipeline_id": self._load_pipeline_id(),
            "stage_id": result.stage_id,
            "status": result.status,
            "tests": "PASS" if verify_result.get("exit_code") == 0 else "FAIL",
            "evidence": "COMPLETE",
            "commit_sha": self.commit_sha,
            "attempts": result.attempts,
            "repairs": result.repairs,
            "last_result": result.last_result,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
        }
        atomic_write_json(path, payload)
        return path

    def _load_pipeline_id(self) -> str:
        return load_pipeline(self.pipeline_file)[0]

    def run(self, resume: bool = True) -> dict[str, Any]:
        pipeline_id, stages, final_verify = load_pipeline(self.pipeline_file)
        ordered = topo_order(stages)
        existing = self._load_state() if resume else None
        if existing and existing.pipeline_id != pipeline_id:
            raise APMError("checkpoint belongs to another pipeline")
        if existing and existing.commit_sha not in {self.commit_sha, "unknown"}:
            raise APMError("checkpoint commit does not match current commit")
        completed = set(existing.completed_stages if existing else [])
        failed: set[str] = set()
        blocked = set(existing.blocked_stages if existing else [])
        self._acquire_lock()
        try:
            state = PipelineState("apm-state/v1", pipeline_id, "RUNNING", len(ordered), None,
                                  "INIT", sorted(completed), [], sorted(blocked), 0,
                                  self.commit_sha, existing.last_result if existing else {}, utc_now())
            self._save_state(state)
            for stage in ordered:
                if stage.id in completed:
                    continue
                if any(dep not in completed for dep in stage.dependencies):
                    state.status = "BLOCKED"
                    state.current_stage = stage.id
                    state.current_step = "DEPENDENCY_GATE"
                    state.blocked_stages = sorted(blocked | {stage.id})
                    state.updated_at = utc_now()
                    self._save_state(state)
                    return state.__dict__
                started = utc_now()
                stage_passed = False
                repairs = 0
                last: dict[str, Any] = {}
                for attempt in range(1, stage.max_retries + 2):
                    state.current_stage, state.current_step, state.attempt = stage.id, "EXECUTE", attempt
                    state.updated_at = utc_now()
                    self._save_state(state)
                    run_result = self._run(stage.run)
                    state.current_step = "WAITING_FOR_VERIFY"
                    state.updated_at = utc_now()
                    self._save_state(state)
                    if stage.verify_wait_seconds:
                        time.sleep(stage.verify_wait_seconds)
                    state.current_step = "VERIFY"
                    verify_result = self._run(stage.verify)
                    last = {"run": run_result, "verify": verify_result}
                    if run_result["exit_code"] == 0 and verify_result["exit_code"] == 0:
                        stage_passed = True
                        break
                    if stage.repair_allowed and stage.repair and attempt <= stage.max_retries:
                        state.current_step = "REPAIR"
                        self._save_state(state)
                        for repair in stage.repair:
                            repairs += 1
                            repair_result = self._run(repair)
                            last["repair"] = repair_result
                            if repair_result["exit_code"] != 0:
                                break
                        continue
                    break
                finished = utc_now()
                if stage_passed:
                    sr = StageResult(stage.id, "PASS", attempt, repairs, started, finished, last)
                    self._evidence(sr, last["verify"])
                    completed.add(stage.id)
                    state.completed_stages = sorted(completed)
                    state.current_step = "EVIDENCE"
                    state.last_result = last
                    state.updated_at = utc_now()
                    self._save_state(state)
                    continue
                if stage.rollback:
                    state.current_step = "ROLLBACK"
                    last["rollback"] = self._run(stage.rollback)
                failed.add(stage.id)
                state.status, state.current_step = "FAILED", "FAILED"
                state.failed_stages = sorted(failed)
                state.last_result, state.updated_at = last, utc_now()
                self._save_state(state)
                return state.__dict__
            if final_verify:
                state.current_stage, state.current_step = None, "FINAL_VERIFY"
                self._save_state(state)
                final_result = self._run(final_verify)
                state.last_result = {"final_verify": final_result}
                if final_result["exit_code"] != 0:
                    state.status, state.current_step = "FAILED", "FINAL_VERIFY_FAILED"
                    state.updated_at = utc_now()
                    self._save_state(state)
                    return state.__dict__
            state.status, state.current_step, state.current_stage = "PASS", "COMPLETE", None
            state.updated_at = utc_now()
            self._save_state(state)
            return state.__dict__
        finally:
            self._release_lock()


def verify_evidence(state_dir: Path) -> dict[str, Any]:
    state_path = state_dir / "checkpoint.json"
    if not state_path.exists():
        raise APMError("checkpoint missing")
    state = load_json(state_path)
    evidence_dir = state_dir / "evidence"
    expected = set(state["completed_stages"])
    actual = {p.stem.removesuffix("_evidence") for p in evidence_dir.glob("*_evidence.json")}
    missing = sorted(expected - actual)
    invalid = []
    for sid in sorted(expected & actual):
        d = load_json(evidence_dir / f"{sid}_evidence.json")
        if not (d.get("status") == "PASS" and d.get("tests") == "PASS" and d.get("evidence") == "COMPLETE"):
            invalid.append(sid)
    ok = state["status"] == "PASS" and not missing and not invalid and len(expected) == state["total_stages"]
    return {"status": "PASS" if ok else "FAILED", "total_stages": state["total_stages"],
            "passed": len(expected), "missing_evidence": missing,
            "invalid_evidence": invalid, "checkpoint": str(state_path)}
