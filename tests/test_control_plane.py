from pathlib import Path

from platform_foundation.audit import EvidenceLedger
from platform_foundation.control_plane import ControlPlane
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.task_state import TaskStatus


def make_plane(tmp_path: Path, allowed=None):
    return ControlPlane(
        SQLiteStateStore(tmp_path / "state.sqlite3"),
        EvidenceLedger(),
        PermissionBoundary(allowed or {"compute": ActionRisk.READ}),
    )


def test_allowed_task_executes_and_persists_success(tmp_path: Path) -> None:
    plane = make_plane(tmp_path)
    plane.register("t1", "compute", ActionRisk.READ, lambda: {"ok": True})
    result = plane.run("t1")
    assert result.status is TaskStatus.SUCCESS
    assert plane.state.get("task:t1")["status"] == "SUCCESS"
    assert plane.evidence.events()[-1].event == "task_succeeded"


def test_denied_task_never_executes(tmp_path: Path) -> None:
    called = []
    plane = make_plane(tmp_path)
    plane.register("t2", "unknown", ActionRisk.WRITE, lambda: called.append(True))
    result = plane.run("t2")
    assert result.status is TaskStatus.FAILED
    assert not called
    assert plane.evidence.events()[-1].event == "task_denied"


def test_handler_failure_is_recorded(tmp_path: Path) -> None:
    plane = make_plane(tmp_path)
    def boom():
        raise RuntimeError("boom")
    plane.register("t3", "compute", ActionRisk.READ, boom)
    result = plane.run("t3")
    assert result.status is TaskStatus.FAILED
    assert plane.evidence.events()[-2].event == "task_diagnostic"
    assert plane.evidence.events()[-2].payload["error_type"] == "RuntimeError"
    assert plane.state.get("task:t3")["diagnostic"]["error"] == "boom"
    assert plane.evidence.events()[-1].event == "task_failed"
