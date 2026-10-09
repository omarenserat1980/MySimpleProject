from pathlib import Path

from platform_foundation.audit import EvidenceLedger
from platform_foundation.control_plane import ControlPlane
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.task_state import TaskStatus


def test_full_control_path_is_restartable(tmp_path: Path) -> None:
    db = tmp_path / "brain.sqlite3"
    evidence = EvidenceLedger()
    plane = ControlPlane(SQLiteStateStore(db), evidence, PermissionBoundary({"build": ActionRisk.WRITE}))
    plane.register("build-1", "build", ActionRisk.WRITE, lambda: "artifact-ready")
    result = plane.run("build-1")
    assert result.status is TaskStatus.SUCCESS
    assert result.output == "artifact-ready"
    assert evidence.events()[-1]["event"] == "task_succeeded"

    plane.state.close()
    reopened = SQLiteStateStore(db)
    assert reopened.get("task:build-1")["status"] == "SUCCESS"
    assert reopened.is_ready()
    reopened.close()
