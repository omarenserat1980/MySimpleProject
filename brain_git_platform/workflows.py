from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import sqlite3
from .service import ROOT, BrainGitError

DB=ROOT/"brain-git.db"

@dataclass(frozen=True)
class WorkflowRun:
    id:int
    namespace:str
    repository:str
    workflow:str
    ref:str
    status:str
    created_at:str

def _init():
    with sqlite3.connect(DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS workflow_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, namespace TEXT, repository TEXT,
          workflow TEXT, ref TEXT, status TEXT, created_at TEXT, completed_at TEXT)""")
        db.commit()

def dispatch(namespace:str, repository:str, workflow:str, ref:str="main")->WorkflowRun:
    _init()
    now=datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB) as db:
        cur=db.execute("""INSERT INTO workflow_runs(namespace,repository,workflow,ref,status,created_at)
                          VALUES(?,?,?,?,?,?)""",
                       (namespace,repository,workflow,ref,"queued",now))
        db.commit()
        return WorkflowRun(cur.lastrowid,namespace,repository,workflow,ref,"queued",now)

def set_status(run_id:int,status:str)->None:
    if status not in {"queued","running","success","failed","cancelled"}:
        raise BrainGitError("invalid workflow status")
    _init()
    with sqlite3.connect(DB) as db:
        cur=db.execute("UPDATE workflow_runs SET status=?, completed_at=? WHERE id=?",
                       (status, datetime.now(timezone.utc).isoformat() if status in {"success","failed","cancelled"} else None, run_id))
        if cur.rowcount!=1: raise BrainGitError("workflow run not found")
        db.commit()

def get_run(run_id:int)->dict:
    _init()
    with sqlite3.connect(DB) as db:
        row=db.execute("SELECT id,namespace,repository,workflow,ref,status,created_at FROM workflow_runs WHERE id=?",(run_id,)).fetchone()
    if not row: raise BrainGitError("workflow run not found")
    return asdict(WorkflowRun(*row))
