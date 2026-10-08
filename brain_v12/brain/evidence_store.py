from __future__ import annotations
import hashlib,json,sqlite3,time
from pathlib import Path
from uuid import uuid4

class EvidenceStore:
    """Append-only evidence index; verification never trusts an executor's success alone."""
    def __init__(self,path="brain6_artifacts/evidence/evidence.db"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS evidence(
          evidence_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, kind TEXT NOT NULL,
          payload TEXT NOT NULL, sha256 TEXT NOT NULL, producer TEXT NOT NULL,
          created_at REAL NOT NULL, verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED', mission_id TEXT, attempt INTEGER, phase TEXT
        )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id)")
        for column, definition in (("mission_id", "TEXT"), ("attempt", "INTEGER"), ("phase", "TEXT")):
            try:
                self.db.execute(f"ALTER TABLE evidence ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError:
                pass
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_evidence_mission_attempt ON evidence(mission_id,attempt)")
        self.db.execute("""CREATE TABLE IF NOT EXISTS execution_idempotency(
          execution_key TEXT PRIMARY KEY, mission_fingerprint TEXT NOT NULL, action TEXT NOT NULL,
          parameters_fingerprint TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL, completed_at REAL
        )""")
        self.db.commit()

    @staticmethod
    def digest(payload):
        raw=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def append(self,task_id,kind,payload,producer="brain",*,mission_id=None,attempt=None,phase=None):
        evidence_id="ev-"+uuid4().hex
        digest=self.digest(payload)
        self.db.execute("INSERT INTO evidence(evidence_id,task_id,kind,payload,sha256,producer,created_at,verification_status,mission_id,attempt,phase) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
          (evidence_id,task_id,kind,json.dumps(payload,ensure_ascii=False),digest,producer,time.time(),"UNVERIFIED",mission_id,attempt,phase))
        self.db.commit()
        return self.get(evidence_id)

    def get(self,evidence_id):
        row=self.db.execute("SELECT * FROM evidence WHERE evidence_id=?",(evidence_id,)).fetchone()
        if not row:return None
        item=dict(row); item["payload"]=json.loads(item["payload"]); return item

    def for_task(self,task_id,*,mission_id=None,attempt=None,phase=None):
        clauses=["task_id=?"]; params=[task_id]
        if mission_id is not None: clauses.append("mission_id=?"); params.append(mission_id)
        if attempt is not None: clauses.append("attempt=?"); params.append(attempt)
        if phase is not None: clauses.append("phase=?"); params.append(phase)
        rows=self.db.execute("SELECT evidence_id FROM evidence WHERE "+" AND ".join(clauses)+" ORDER BY created_at",tuple(params)).fetchall()
        return [self.get(r["evidence_id"]) for r in rows]

    def verify_hash(self,evidence_id):
        item=self.get(evidence_id)
        if not item:return {"ok":False,"status":"EVIDENCE_NOT_FOUND"}
        valid=self.digest(item["payload"])==item["sha256"]
        status="VERIFIED" if valid else "TAMPERED"
        self.db.execute("UPDATE evidence SET verification_status=? WHERE evidence_id=?",(status,evidence_id))
        self.db.commit()
        return {"ok":valid,"status":status,"evidence_id":evidence_id,"sha256":item["sha256"]}

    def claim_execution(self,execution_key,mission_fingerprint,action,parameters_fingerprint):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("INSERT INTO execution_idempotency(execution_key,mission_fingerprint,action,parameters_fingerprint,status,created_at) VALUES(?,?,?,?,?,?)",(execution_key,mission_fingerprint,action,parameters_fingerprint,"CLAIMED",time.time()))
            self.db.commit()
            return {"ok":True,"status":"CLAIMED","execution_key":execution_key}
        except sqlite3.IntegrityError:
            self.db.rollback()
            row=self.db.execute("SELECT status FROM execution_idempotency WHERE execution_key=?",(execution_key,)).fetchone()
            return {"ok":False,"status":row["status"] if row else "UNKNOWN","execution_key":execution_key}

    def complete_execution(self,execution_key):
        self.db.execute("UPDATE execution_idempotency SET status=?,completed_at=?,lease_until=NULL WHERE execution_key=? AND status=?",("COMPLETED",time.time(),execution_key,"CLAIMED"))
        self.db.commit()
        return self.db.execute("SELECT status FROM execution_idempotency WHERE execution_key=?",(execution_key,)).fetchone()["status"]

    def execution_status(self,execution_key):
        row=self.db.execute("SELECT * FROM execution_idempotency WHERE execution_key=?",(execution_key,)).fetchone()
        return dict(row) if row else None

    def close(self): self.db.close()


    def renew_execution(self,execution_key,lease_seconds=300):
        now=time.time()
        self.db.execute("UPDATE execution_idempotency SET lease_until=? WHERE execution_key=? AND status=?", (now+lease_seconds,execution_key,"CLAIMED"))
        self.db.commit()
        return self.execution_status(execution_key)

    def recoverable_executions(self):
        now=time.time()
        rows=self.db.execute("SELECT * FROM execution_idempotency WHERE status=? AND lease_until IS NOT NULL AND lease_until<? ORDER BY created_at",("CLAIMED",now)).fetchall()
        return [dict(r) for r in rows]
