from uuid import uuid4
class TaskEngine:
    def __init__(self): self.tasks={}
    def create(self,title,parent_id=None,depends_on=None):
        tid=str(uuid4()); self.tasks[tid]={"id":tid,"title":title,"parent_id":parent_id,"depends_on":depends_on or [],"status":"PENDING","attempts":0}; return self.tasks[tid]
    def ready(self):
        done={k for k,v in self.tasks.items() if v["status"]=="COMPLETED"}
        return [v for v in self.tasks.values() if v["status"]=="PENDING" and all(d in done for d in v["depends_on"])]
    def fail(self,task_id,error="TASK_FAILED",evidence_ref=None):
        if task_id not in self.tasks: return {"ok":False,"error":"TASK_NOT_FOUND"}
        self.tasks[task_id]["status"]="FAILED"
        self.tasks[task_id]["error"]=error
        if evidence_ref:
            self.tasks[task_id]["evidence_ref"]=evidence_ref
        return self.tasks[task_id]

    def retry(self,task_id,max_attempts=3):
        if task_id not in self.tasks: return {"ok":False,"error":"TASK_NOT_FOUND"}
        task=self.tasks[task_id]
        if task["status"] != "FAILED": return {"ok":False,"error":"TASK_NOT_FAILED"}
        if task["attempts"] >= max(1,int(max_attempts)):
            return {"ok":False,"error":"RETRY_LIMIT_REACHED","task":task}
        task["status"]="PENDING"
        task["error"]=""
        task["retry_of"] = task.get("retry_of") or task["id"]
        task["retry_count"] = int(task.get("retry_count", 0)) + 1
        return {"ok":True,"task":task}

    def update(self,task_id,status,evidence_ref=None):
        if task_id not in self.tasks: return {"ok":False,"error":"TASK_NOT_FOUND"}
        if status=="COMPLETED" and not evidence_ref:
            return {"ok":False,"error":"EVIDENCE_REQUIRED"}
        self.tasks[task_id]["status"]=status
        if status=="RUNNING": self.tasks[task_id]["attempts"]+=1
        if evidence_ref:
            self.tasks[task_id]["evidence_ref"]=evidence_ref
        return self.tasks[task_id]
    def complete(self,task_id,evidence_ref=None):
        """Evidence-gated terminal completion."""
        return self.update(task_id, "COMPLETED", evidence_ref)

    def verify_and_complete(self,task_id,verification, evidence_ref=None):
        """Complete only when an external verification result explicitly passes."""
        if not verification:
            return {"ok":False,"error":"VERIFICATION_FAILED"}
        return self.complete(task_id, evidence_ref)

    def run_with_alternatives(self, task_id, solution_engine, problem, executors, verifier):
        """Run a verified fallback chain and reflect its lifecycle on this task."""
        if task_id not in self.tasks: return {"ok":False,"error":"TASK_NOT_FOUND"}
        task = self.tasks[task_id]
        if task["status"] not in {"PENDING", "FAILED"}:
            return {"ok":False,"error":"TASK_NOT_RUNNABLE"}
        self.update(task_id, "RUNNING")
        try:
            result = solution_engine.solve(problem, executors, verifier)
            if not isinstance(result, dict):
                raise TypeError("solution engine must return a mapping")
        except Exception as exc:
            error = f"SOLUTION_ENGINE_ERROR:{type(exc).__name__}"
            self.fail(task_id, error)
            return {"ok":False,"error":error,"task":task}
        task["solution_run"] = result
        if result.get("ok") is True and result.get("status") == "VERIFIED":
            evidence_ref = result.get("evidence_ref")
            if evidence_ref:
                return self.verify_and_complete(task_id, True, evidence_ref)
            self.fail(task_id, "VERIFICATION_EVIDENCE_REQUIRED")
            return {"ok":False,"error":"VERIFICATION_EVIDENCE_REQUIRED","task":task,
                    "solution_run":result}
        self.fail(task_id, "NO_ALTERNATIVE_VERIFIED", result.get("evidence_ref"))
        return {"ok":False,"error":"NO_ALTERNATIVE_VERIFIED","task":task,
                "solution_run":result}

    def snapshot(self):
        return {"tasks":list(self.tasks.values()),"ready":self.ready()}
