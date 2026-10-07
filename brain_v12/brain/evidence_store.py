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

    def close(self): self.db.close()
