"""Bounded, read-only local probes for the Universal Heartbeat Factory.

These probes do not call remote providers, enqueue device work, launch workers,
or imply that a local record was sent to or acknowledged by a remote receiver.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable

from .heartbeat_factory import FunctionDefinition, HeartbeatFactory

Probe = Callable[[dict[str, Any]], dict[str, Any]]

CORE_PROBE_SPECS = (
    ("brain.python_runtime", "Python runtime", "core", "sys.version_info"),
    ("brain.memory_store", "Memory store read", "core", "MemoryStore.state"),
    ("brain.cognitive_loop", "Cognitive loop shape", "core", "CognitiveLoop.STAGES"),
    ("brain.sync_queue", "Sync queue counts", "sync", "DurableSyncQueue.counts"),
    ("brain.sync_store", "Sync store digest", "sync", "BrainSyncStore.snapshot"),
    ("brain.worker_registry", "Software worker registry", "workers", "WorkerRegistry.snapshot"),
    ("brain.self_monitor", "Brain self monitor", "monitoring", "BrainSelfMonitor.snapshot"),
    ("brain.evidence_store", "Evidence store connectivity", "evidence", "EvidenceStore SQLite connection"),
    ("brain.device_bridge", "Optional device bridge status", "workers", "DeviceBridge.status"),
    ("brain.api_routes", "API route map", "api", "FastAPI app.routes"),
)


def core_probe_definitions() -> list[FunctionDefinition]:
    """Return ten concrete local probe definitions; no network probes are included."""
    return [
        FunctionDefinition(
            function_id=function_id,
            name=name,
            category=category,
            owner="brain-v12",
            implementation="local_read_only_probe",
            interval_seconds=60,
            timeout_seconds=5,
            max_concurrency=1,
            auth_required=True,
            enabled=True,
            source_of_truth=source,
            resource_limit="one local call; no network",
            retry_limit=0,
        )
        for function_id, name, category, source in CORE_PROBE_SPECS
    ]


def register_core_probes(factory: HeartbeatFactory, *, now: float | None = None) -> list[dict[str, Any]]:
    """Idempotently register the ten implemented local probes."""
    return [factory.register_function(item, now=now) for item in core_probe_definitions()]


def _result(ok: bool | None, status: str, **details: Any) -> dict[str, Any]:
    return {"ok": ok, "status": status, **details}


def _probe_python(_ctx: dict[str, Any]) -> dict[str, Any]:
    return _result(True, "PASS", python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def _probe_memory(ctx: dict[str, Any]) -> dict[str, Any]:
    state = ctx["store"].state()
    ok = isinstance(state, dict)
    return _result(ok, "PASS" if ok else "FAIL", response_type=type(state).__name__)


def _probe_cognitive(ctx: dict[str, Any]) -> dict[str, Any]:
    stages = getattr(ctx["cognitive"], "STAGES", None)
    ok = isinstance(stages, (list, tuple)) and len(stages) > 0
    return _result(ok, "PASS" if ok else "FAIL", stage_count=len(stages) if isinstance(stages, (list, tuple)) else 0)


def _probe_sync_queue(ctx: dict[str, Any]) -> dict[str, Any]:
    counts = ctx["sync_queue"].counts()
    ok = isinstance(counts, dict) and all(isinstance(v, int) and v >= 0 for v in counts.values())
    return _result(ok, "PASS" if ok else "FAIL", counts=counts if isinstance(counts, dict) else {})


def _probe_sync_store(ctx: dict[str, Any]) -> dict[str, Any]:
    snapshot = ctx["sync_store"].snapshot()
    digest = snapshot.get("digest") if isinstance(snapshot, dict) else None
    ok = isinstance(digest, str) and len(digest) == 64
    return _result(ok, "PASS" if ok else "FAIL", digest_present=bool(digest), audit_chain_valid=snapshot.get("audit_chain_valid") if isinstance(snapshot, dict) else None)


def _probe_worker_registry(ctx: dict[str, Any]) -> dict[str, Any]:
    snapshot = ctx["worker_registry"].snapshot()
    if not isinstance(snapshot, dict):
        return _result(False, "FAIL", response_type=type(snapshot).__name__)
    workers = snapshot.get("workers", [])
    online = sum(1 for worker in workers if worker.get("online")) if isinstance(workers, list) else 0
    return _result(snapshot.get("ok") is True, "PASS" if snapshot.get("ok") is True else "FAIL",
                   mode=snapshot.get("mode", "UNKNOWN"), worker_count=len(workers) if isinstance(workers, list) else 0,
                   online_workers=online, device_adapters_enabled=bool(snapshot.get("device_adapters_enabled", False)))


def _probe_self_monitor(ctx: dict[str, Any]) -> dict[str, Any]:
    snapshot = ctx["self_monitor"].snapshot()
    ok = isinstance(snapshot, dict) and snapshot.get("ok") is True
    checks = snapshot.get("checks", []) if isinstance(snapshot, dict) else []
    return _result(ok, "PASS" if ok else "FAIL", monitor_status=snapshot.get("status", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
                   check_count=len(checks) if isinstance(checks, list) else 0,
                   failed_checks=[str(item.get("name", "unknown")) for item in checks if isinstance(item, dict) and not item.get("ok")] if isinstance(checks, list) else [])


def _probe_evidence_store(ctx: dict[str, Any]) -> dict[str, Any]:
    store = ctx["evidence_store"]
    row = store.db.execute("SELECT 1 AS ready").fetchone()
    ok = bool(row and row["ready"] == 1)
    return _result(ok, "PASS" if ok else "FAIL", sqlite_query_ok=ok)


def _probe_device_bridge(ctx: dict[str, Any]) -> dict[str, Any]:
    snapshot = ctx["device_bridge"].status()
    if not isinstance(snapshot, dict):
        return _result(False, "FAIL", response_type=type(snapshot).__name__)
    configured = bool(snapshot.get("configured"))
    agents = snapshot.get("agents", {})
    online = bool(agents.get("online")) if isinstance(agents, dict) else False
    # An optional disconnected/unconfigured agent is unknown, not a Brain failure.
    status = "PASS" if configured else "UNKNOWN"
    return _result(True if configured else None, status, configured=configured, agents_online=online,
                   queued=int(snapshot.get("queued", 0) or 0), pending=int(snapshot.get("pending", 0) or 0))


def _probe_api_routes(ctx: dict[str, Any]) -> dict[str, Any]:
    routes = {str(getattr(route, "path", "")) for route in ctx["app"].routes}
    required = {"/api/system/readiness", "/api/heartbeats/summary", "/api/heartbeats/diagnostic"}
    missing = sorted(required - routes)
    return _result(not missing, "PASS" if not missing else "FAIL", required_routes=sorted(required), missing_routes=missing)


_PROBES: dict[str, Probe] = {
    "brain.python_runtime": _probe_python,
    "brain.memory_store": _probe_memory,
    "brain.cognitive_loop": _probe_cognitive,
    "brain.sync_queue": _probe_sync_queue,
    "brain.sync_store": _probe_sync_store,
    "brain.worker_registry": _probe_worker_registry,
    "brain.self_monitor": _probe_self_monitor,
    "brain.evidence_store": _probe_evidence_store,
    "brain.device_bridge": _probe_device_bridge,
    "brain.api_routes": _probe_api_routes,
}


def run_local_probe(factory: HeartbeatFactory, function_id: str, context: dict[str, Any], *,
                    worker_id: str = "brain-process", node_id: str | None = None,
                    now: float | None = None, authorization_ref: str | None = None) -> dict[str, Any]:
    """Execute one bounded local probe and store its result as CREATED local evidence.

    CREATED is deliberately retained as the delivery state. This local execution
    does not pretend that a remote receiver acknowledged the record.
    """
    if function_id not in _PROBES:
        raise KeyError("LOCAL_PROBE_NOT_IMPLEMENTED")
    definition = factory.get_function(function_id)
    if definition is None:
        raise KeyError("FUNCTION_NOT_REGISTERED")
    if not definition["enabled"]:
        raise RuntimeError("FUNCTION_DISABLED")
    started = time.monotonic()
    try:
        result = _PROBES[function_id](context)
        if not isinstance(result, dict) or result.get("status") not in {"PASS", "FAIL", "UNKNOWN"}:
            result = _result(None, "UNKNOWN", error_code="PROBE_RESULT_INVALID")
    except Exception as exc:
        # Keep error text and local paths out of durable heartbeat payloads.
        result = _result(False, "FAIL", error_code=f"PROBE_{type(exc).__name__.upper()[:48]}")
    latency_ms = round((time.monotonic() - started) * 1000, 3)
    instant = time.time() if now is None else float(now)
    heartbeat = factory.create_heartbeat(
        function_id,
        worker_id=worker_id,
        node_id=node_id or os.getenv("BRAIN_NODE_ID", "brain-local"),
        mode="local",
        source="local_read_only_probe",
        payload={"probe_result": result, "latency_ms": latency_ms},
        now=instant,
        authorization_ref=authorization_ref,
    )
    return {
        "function_id": function_id,
        "probe_status": result["status"],
        "ok": result.get("ok"),
        "latency_ms": latency_ms,
        "heartbeat_id": heartbeat["heartbeat_id"],
        "delivery_status": heartbeat["status"],
        "remote_delivery_proven": False,
        "result": result,
    }


def run_core_probes(factory: HeartbeatFactory, context: dict[str, Any], *,
                    function_ids: list[str] | None = None, now: float | None = None,
                    authorization_ref: str | None = None) -> dict[str, Any]:
    """Run selected local probes sequentially; never starts a background loop."""
    selected = function_ids if function_ids is not None else [item[0] for item in CORE_PROBE_SPECS]
    if len(selected) > len(CORE_PROBE_SPECS):
        raise ValueError("LOCAL_PROBE_BATCH_LIMIT_EXCEEDED")
    results = [run_local_probe(factory, function_id, context, now=now,
                               authorization_ref=authorization_ref) for function_id in selected]
    passed = sum(item["probe_status"] == "PASS" for item in results)
    failed = sum(item["probe_status"] == "FAIL" for item in results)
    unknown = sum(item["probe_status"] == "UNKNOWN" for item in results)
    return {
        "mode": "local_read_only_diagnostic",
        "count": len(results),
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "results": results,
        "scheduler_running": False,
        "remote_delivery_proven": False,
    }
