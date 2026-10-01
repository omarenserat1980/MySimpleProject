"""Brain-native HTTP API for Git repositories."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .service import BrainGitError, BrainGitService

class RepoIn(BaseModel):
    name:str
    private:bool=True

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
    @r.get("/repositories/{name}/fsck")
    def fsck(name:str):
        try:return svc.fsck(name)
        except BrainGitError as e: raise HTTPException(404,str(e))
    @r.get("/audit")
    def audit(repository:str|None=None): return {"ok":True,"audit":svc.audit(repository)}
    return r
