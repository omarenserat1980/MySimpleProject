from __future__ import annotations
import json, sqlite3, threading, time
from pathlib import Path

class DurableTaskStore:
    """SQLite-backed task state with atomic claims and restart recovery."""
    def __init__(self, path="brain6_artifacts/virtual_tasks/tasks.db"):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.db=sqlite3.connect(self.path,check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        with self.lock:
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks(
              task_id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              status TEXT NOT NULL,
              blade_id TEXT,
              lease_id TEXT,
              lease_expires_at REAL,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_lease ON tasks(lease_expires_at);
            """)
            self.db.commit()

    def submit(self,task_id,payload):
        now=time.time()
        with self.lock:
            row=self.db.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if row: return dict(row)
            self.db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)",
                (task_id,json.dumps(payload,ensure_ascii=False), "QUEUED",None,None,None,now,now))
            self.db.commit()
            return self.get(task_id)

    def get(self,task_id):
        with self.lock:
            row=self.db.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            return dict(row) if row else None

    def claim(self,task_id,blade_id,lease_seconds=300):
        now=time.time(); lease=now+max(5,int(lease_seconds))
        with self.lock:
            cur=self.db.execute("""
              UPDATE tasks SET status='RUNNING',blade_id=?,lease_id=?,lease_expires_at=?,updated_at=?
              WHERE task_id=? AND status IN ('QUEUED','WAITING')
            """,(blade_id,__import__('uuid').uuid4().hex,lease,now,task_id))
            self.db.commit()
            return self.get(task_id) if cur.rowcount else None

    def heartbeat(self,task_id,lease_id,lease_seconds=300):
        now=time.time(); lease=now+max(5,int(lease_seconds))
        with self.lock:
            cur=self.db.execute("""UPDATE tasks SET lease_expires_at=?,updated_at=?
              WHERE task_id=? AND status='RUNNING' AND lease_id=?""",(lease,now,task_id,lease_id))
            self.db.commit()
            return cur.rowcount==1

    def finish(self,task_id,ok,result):
        status="COMPLETED" if ok else "FAILED"; now=time.time()
        with self.lock:
            self.db.execute("""UPDATE tasks SET status=?,payload=?,lease_id=NULL,lease_expires_at=NULL,updated_at=?
              WHERE task_id=? AND status='RUNNING'""",
              (status,json.dumps(result,ensure_ascii=False),now,task_id))
            self.db.commit()
            return self.get(task_id)

    def recover_expired(self):
        now=time.time()
        with self.lock:
            cur=self.db.execute("""UPDATE tasks SET status='QUEUED',blade_id=NULL,lease_id=NULL,
              lease_expires_at=NULL,updated_at=? WHERE status='RUNNING' AND lease_expires_at<?""",(now,now))
            self.db.commit()
            return cur.rowcount

    def counts(self):
        with self.lock:
            rows=self.db.execute("SELECT status,COUNT(*) n FROM tasks GROUP BY status").fetchall()
            return {r["status"]:r["n"] for r in rows}

    def close(self):
        with self.lock: self.db.close()
