from __future__ import annotations
import hashlib,json
from .evidence_store import EvidenceStore

class VerificationEngine:
    """Independent verifier. Renderer/executor cannot mark a task VERIFIED."""
    def __init__(self,evidence_store=None):
        self.evidence=evidence_store or EvidenceStore()

    def verify_execution(self,task):
        if task is None:return {"ok":False,"status":"TASK_NOT_FOUND","reasons":["missing_task"]}
        if task.status!="COMPLETED":return {"ok":False,"status":"NOT_COMPLETED","reasons":[f"status={task.status}"]}
        result=task.result or {}
        if result.get("ok") is False:return {"ok":False,"status":"EXECUTION_RESULT_FAILED","reasons":["executor_reported_failure"]}
        payload={"task_id":task.task_id,"status":task.status,"attempt":task.attempt,"result":result}
        ev=self.evidence.append(task.task_id,"execution",payload,"verification-engine")
        check=self.evidence.verify_hash(ev["evidence_id"])
        if not check["ok"]:return {"ok":False,"status":"EVIDENCE_TAMPERED","evidence_id":ev["evidence_id"]}
        return {"ok":True,"status":"VERIFIED","task_id":task.task_id,"evidence_id":ev["evidence_id"],"evidence_sha256":ev["sha256"]}

    def verify_payload_hash(self,payload,expected_sha256):
        actual=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
        return {"ok":actual==expected_sha256,"status":"VERIFIED" if actual==expected_sha256 else "HASH_MISMATCH","sha256":actual}
