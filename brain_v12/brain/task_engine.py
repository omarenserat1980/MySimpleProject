from uuid import uuid4
class TaskEngine:
    def __init__(self): self.tasks={}
    def create(self,title,parent_id=None,depends_on=None):
        tid=str(uuid4()); self.tasks[tid]={"id":tid,"title":title,"parent_id":parent_id,"depends_on":depends_on or [],"status":"PENDING","attempts":0}; return self.tasks[tid]
    def ready(self):
        done={k for k,v in self.tasks.items() if v["status"]=="COMPLETED"}
        return [v for v in self.tasks.values() if v["status"]=="PENDING" and all(d in done for d in v["depends_on"])]
    def fail(self,task_id,error="TASK_FAILED"):
        if task_id not in self.tasks: return {"ok":False,"error":"TASK_NOT_FOUND"}
        self.tasks[task_id]["status"]="FAILED"
        self.tasks[task_id]["error"]=error
        return self.tasks[task_id]

    def retry(self,task_id,max_attempts=3):
        if task_id not in self.tasks: return {"ok":False,"error":"TASK_NOT_FOUND"}
        task=self.tasks[task_id]
        if task["status"] != "FAILED": return {"ok":False,"error":"TASK_NOT_FAILED"}
        if task["attempts"] >= max(1,int(max_attempts)):
            return {"ok":False,"error":"RETRY_LIMIT_REACHED","task":task}
        task["status"]="PENDING"
        task["error"]=""
        return {"ok":True,"task":task}

    def update(self,task_id,status):
        if task_id not in self.tasks: return {"ok":False,"error":"TASK_NOT_FOUND"}
        self.tasks[task_id]["status"]=status
        if status=="RUNNING": self.tasks[task_id]["attempts"]+=1
        return self.tasks[task_id]
    def snapshot(self): return {"tasks":list(self.tasks.values()),"ready":self.ready()}
