"""Authenticated FastAPI endpoints for the persistent Arkan software executor."""
from __future__ import annotations

from threading import RLock
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .arkan_software_executor import ArkanSoftwareExecutor, WORKLOADS
from .control_auth import require_control_key

router = APIRouter(prefix="/api/arkan/software-executor", tags=["arkan-software-executor"])
_lock = RLock()
_executor: ArkanSoftwareExecutor | None = None


def _authorized(request: Request) -> None:
    require_control_key(request)


def get_executor() -> ArkanSoftwareExecutor:
    """Create one process-local service backed by the configured persistent SQLite path."""
    global _executor
    with _lock:
        if _executor is None:
            _executor = ArkanSoftwareExecutor()
        return _executor


def close_executor_for_shutdown() -> None:
    """Gracefully close the process-local worker; SQLite state remains on disk."""
    global _executor
    with _lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.close()


@router.get("/status")
def software_executor_status(request: Request) -> dict[str, Any]:
    _authorized(request)
    return get_executor().status()


@router.post("/tasks")
def submit_software_task(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    _authorized(request)
    task_type = str(body.get("task_type", "cpu_smoke"))
    if task_type not in WORKLOADS:
        raise HTTPException(status_code=422, detail={
            "code": "TASK_TYPE_NOT_ALLOWED", "allowed": sorted(WORKLOADS),
        })
    try:
        executor = get_executor()
        executor.start()
        return {"ok": True, "submission": executor.submit(
            task_type,
            task_id=body.get("task_id"),
            idempotency_key=body.get("idempotency_key"),
        )}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": str(exc)}) from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail={
            "code": "ARKAN_SOFTWARE_EXECUTOR_UNAVAILABLE", "error": str(exc)[:300],
        }) from exc


@router.get("/tasks/{task_id}")
def get_software_task(task_id: str, request: Request) -> dict[str, Any]:
    _authorized(request)
    result = get_executor().task_status(task_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result)
    return result
