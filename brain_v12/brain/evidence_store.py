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
          created_at REAL NOT NULL, verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED'
        )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id)")
        self.db.commit()

    @staticmethod
    def digest(payload):
        raw=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def append(self,task_id,kind,payload,producer="brain"):
        evidence_id="ev-"+uuid4().hex
        digest=self.digest(payload)
        self.db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?)",
          (evidence_id,task_id,kind,json.dumps(payload,ensure_ascii=False),digest,producer,time.time(),"UNVERIFIED"))
        self.db.commit()
        return self.get(evidence_id)

    def get(self,evidence_id):
        row=self.db.execute("SELECT * FROM evidence WHERE evidence_id=?",(evidence_id,)).fetchone()
        if not row:return None
        item=dict(row); item["payload"]=json.loads(item["payload"]); return item

    def for_task(self,task_id):
        rows=self.db.execute("SELECT evidence_id FROM evidence WHERE task_id=? ORDER BY created_at",(task_id,)).fetchall()
        return [self.get(r["evidence_id"]) for r in rows]

    def verify_hash(self,evidence_id):
        item=self.get(evidence_id)
        if not item:return {"ok":False,"status":"EVIDENCE_NOT_FOUND"}
        valid=self.digest(item["payload"])==item["sha256"]
        status="VERIFIED" if valid else "TAMPERED"
        self.db.execute("UPDATE evidence SET verification_status=? WHERE evidence_id=?",(status,evidence_id))
        self.db.commit()
        return {"ok":valid,"status":status,"evidence_id":evidence_id,"sha256":item["sha256"]}

    def recent_golden(self, limit=100):
        """Return recent Golden-loop evidence only; this is a read-only projection."""
        limit = max(1, min(int(limit), 200))
        rows = self.db.execute(
            "SELECT evidence_id FROM evidence WHERE kind LIKE 'golden:%' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self.get(row["evidence_id"]) for row in rows]

    def golden_count(self):
        row = self.db.execute(
            "SELECT COUNT(*) AS total FROM evidence WHERE kind LIKE 'golden:%'"
        ).fetchone()
        return int(row["total"])

    def close(self): self.db.close()
