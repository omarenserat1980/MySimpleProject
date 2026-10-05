"""BRAIN Cloud Fabric: a provider-neutral private-cloud control plane.

This is the Brain-owned layer above infrastructure providers. It does not pretend
to be a hypervisor or create physical compute; it registers compute nodes,
tracks capacity/health, persists jobs, and chooses an eligible node.
"""
from __future__ import annotations
import json, os, threading, time, uuid
from pathlib import Path
from typing import Any

DEFAULT_STATE = Path(os.getenv("BRAIN_STATE_DIR", ".brain_state")) / "fabric"
_LOCK = threading.RLock()

def _state_dir() -> Path:
    p = Path(os.getenv("BRAIN_FABRIC_STATE_DIR", str(DEFAULT_STATE)))
    p.mkdir(parents=True, exist_ok=True)
    return p

def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _read(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def _validate_id(value: str) -> str:
    value = value.strip()
    if not value or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in value):
        raise ValueError("invalid fabric id")
    return value

def _now() -> float:
    return time.time()

def register_node(name: str, *, provider: str = "self-hosted",
                  architecture: str = "unknown", cpu: float = 0,
                  memory_mb: int = 0, storage_gb: int = 0,
                  capabilities: list[str] | None = None,
                  endpoint: str | None = None) -> dict[str, Any]:
    node_id = _validate_id(name)
    record = {
        "node_id": node_id, "name": node_id,
        "provider": provider.strip() or "self-hosted",
        "architecture": architecture.strip() or "unknown",
        "capacity": {"cpu": float(cpu), "memory_mb": int(memory_mb), "storage_gb": int(storage_gb)},
        "capabilities": sorted(set(str(x).strip() for x in (capabilities or []) if str(x).strip())),
        "endpoint": endpoint, "state": "READY", "last_heartbeat": _now(),
        "registered_at": _now(), "jobs_running": 0,
    }
    with _LOCK:
        _atomic_write(_state_dir() / f"node-{node_id}.json", record)
    return record

def heartbeat(node_id: str, *, state: str = "READY", jobs_running: int = 0) -> dict[str, Any]:
    node_id = _validate_id(node_id)
    path = _state_dir() / f"node-{node_id}.json"
    with _LOCK:
        record = _read(path)
        if not record:
            raise KeyError(node_id)
        record["state"] = state.strip().upper() or "READY"
        record["jobs_running"] = max(0, int(jobs_running))
        record["last_heartbeat"] = _now()
        _atomic_write(path, record)
    return record

def update_node(node_id: str, **changes: Any) -> dict[str, Any]:
    """Apply a validated partial node update and persist it atomically."""
    node_id = _validate_id(node_id)
    allowed = {"provider", "architecture", "endpoint", "capabilities", "state", "jobs_running"}
    capacity_allowed = {"cpu", "memory_mb", "storage_gb"}
    unknown = set(changes) - allowed - capacity_allowed
    if unknown:
        raise ValueError("unsupported node fields: " + ",".join(sorted(unknown)))
    path = _state_dir() / f"node-{node_id}.json"
    with _LOCK:
        record = _read(path)
        if not record:
            raise KeyError(node_id)
        for key in allowed:
            if key in changes and changes[key] is not None:
                if key == "capabilities":
                    record[key] = sorted(set(str(x).strip() for x in changes[key] if str(x).strip()))
                elif key == "jobs_running":
                    record[key] = max(0, int(changes[key]))
                elif key == "state":
                    record[key] = str(changes[key]).strip().upper() or "READY"
                elif key in {"provider", "architecture", "endpoint"}:
                    record[key] = changes[key]
        for key in capacity_allowed:
            if key in changes and changes[key] is not None:
                record.setdefault("capacity", {})[key] = int(changes[key]) if key != "cpu" else float(changes[key])
        _atomic_write(path, record)
    return record

def list_nodes() -> list[dict[str, Any]]:
    with _LOCK:
        items = [_read(p) for p in sorted(_state_dir().glob("node-*.json"))]
    return [x for x in items if x]

def _eligible(node: dict[str, Any], required: set[str]) -> bool:
    if node.get("state") not in {"READY", "RUNNING"}:
        return False
    if _now() - float(node.get("last_heartbeat", 0)) > float(os.getenv("BRAIN_FABRIC_HEARTBEAT_TIMEOUT", "120")):
        return False
    return required.issubset(set(node.get("capabilities", [])))

def choose_node(required_capabilities: list[str] | None = None) -> dict[str, Any]:
    # Recover abandoned worker leases before scheduling new work.
    recover_expired_jobs()
    required = {str(x).strip() for x in (required_capabilities or []) if str(x).strip()}
    candidates = [n for n in list_nodes() if _eligible(n, required)]
    if not candidates:
        raise RuntimeError("NO_ELIGIBLE_BRAIN_FABRIC_NODE")
    return min(candidates, key=lambda n: (int(n.get("jobs_running", 0)), n["node_id"]))

def create_job(kind: str, payload: dict[str, Any], required_capabilities: list[str] | None = None) -> dict[str, Any]:
    node = choose_node(required_capabilities)
    job = {
        "job_id": uuid.uuid4().hex, "kind": kind.strip() or "generic",
        "payload": payload, "required_capabilities": list(required_capabilities or []),
        "node_id": node["node_id"], "state": "QUEUED",
        "created_at": _now(), "updated_at": _now(), "evidence": [],
    }
    with _LOCK:
        _atomic_write(_state_dir() / f"job-{job['job_id']}.json", job)
    return job

def next_node_job(node_id: str, required_capabilities: list[str] | None = None) -> dict[str, Any] | None:
    """Lease the oldest queued job assigned to a healthy node."""
    recover_expired_jobs()
    node_id = _validate_id(node_id)
    node = next((n for n in list_nodes() if n.get("node_id") == node_id), None)
    if not node or not _eligible(node, set(required_capabilities or [])):
        return None
    with _LOCK:
        jobs = []
        for p in sorted(_state_dir().glob("job-*.json")):
            item = _read(p)
            if item and item.get("node_id") == node_id and item.get("state") in {"QUEUED", "RETRYING"}:
                jobs.append((p, item))
        if not jobs:
            return None
        path, job = jobs[0]
        job["state"] = "RUNNING"
        job["leased_at"] = _now()
        job["updated_at"] = _now()
        _atomic_write(path, job)
        return job

def recover_expired_jobs(*, lease_timeout: float | None = None) -> list[str]:
    """Return abandoned RUNNING jobs to the durable queue.

    A worker crash must not permanently strand a job. Recovery is conservative:
    only RUNNING jobs with an expired lease are re-queued as RETRYING, preserving
    the previous lease evidence.
    """
    timeout = float(
        lease_timeout
        if lease_timeout is not None
        else os.getenv("BRAIN_FABRIC_JOB_LEASE_TIMEOUT", "600")
    )
    now = _now()
    recovered: list[str] = []
    with _LOCK:
        for path in sorted(_state_dir().glob("job-*.json")):
            job = _read(path)
            if not job or job.get("state") != "RUNNING":
                continue
            leased_at = float(job.get("leased_at", job.get("updated_at", 0)))
            if now - leased_at <= timeout:
                continue
            retries = int(job.get("lease_retries", 0))
            max_retries = int(os.getenv("BRAIN_FABRIC_MAX_LEASE_RETRIES", "3"))
            job["lease_retries"] = retries + 1
            job["updated_at"] = now
            job.setdefault("evidence", []).append({
                "at": now,
                "event": "LEASE_EXPIRED",
                "previous_state": "RUNNING",
                "lease_timeout": timeout,
                "lease_retry": retries + 1,
            })
            job["state"] = "FAILED" if retries + 1 > max_retries else "RETRYING"
            if job["state"] == "FAILED":
                job["evidence"].append({
                    "at": now,
                    "event": "LEASE_RETRY_LIMIT_EXCEEDED",
                    "max_retries": max_retries,
                })
            _atomic_write(path, job)
            recovered.append(str(job["job_id"]))
    return recovered


def get_job(job_id: str) -> dict[str, Any] | None:
    return _read(_state_dir() / f"job-{_validate_id(job_id)}.json")

def transition_job(job_id: str, state: str, *, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    job_id = _validate_id(job_id)
    state = state.strip().upper()
    if state not in {"QUEUED", "RUNNING", "SUCCESS", "FAILED", "CANCELLED", "RETRYING"}:
        raise ValueError("unsupported fabric job state")
    path = _state_dir() / f"job-{job_id}.json"
    with _LOCK:
        job = _read(path)
        if not job:
            raise KeyError(job_id)
        current = str(job.get("state", "")).upper()
        allowed = {
            "QUEUED": {"RUNNING", "CANCELLED"},
            "RETRYING": {"RUNNING", "CANCELLED"},
            "RUNNING": {"SUCCESS", "FAILED", "CANCELLED", "RETRYING"},
            "SUCCESS": set(),
            "FAILED": set(),
            "CANCELLED": set(),
        }
        if state != current and state not in allowed.get(current, set()):
            raise ValueError(f"invalid job transition: {current}->{state}")
        job["state"] = state
        job["updated_at"] = _now()
        if evidence:
            job.setdefault("evidence", []).append({"at": _now(), **evidence})
        _atomic_write(path, job)
    return job

def snapshot() -> dict[str, Any]:
    nodes = list_nodes()
    jobs = []
    with _LOCK:
        for p in sorted(_state_dir().glob("job-*.json")):
            item = _read(p)
            if item:
                jobs.append(item)
    return {
        "system": "BRAIN_CLOUD_FABRIC", "mode": "provider-neutral",
        "provider_lock_in": False, "persistent": True, "nodes": nodes,
        "jobs": jobs[-100:],
        "capabilities": ["node_registry", "health_heartbeat", "capacity_tracking",
                         "capability_scheduling", "durable_job_state",
                         "provider_neutral_infrastructure"],
    }
