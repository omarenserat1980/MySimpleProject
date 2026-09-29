from __future__ import annotations

from pathlib import Path

from .. import service as git_service
from ..storage.artifacts import ArtifactStore
from ..workflow_manifest import load
from ..workflows import get_run, set_status
from .executor import BrainRunnerExecutor
from .logs import RunLog


def execute_run(run_id: int, manifest: Path, workspace: Path) -> dict:
    run = get_run(run_id)
    if run["status"] not in {"queued", "running"}:
        raise ValueError("workflow run is not executable")

    set_status(run_id, "running")
    logs = RunLog(git_service.ROOT / "logs")
    artifacts = ArtifactStore(str(git_service.ROOT / "artifacts"))
    try:
        workflow = load(manifest)
        result = BrainRunnerExecutor(workspace, logs, artifacts).run_workflow(workflow, run_id)
        set_status(run_id, "success" if result.success else "failed")
        return {
            "run_id": run_id,
            "status": "success" if result.success else "failed",
            "steps": [item.__dict__ for item in result.steps],
        }
    except Exception:
        set_status(run_id, "failed")
        raise
