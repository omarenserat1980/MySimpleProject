from __future__ import annotations
import json, os, sqlite3, threading, time
from pathlib import Path
from uuid import uuid4

class DurableTaskStore:
    """Transactional task state: immutable spec, separate result, leases and attempts."""
    def __init__(self,path=None):
        if path is None:
            runtime_path = os.getenv("BRAIN_VIRTUAL_TASK_DB")
            runtime_home = os.getenv("BRAIN_RUNTIME_HOME")
            path = runtime_path or ((Path(runtime_home).expanduser() / "brain6_artifacts" / "virtual_tasks" / "tasks.db") if runtime_home else "brain6_artifacts/virtual_tasks/tasks.db")
        self.path=Path(path).expanduser(); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.db=sqlite3.connect(self.path,check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        with self.lock:
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks(
              task_id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL,
              blade_id TEXT, lease_id TEXT, lease_expires_at REAL,
              created_at REAL NOT NULL, updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_lease ON tasks(lease_expires_at);
            """)
            cols={r["name"] for r in self.db.execute("PRAGMA table_info(tasks)").fetchall()}
            if "result_json" not in cols: self.db.execute("ALTER TABLE tasks ADD COLUMN result_json TEXT")
            if "attempt" not in cols: self.db.execute("ALTER TABLE tasks ADD COLUMN attempt INTEGER NOT NULL DEFAULT 0")
            if "idempotency_key" not in cols: self.db.execute("ALTER TABLE tasks ADD COLUMN idempotency_key TEXT")
            if "error_json" not in cols: self.db.execute("ALTER TABLE tasks ADD COLUMN error_json TEXT")
            self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_idempotency ON tasks(idempotency_key) WHERE idempotency_key IS NOT NULL")
            self.db.commit()

    def submit(self,task_id,payload,idempotency_key=None):
        now=time.time()
        with self.lock:
            row=self.db.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if row: return dict(row)
            if idempotency_key:
                row=self.db.execute("SELECT * FROM tasks WHERE idempotency_key=?",(idempotency_key,)).fetchone()
                if row: return dict(row)
            self.db.execute("INSERT INTO tasks(task_id,payload,status,created_at,updated_at,idempotency_key,attempt) VALUES(?,?,?,?,?,?,0)",
                (task_id,json.dumps(payload,ensure_ascii=False),"QUEUED",now,now,idempotency_key))
            self.db.commit(); return self.get(task_id)

    def get(self,task_id):
        with self.lock:
            row=self.db.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            return dict(row) if row else None

    def list_active(self):
        with self.lock:
            rows=self.db.execute("SELECT * FROM tasks WHERE status IN ('QUEUED','WAITING','RUNNING') ORDER BY created_at").fetchall()
            return [dict(r) for r in rows]

    def claim(self,task_id,blade_id,lease_seconds=300):
        now=time.time(); lease=now+max(1,int(lease_seconds)); lease_id=uuid4().hex
        with self.lock:
            cur=self.db.execute("""UPDATE tasks SET status='RUNNING',blade_id=?,lease_id=?,lease_expires_at=?,updated_at=?,attempt=attempt+1
              WHERE task_id=? AND status IN ('QUEUED','WAITING')""",(blade_id,lease_id,lease,now,task_id))
            self.db.commit()
            return self.get(task_id) if cur.rowcount else None

    def heartbeat(self,task_id,lease_id,lease_seconds=300):
        now=time.time(); lease=now+max(5,int(lease_seconds))
        with self.lock:
            cur=self.db.execute("UPDATE tasks SET lease_expires_at=?,updated_at=? WHERE task_id=? AND status='RUNNING' AND lease_id=?",
                (lease,now,task_id,lease_id))
            self.db.commit(); return cur.rowcount==1

    def finish(self,task_id,ok,result):
        status="COMPLETED" if ok else "FAILED"; now=time.time()
        with self.lock:
            row=self.db.execute("SELECT lease_id FROM tasks WHERE task_id=? AND status='RUNNING'",(task_id,)).fetchone()
            if not row: return self.get(task_id)
            error=None if ok else json.dumps(result,ensure_ascii=False)
            self.db.execute("""UPDATE tasks SET status=?,result_json=?,error_json=?,lease_id=NULL,lease_expires_at=NULL,updated_at=?
              WHERE task_id=? AND status='RUNNING'""",(status,json.dumps(result,ensure_ascii=False),error,now,task_id))
            self.db.commit(); return self.get(task_id)

    def requeue(self,task_id):
        now=time.time()
        with self.lock:
            cur=self.db.execute("UPDATE tasks SET status='QUEUED',blade_id=NULL,lease_id=NULL,lease_expires_at=NULL,updated_at=? WHERE task_id=? AND status='RUNNING'",(now,task_id))
            self.db.commit(); return cur.rowcount==1

    def recover_expired(self):
        now=time.time()
        with self.lock:
            rows=self.db.execute("SELECT task_id FROM tasks WHERE status='RUNNING' AND lease_expires_at<?",(now,)).fetchall()
            ids=[r["task_id"] for r in rows]
            self.db.execute("""UPDATE tasks SET status='QUEUED',blade_id=NULL,lease_id=NULL,lease_expires_at=NULL,updated_at=?
              WHERE status='RUNNING' AND lease_expires_at<?""",(now,now))
            self.db.commit(); return ids

    def counts(self):
        with self.lock:
            rows=self.db.execute("SELECT status,COUNT(*) n FROM tasks GROUP BY status").fetchall()
            return {r["status"]:r["n"] for r in rows}

    def close(self):
        with self.lock: self.db.close()
