from __future__ import annotations

from .contracts import ApiResponse
from ..service import Repository, create_repository, repository_path, ROOT
from ..refs import list_refs, create_branch
from ..workflows import dispatch, get_run, set_status, cancel, retry
from ..pull_requests import create_pull_request, merge_pull_request, close_pull_request
from ..runner.logs import RunLog
from ..storage.artifacts import ArtifactStore


class BrainGitApi:
    def create_repo(self, namespace: str, name: str, default_branch: str = "main"):
        repo = create_repository(Repository(namespace, name, default_branch))
        return ApiResponse(True, {"namespace": namespace, "name": name, "default_branch": default_branch, "path": str(repo)}).json()

    def refs(self, namespace: str, name: str):
        return ApiResponse(True, {"refs": list_refs(repository_path(namespace, name))}).json()

    def create_branch(self, namespace: str, name: str, branch: str, start_point: str = "HEAD"):
        create_branch(repository_path(namespace, name), branch, start_point)
        return ApiResponse(True, {"branch": branch}).json()

    def dispatch_workflow(self, namespace: str, name: str, workflow: str, ref: str = "main"):
        run = dispatch(namespace, name, workflow, ref)
        return ApiResponse(True, {"run": run.__dict__}).json()

    def workflow(self, run_id: int):
        return ApiResponse(True, get_run(run_id)).json()

    def set_workflow_status(self, run_id: int, status: str):
        set_status(run_id, status)
        return ApiResponse(True, {"run_id": run_id, "status": status}).json()

    def cancel_workflow(self, run_id: int):
        cancel(run_id)
        return ApiResponse(True, {"run_id": run_id, "status": "cancelled"}).json()

    def retry_workflow(self, run_id: int):
        retry(run_id)
        return ApiResponse(True, {"run_id": run_id, "status": "queued"}).json()

    def run_logs(self, run_id: int, stream: str = "stdout"):
        return ApiResponse(True, {"run_id": run_id, "stream": stream, "text": RunLog(ROOT / "logs").read(run_id, stream)}).json()

    def artifact(self, run_id: int, name: str):
        data = ArtifactStore(str(ROOT / "artifacts")).get(str(run_id), name)
        return ApiResponse(True, {"run_id": run_id, "name": name, "size": len(data), "data": data.decode("utf-8", errors="replace")}).json()

    def create_pr(self, namespace: str, repository: str, source: str, target: str, title: str):
        pr = create_pull_request(namespace, repository, source, target, title)
        return ApiResponse(True, {"pull_request": pr.__dict__}).json()

    def merge_pr(self, pr_id: int):
        pr = merge_pull_request(pr_id)
        return ApiResponse(True, {"pull_request": pr.__dict__}).json()

    def close_pr(self, pr_id: int):
        close_pull_request(pr_id)
        return ApiResponse(True, {"pull_request_id": pr_id, "status": "closed"}).json()
