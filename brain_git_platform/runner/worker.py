from __future__ import annotations

import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from .. import service
from ..workflow_manifest import load
from ..workflows import claim_next, get_run, heartbeat, recover_stale, set_status
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
        safe += ".json"
    for candidate in (
        workspace / "brain_git_platform" / "workflows" / safe,
        workspace / "workflows" / safe,
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"workflow manifest not found: {workflow_name}")


def execute_claimed_run(run: dict, worker_id: str, heartbeat_interval: float = 30.0) -> dict:
    run_id = int(run["id"])
    temp = Path(tempfile.mkdtemp(prefix="brain-runner-"))
    stop_heartbeat = threading.Event()
    heartbeat_error: list[Exception] = []

    def keepalive() -> None:
        while not stop_heartbeat.wait(heartbeat_interval):
            try:
                heartbeat(run_id, worker_id)
            except Exception as exc:
                heartbeat_error.append(exc)
                stop_heartbeat.set()
                return

    thread = threading.Thread(target=keepalive, name=f"brain-heartbeat-{run_id}", daemon=True)
    try:
        workspace = temp / "workspace"
        checkout_repository(run["namespace"], run["repository"], run["ref"], workspace)
        heartbeat(run_id, worker_id)
        thread.start()
        workflow = load(_manifest_for(workspace, run["workflow"]))
        result = BrainRunnerExecutor(
            workspace,
            RunLog(service.ROOT / "logs"),
            ArtifactStore(str(service.ROOT / "artifacts")),
        ).run_workflow(workflow, run_id)
        if heartbeat_error:
            raise heartbeat_error[0]
        status = "success" if result.success else "failed"
        set_status(run_id, status, worker_id=worker_id)
        return {"run_id": run_id, "status": status, "steps": [x.__dict__ for x in result.steps]}
    except Exception:
        try:
            set_status(run_id, "failed", worker_id=worker_id)
        except Exception:
            pass
        raise
    finally:
        stop_heartbeat.set()
        thread.join(timeout=max(1.0, heartbeat_interval))
        shutil.rmtree(temp, ignore_errors=True)


def execute_queued_run(run_id: int) -> dict:
    run = get_run(run_id)
    if run["status"] != "queued":
        raise ValueError("workflow run is not queued")
    worker_id = "manual-" + uuid.uuid4().hex
    claimed = claim_next(worker_id)
    if not claimed or int(claimed["id"]) != run_id:
        raise ValueError("workflow run could not be claimed")
    return execute_claimed_run(claimed, worker_id)


def worker_once(worker_id: str | None = None) -> dict | None:
    worker_id = worker_id or "worker-" + uuid.uuid4().hex
    recover_stale()
    run = claim_next(worker_id)
    if not run:
        return None
    return execute_claimed_run(run, worker_id)
