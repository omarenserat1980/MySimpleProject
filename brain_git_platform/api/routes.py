from __future__ import annotations
from .contracts import ApiResponse
from ..service import Repository, create_repository, repository_path
from ..refs import list_refs, create_branch
from ..workflows import dispatch, get_run, set_status

class BrainGitApi:
    def create_repo(self, namespace:str, name:str, default_branch:str="main"):
        repo=create_repository(Repository(namespace,name,default_branch))
        return ApiResponse(True,{"namespace":namespace,"name":name,"default_branch":default_branch,"path":str(repo)}).json()

    def refs(self, namespace:str, name:str):
        return ApiResponse(True,{"refs":list_refs(repository_path(namespace,name))}).json()

    def create_branch(self, namespace:str, name:str, branch:str, start_point:str="HEAD"):
        create_branch(repository_path(namespace,name),branch,start_point)
        return ApiResponse(True,{"branch":branch}).json()

    def dispatch_workflow(self, namespace:str, name:str, workflow:str, ref:str="main"):
        run=dispatch(namespace,name,workflow,ref)
        return ApiResponse(True,{"run":run.__dict__}).json()

    def workflow(self, run_id:int):
        return ApiResponse(True,get_run(run_id)).json()

    def set_workflow_status(self, run_id:int, status:str):
        set_status(run_id,status)
        return ApiResponse(True,{"run_id":run_id,"status":status}).json()
