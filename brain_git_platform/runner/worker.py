from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .. import service
from ..workflow_manifest import load
from ..workflows import get_run, set_status
from .executor import BrainRunnerExecutor
from .logs import RunLog
from ..storage.artifacts import ArtifactStore


def checkout_repository(namespace: str, repository: str, ref: str, destination: Path) -> Path:
    repo = service.repository_path(namespace, repository)
    destination.parent.mkdir(parents=True, exist_ok=True)
    import subprocess
    subprocess.run(["git", "clone", "--no-tags", "--branch", ref, str(repo), str(destination)], check=True, capture_output=True)
    return destination


def execute_queued_run(run_id: int, manifest_relative: str = "brain_git_platform/workflows/brain-git-foundation.json") -> dict:
    run = get_run(run_id)
    if run["status"] != "queued":
        raise ValueError("workflow run is not queued")
    set_status(run_id, "running")
    temp = Path(tempfile.mkdtemp(prefix="brain-runner-"))
    try:
        workspace = temp / "workspace"
        checkout_repository(run["namespace"], run["repository"], run["ref"], workspace)
        manifest = workspace / manifest_relative
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
