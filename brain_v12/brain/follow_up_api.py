"""Authenticated API for the persistent Electronic Brain follow-up ledger."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from html import escape

from .control_auth import require_control_key
from .follow_up_store import FollowUpStore

router = APIRouter(prefix="/api/follow-up", tags=["Brain Follow-up"])
store = FollowUpStore()


@router.get("/dashboard", response_class=HTMLResponse)
def follow_up_dashboard():
    """Render a read-only HTML view from the SQLite ledger; refresh every minute."""
    summary = store.summary()
    tasks = store.list_tasks()
    metrics = [
        ("All tasks", summary["total_tasks"]),
        ("In progress", summary["active_tasks"]),
        ("Blocked", summary["blocked_tasks"]),
        ("Passed", summary["counts"].get("PASS", 0)),
        ("Not proven", summary["counts"].get("NOT_PROVEN", 0)),
    ]
    metric_html = "".join(
        '<article class="metric"><strong>' + str(value) + '</strong><span>' + escape(label) + '</span></article>'
        for label, value in metrics
    )
    cards = []
    for task in tasks:
        evidence = []
        for url in task.get("evidence", []):
            safe_url = escape(url, quote=True)
            if url.startswith("https://"):
                evidence.append('<li><a rel="noopener noreferrer" target="_blank" href="' + safe_url + '">' + escape(url) + '</a></li>')
            else:
                evidence.append('<li>' + escape(url) + '</li>')
        cards.append(
            '<article class="task"><div class="head"><h2>' + escape(task["task_id"] + " · " + task["title"]) +
            '</h2><span class="status">' + escape(task["status"]) + '</span></div><p>' +
            escape(task["detail"]) + '</p><p><b>Next:</b> ' + escape(task["next_action"]) +
            '</p>' + ('<details><summary>Evidence</summary><ul>' + "".join(evidence) + '</ul></details>' if evidence else '') +
            '</article>'
        )
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="60">
<title>Electronic Brain — Follow-up</title><style>
body{font:16px/1.5 system-ui,sans-serif;background:#10151d;color:#eef3f8;margin:0}
main{max-width:950px;margin:auto;padding:24px 16px}header,.head{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.muted{color:#aab8c8}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:20px 0}
.metric,.task{background:#1a2330;border:1px solid #344355;border-radius:12px;padding:14px}.metric strong{display:block;font-size:1.5rem}
.task{margin:10px 0}.task h2{font-size:1.05rem;margin:0}.status{border:1px solid #52657a;border-radius:99px;padding:3px 9px;font-size:.8rem}
a{color:#83c5ff;overflow-wrap:anywhere}button{background:#1a2330;color:#eef3f8;border:1px solid #52657a;border-radius:9px;padding:9px 13px;font:inherit}
</style></head><body><main><header><div><h1>Electronic Brain — Follow-up</h1>
<p class="muted">Persistent SQLite task ledger · auto-refreshes every 60 seconds</p></div>
<button onclick="location.reload()">Refresh now</button></header>
<div class="metrics">""" + metric_html + """</div><section>""" + "".join(cards) + """</section>
<p class="muted">PASS applies only to the recorded task criteria. Prototype tests do not prove real-device execution, mining, or revenue.</p>
</main></body></html>"""
    return HTMLResponse(page)


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
