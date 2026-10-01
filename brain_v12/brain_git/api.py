"""Brain-native HTTP API for Git repositories."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .service import BrainGitError, BrainGitService
import time

class RepoIn(BaseModel):
    name:str
    private:bool=True

class CommitIn(BaseModel):
    files:dict[str,str]
    message:str
    branch:str="main"

class BranchIn(BaseModel):
    branch:str
    from_ref:str=""

class WorkflowIn(BaseModel):
    name:str="brain-cinema"
    command:list[str]=[]
    metadata:dict={}


def router(service:BrainGitService|None=None):
    svc=service or BrainGitService()
    r=APIRouter(prefix="/api/brain-git",tags=["Brain Git"])
    @r.get("/status")
    def status():
        return {"ok":True,"authority":"BRAIN_GIT_PRIMARY","github_dependency":False,"repositories":len(svc.list_repositories())}
    @r.get("/repositories")
    def repositories(): return {"ok":True,"repositories":svc.list_repositories()}
    @r.post("/repositories")
    def create(body:RepoIn):
        try:return {"ok":True,"repository":svc.create_repository(body.name,body.private)}
        except BrainGitError as e: raise HTTPException(400,str(e))
    @r.get("/repositories/{name}")
    def get(name:str):
        try:return {"ok":True,"repository":svc.repository(name),"branches":svc.branches(name)}
        except BrainGitError as e: raise HTTPException(404,str(e))
    @r.post("/repositories/{name}/branches")
    def branch(name:str,body:BranchIn):
        try:return {"ok":True,"branches":svc.create_branch(name,body.branch,body.from_ref)}
        except BrainGitError as e: raise HTTPException(400,str(e))
    @r.post("/repositories/{name}/commits")
    def commit(name:str,body:CommitIn):
        try:return {"ok":True,"commit":svc.commit_files(name,body.files,body.message,body.branch)}
        except BrainGitError as e: raise HTTPException(400,str(e))
    @r.get("/repositories/{name}/file")
    def file(name:str,path:str,ref:str="HEAD"):
        try:return {"ok":True,"path":path,"ref":ref,"content":svc.read_file_at(name,path,ref)}
        except BrainGitError as e: raise HTTPException(404,str(e))
    @r.get("/repositories/{name}/fsck")
    def fsck(name:str):
        try:return svc.fsck(name)
        except BrainGitError as e: raise HTTPException(404,str(e))
    @r.post("/workflows")
    def create_workflow(body:WorkflowIn):
        wf_id=f"brain-wf-{int(time.time()*1000)}"
        service.root.joinpath("workflows").mkdir(parents=True,exist_ok=True)
        import json
        p=service.root/"workflows"/f"{wf_id}.json"
        p.write_text(json.dumps({"id":wf_id,"name":body.name,"status":"QUEUED","created_at":time.time(),"command":body.command,"metadata":body.metadata},ensure_ascii=False,indent=2),encoding="utf-8")
        return {"ok":True,"workflow":{"id":wf_id,"name":body.name,"status":"QUEUED"}}
    @r.get("/workflows")
    def workflows():
        d=service.root/"workflows"; items=[]
        if d.exists():
            import json
            for p in sorted(d.glob("*.json"),reverse=True):
                try: items.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception: pass
        return {"ok":True,"workflows":items}
    @r.get("/workflows/{workflow_id}")
    def workflow(workflow_id:str):
        import json
        p=service.root/"workflows"/f"{workflow_id}.json"
        if not p.exists(): raise HTTPException(404,"WORKFLOW_NOT_FOUND")
        return {"ok":True,"workflow":json.loads(p.read_text(encoding="utf-8"))}
    @r.get("/audit")
    def audit(repository:str|None=None): return {"ok":True,"audit":svc.audit(repository)}
    return r
