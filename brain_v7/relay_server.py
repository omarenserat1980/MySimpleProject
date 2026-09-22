"""V11 Brain Relay server.

A small HTTPS-facing queue between an external controller and the Android
brain. The Android side polls outbound; this server never connects inward to
the phone.

Set:
  RELAY_TOKEN=<long-random-secret>
  RELAY_DB=relay.db

Run behind HTTPS in production.
"""
from __future__ import annotations
import os, sqlite3, uuid
from datetime import datetime, timezone
from contextlib import closing
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB = os.getenv("RELAY_DB", "relay.db")
TOKEN = os.getenv("RELAY_TOKEN", "")

app = FastAPI(title="Electronic Brain V11 Relay", version="11.0")

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init():
    with closing(db()) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS tasks(
          id TEXT PRIMARY KEY, brain_id TEXT, objective TEXT NOT NULL,
          timeout INTEGER NOT NULL DEFAULT 30,
          max_steps INTEGER NOT NULL DEFAULT 12,
          status TEXT NOT NULL DEFAULT 'QUEUED',
          result TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        con.commit()

init()

def auth(authorization: str | None):
    if not TOKEN or authorization != f"Bearer {TOKEN}":
        raise HTTPException(401, "RELAY_AUTH_REQUIRED")

class TaskIn(BaseModel):
    brain_id: str = ""
    objective: str
    timeout: int = Field(default=30, ge=1, le=60)
    max_steps: int = Field(default=12, ge=1, le=12)

class ResultIn(BaseModel):
    brain_id: str
    result: dict

@app.get("/health")
def health():
    return {"ok": True, "service": "Electronic Brain V11 Relay"}

@app.post("/v1/tasks")
def create_task(body: TaskIn, authorization: str | None = Header(default=None)):
    auth(authorization)
    task_id = uuid.uuid4().hex
    with closing(db()) as con:
        t = now()
        con.execute(
            "INSERT INTO tasks(id,brain_id,objective,timeout,max_steps,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (task_id, body.brain_id, body.objective.strip(), body.timeout,
             body.max_steps, "QUEUED", t, t),
        )
        con.commit()
    return {"ok": True, "task_id": task_id, "status": "QUEUED"}

@app.get("/v1/tasks/next")
def next_task(
    brain_id: str,
    authorization: str | None = Header(default=None),
):
    auth(authorization)
    with closing(db()) as con:
        row = con.execute(
            "SELECT * FROM tasks WHERE status='QUEUED' AND (brain_id='' OR brain_id=?) ORDER BY created_at LIMIT 1",
            (brain_id,),
        ).fetchone()
        if not row:
            return {"ok": True, "task": None}
        t = now()
        con.execute(
            "UPDATE tasks SET status='RUNNING',brain_id=?,updated_at=? WHERE id=?",
            (brain_id, t, row["id"]),
        )
        con.commit()
        item = dict(row)
        item["status"] = "RUNNING"
        item.pop("result", None)
        return {"ok": True, "task": item}

@app.post("/v1/tasks/{task_id}/result")
def task_result(
    task_id: str,
    body: ResultIn,
    authorization: str | None = Header(default=None),
):
    auth(authorization)
    with closing(db()) as con:
        row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "TASK_NOT_FOUND")
        import json
        con.execute(
            "UPDATE tasks SET status=?,result=?,updated_at=? WHERE id=?",
            ("COMPLETED" if body.result.get("status") == "COMPLETED" else "FAILED",
             json.dumps(body.result, ensure_ascii=False), now(), task_id),
        )
        con.commit()
    return {"ok": True, "task_id": task_id}

@app.get("/v1/tasks/{task_id}")
def get_task(task_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    with closing(db()) as con:
        row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "TASK_NOT_FOUND")
        item = dict(row)
        if item.get("result"):
            import json
            item["result"] = json.loads(item["result"])
        return {"ok": True, "task": item}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
