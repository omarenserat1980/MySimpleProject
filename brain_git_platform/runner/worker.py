from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from .. import service
from ..workflow_manifest import load
from ..workflows import claim_next, get_run, heartbeat, set_status
from .executor import BrainRunnerExecutor
from .logs import RunLog
from ..storage.artifacts import ArtifactStore


def checkout_repository(namespace: str, repository: str, ref: str, destination: Path) -> Path:
    repo = service.repository_path(namespace, repository)
    destination.parent.mkdir(parents=True, exist_ok=True)
    import subprocess
    subprocess.run(
        ["git", "clone", "--no-tags", "--branch", ref, str(repo), str(destination)],
        check=True,
        capture_output=True,
    )
    return destination


def _manifest_for(workspace: Path, workflow_name: str) -> Path:
    safe = Path(workflow_name).name
    if safe != workflow_name or not safe.endswith(".json"):
        safe = safe + ".json"
    candidates = [
        workspace / "brain_git_platform" / "workflows" / safe,
        workspace / "workflows" / safe,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"workflow manifest not found: {workflow_name}")


def execute_claimed_run(run: dict, worker_id: str) -> dict:
    run_id = int(run["id"])
    temp = Path(tempfile.mkdtemp(prefix="brain-runner-"))
    try:
        workspace = temp / "workspace"
        checkout_repository(run["namespace"], run["repository"], run["ref"], workspace)
        heartbeat(run_id, worker_id)
        manifest = _manifest_for(workspace, run["workflow"])
        workflow = load(manifest)
        result = BrainRunnerExecutor(
            workspace,
            RunLog(service.ROOT / "logs"),
            ArtifactStore(str(service.ROOT / "artifacts")),
        ).run_workflow(workflow, run_id)
        status = "success" if result.success else "failed"
        set_status(run_id, status)
        return {"run_id": run_id, "status": status, "steps": [x.__dict__ for x in result.steps]}
    except Exception:
        set_status(run_id, "failed")
        raise
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def execute_queued_run(run_id: int) -> dict:
    run = get_run(run_id)
    if run["status"] != "queued":
        raise ValueError("workflow run is not queued")
    worker_id = "manual-" + uuid.uuid4().hex
    from ..workflows import claim_next
    claimed = claim_next(worker_id)
    if not claimed or int(claimed["id"]) != run_id:
        raise ValueError("workflow run could not be claimed")
    return execute_claimed_run(claimed, worker_id)


def worker_once(worker_id: str | None = None) -> dict | None:
    worker_id = worker_id or "worker-" + uuid.uuid4().hex
    run = claim_next(worker_id)
    if not run:
        return None
    return execute_claimed_run(run, worker_id)
