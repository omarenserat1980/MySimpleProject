#!/usr/bin/env python3
"""Bounded, local-first task runner for Brain Phone Base.

Only fixed, reviewed actions are available. No arbitrary shell, network calls,
node activation, mining, or pool communication are implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "brain-local-executor.task.v1"
MAX_BATCH = 20


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


class LocalExecutor:
    def __init__(self, repo: Path):
        self.repo = repo.resolve()
        if not (self.repo / "brain_phone_base").is_dir():
            raise ValueError(f"Not a Brain Phone Base repository root: {self.repo}")
        self.state_dir = self.repo / ".brain_local_executor"
        self.queue_path = self.state_dir / "queue.json"
        self.audit_path = self.state_dir / "audit.jsonl"

    def _load_queue(self) -> list[dict[str, Any]]:
        if not self.queue_path.exists():
            return []
        data = json.loads(self.queue_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("QUEUE_FORMAT_INVALID")
        return data

    def _save_queue(self, queue: list[dict[str, Any]]) -> None:
        atomic_json(self.queue_path, queue)

    def _audit(self, event: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        previous = "0" * 64
        if self.audit_path.exists():
            with self.audit_path.open("rb") as stream:
                for line in stream:
                    try:
                        previous = json.loads(line).get("event_hash", previous)
                    except (json.JSONDecodeError, AttributeError):
                        previous = "INVALID_PREVIOUS_AUDIT"
        record = {"at_utc": utc_now(), "previous_hash": previous, **event}
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        record["event_hash"] = sha256_bytes(canonical)
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def enqueue(self, action: str) -> dict[str, Any]:
        if action not in self.actions():
            raise ValueError(f"ACTION_NOT_ALLOWED:{action}")
        queue = self._load_queue()
        task = {"schema": SCHEMA, "task_id": str(uuid.uuid4()), "action": action,
                "status": "queued", "created_at_utc": utc_now(), "result": None}
        queue.append(task)
        self._save_queue(queue)
        self._audit({"event": "task_queued", "task_id": task["task_id"], "action": action})
        return task

    @staticmethod
    def actions() -> tuple[str, ...]:
        return ("status", "test-measurement", "measure", "verify-evidence")

    def _run_action(self, action: str) -> dict[str, Any]:
        if action == "status":
            proc = subprocess.run(["git", "status", "--short"], cwd=self.repo,
                                  capture_output=True, text=True, timeout=20, check=False)
            return {"exit_code": proc.returncode, "stdout": proc.stdout[-12000:],
                    "stderr": proc.stderr[-4000:]}
        if action == "test-measurement":
            proc = subprocess.run([sys.executable, "-m", "unittest",
                                   "brain_phone_base.test_android_real_measurement", "-v"],
                                  cwd=self.repo, capture_output=True, text=True, timeout=120, check=False)
            return {"exit_code": proc.returncode, "stdout": proc.stdout[-12000:],
                    "stderr": proc.stderr[-12000:]}
        if action == "measure":
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            suffix = uuid.uuid4().hex[:8]
            output = self.repo / "evidence" / f"phone-real-measurement-{stamp}-{suffix}.json"
            proc = subprocess.run([sys.executable, "-m", "brain_phone_base.android_real_measurement",
                                   "--output", str(output)], cwd=self.repo,
                                  capture_output=True, text=True, timeout=30, check=False)
            result: dict[str, Any] = {"exit_code": proc.returncode, "stdout": proc.stdout[-4000:],
                                      "stderr": proc.stderr[-4000:]}
            if proc.returncode == 0 and output.is_file():
                result["evidence_path"] = str(output.relative_to(self.repo))
                result["evidence_sha256"] = sha256_bytes(output.read_bytes())
            return result
        if action == "verify-evidence":
            return self.verify_evidence()
        raise ValueError(f"ACTION_NOT_ALLOWED:{action}")

    def verify_evidence(self) -> dict[str, Any]:
        candidates = sorted((self.repo / "evidence").glob("phone-real-measurement*.json"))
        if not candidates:
            return {"exit_code": 2, "status": "BLOCKED", "reason": "NO_EVIDENCE_FILE",
                    "independent_identity_verification": "NOT_PERFORMED",
                    "node_activation": "PROHIBITED_BY_DEFAULT", "mining": "DISABLED", "findings": []}
        findings: list[dict[str, Any]] = []
        for path in candidates:
            try:
                raw = path.read_bytes()
                data = json.loads(raw)
                if data.get("schema") != "brain-phone-base.real-measurement.v1":
                    raise ValueError("SCHEMA_INVALID")
                gate = data["node_gate"]
                evidence = data["evidence"]
                network = data["network_actions"]
                required_gate = {
                    "state": "untrusted_inactive", "trusted": False, "active": False,
                    "activation_allowed": False, "manual_approval": "not_granted",
                }
                for key, expected in required_gate.items():
                    if gate.get(key) != expected or type(gate.get(key)) is not type(expected):
                        raise ValueError(f"NODE_GATE_INVALID:{key}")
                required_evidence = {
                    "device_identity_verified": False,
                    "independent_verification": "not_performed",
                    "integrity_signature": None,
                }
                for key, expected in required_evidence.items():
                    if evidence.get(key, object()) != expected or type(evidence.get(key, object())) is not type(expected):
                        raise ValueError(f"EVIDENCE_GATE_INVALID:{key}")
                for key in ("measurement_uploaded", "node_registered", "mining_started", "mining_pool_contacted"):
                    if network.get(key) is not False:
                        raise ValueError(f"NETWORK_GATE_NOT_CLOSED:{key}")
                findings.append({"path": str(path.relative_to(self.repo)), "status": "PASS_LOCAL_CONTRACT_ONLY",
                                 "measured_at_utc": data.get("measured_at_utc", data.get("timestamp")),
                                 "sha256": sha256_bytes(raw)})
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                findings.append({"path": str(path.relative_to(self.repo)), "status": "FAIL",
                                 "reason": str(exc)[:300]})
        ok = all(item["status"] == "PASS_LOCAL_CONTRACT_ONLY" for item in findings)
        return {"exit_code": 0 if ok else 2,
                "status": "PASS_LOCAL_CONTRACT_ONLY" if ok else "BLOCKED",
                "independent_identity_verification": "NOT_PERFORMED",
                "node_activation": "PROHIBITED_BY_DEFAULT",
                "mining": "DISABLED",
                "findings": findings}

    def run_next(self) -> dict[str, Any] | None:
        queue = self._load_queue()
        index = next((i for i, task in enumerate(queue) if task.get("status") == "queued"), None)
        if index is None:
            return None
        task = queue[index]
        action = task.get("action")
        if action not in self.actions():
            task["status"] = "blocked"
            task["result"] = {"reason": "ACTION_NOT_ALLOWED"}
            self._save_queue(queue)
            self._audit({"event": "task_blocked", "task_id": task.get("task_id"), "action": action})
            return task
        task["status"] = "running"
        task["started_at_utc"] = utc_now()
        self._save_queue(queue)
        self._audit({"event": "task_started", "task_id": task["task_id"], "action": action})
        try:
            result = self._run_action(action)
            task["result"] = result
            task["status"] = "succeeded" if result.get("exit_code") == 0 else "failed"
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            task["result"] = {"reason": type(exc).__name__, "message": str(exc)[:500]}
            task["status"] = "failed"
        task["finished_at_utc"] = utc_now()
        self._save_queue(queue)
        self._audit({"event": "task_finished", "task_id": task["task_id"], "action": action,
                     "status": task["status"], "result_sha256": sha256_bytes(json.dumps(task["result"], sort_keys=True).encode())})
        return task

    def run_all(self, limit: int) -> list[dict[str, Any]]:
        if limit < 1 or limit > MAX_BATCH:
            raise ValueError(f"LIMIT_MUST_BE_1_TO_{MAX_BATCH}")
        results = []
        for _ in range(limit):
            task = self.run_next()
            if task is None:
                break
            results.append(task)
            if task.get("status") != "succeeded":
                break
        return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root (must contain brain_phone_base/)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list-actions", help="List fixed, allowed actions")
    enqueue = sub.add_parser("enqueue", help="Queue a fixed local action")
    enqueue.add_argument("action", choices=LocalExecutor.actions())
    sub.add_parser("run-next", help="Run one queued task")
    batch = sub.add_parser("run-all", help="Run queued tasks, stopping on first failure")
    batch.add_argument("--limit", type=int, default=5)
    sub.add_parser("queue", help="Show queued task state")
    sub.add_parser("verify-now", help="Validate all local measurement JSON files without network access")
    args = parser.parse_args(argv)
    try:
        if args.command == "list-actions":
            print(json.dumps({"actions": list(LocalExecutor.actions()), "arbitrary_shell": False,
                              "network": False, "node_activation": False, "mining": False}, indent=2))
            return 0
        executor = LocalExecutor(Path(args.repo))
        if args.command == "enqueue":
            result: Any = executor.enqueue(args.action)
        elif args.command == "run-next":
            result = executor.run_next()
        elif args.command == "run-all":
            result = executor.run_all(args.limit)
        elif args.command == "queue":
            result = executor._load_queue()
        else:
            result = executor.verify_evidence()
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        if isinstance(result, dict) and "exit_code" in result:
            return int(result["exit_code"])
        if isinstance(result, list) and any(item.get("status") != "succeeded" for item in result):
            return 2
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)[:500]}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
