"""Authenticated API for the persistent Electronic Brain follow-up ledger."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .control_auth import require_control_key
from .follow_up_store import FollowUpStore

router = APIRouter(prefix="/api/follow-up", tags=["Brain Follow-up"])
store = FollowUpStore()


@router.get("/status")
def follow_up_status():
    """Return persistent counts and the database path, without exposing secrets."""
    return store.summary()


@router.get("/tasks")
def follow_up_tasks():
    """List tasks in active/blocked-first order."""
    return {"ok": True, "tasks": store.list_tasks()}


@router.get("/tasks/{task_id}/history")
def follow_up_history(task_id: str, limit: int = 50):
    if store.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")
    return {"ok": True, "task_id": task_id, "events": store.history(task_id, limit)}


@router.patch("/tasks/{task_id}")
def update_follow_up_task(task_id: str, body: dict, request: Request):
    """Mutations require the existing Brain control-plane key."""
    require_control_key(request)
    status = str(body.get("status", "")).strip().upper()
    note = str(body.get("note", "")).strip()
    evidence = body.get("evidence")
    if evidence is not None and (
        not isinstance(evidence, list)
        or any(not isinstance(item, str) for item in evidence)
    ):
        raise HTTPException(status_code=422, detail="EVIDENCE_MUST_BE_STRING_LIST")
    next_action = body.get("next_action")
    if next_action is not None and not isinstance(next_action, str):
        raise HTTPException(status_code=422, detail="NEXT_ACTION_MUST_BE_STRING")
    try:
        task = store.update_task(
            task_id,
            status=status,
            note=note,
            evidence=evidence,
            next_action=next_action,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "task": task}
