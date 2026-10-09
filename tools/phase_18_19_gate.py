from __future__ import annotations

import os
import tempfile
from pathlib import Path

from brain_v12.brain_git.service import BrainGitService
from brain_v12.blade_server import BladeChassis
from brain_v12.brain.resource_manager import ResourceManager
from brain_v12.brain.virtual_task_queue import VirtualTaskQueue


def phase18_brain_git_only() -> dict:
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS"):
        os.environ.pop(key, None)
    with tempfile.TemporaryDirectory() as d:
        service = BrainGitService(Path(d) / "git")
        repo = service.create_repository("phase18")
        service.create_branch("phase18", "work", "main")
        commit = service.commit_files(
            "phase18",
            {"PHASE18.txt": "BRAIN_GIT_ONLY\n"},
            "phase 18 proof",
            "work",
        )
        content = service.read_file_at("phase18", "PHASE18.txt", "work")
        integrity = service.fsck("phase18")
        audit = service.audit("phase18")
        ok = (
            repo["name"] == "phase18"
            and commit["branch"] == "work"
            and content == "BRAIN_GIT_ONLY"
            and integrity["ok"]
            and len(audit) >= 3
        )
        return {"phase": 18, "status": "PASS" if ok else "FAIL", "commit": commit["sha"], "audit_events": len(audit)}


def phase19_brain_scheduler_only() -> dict:
    with tempfile.TemporaryDirectory() as d:
        chassis = BladeChassis("PHASE19")
        blade = chassis.create_blade({"cpu"})
        blade.power_on()
        queue = VirtualTaskQueue(
            chassis,
            ResourceManager(),
            max_workers=1,
            store_path=str(Path(d) / "tasks.db"),
        )
        task = queue.submit([("MOVI", 0, 7), ("OUT", 0), ("HALT",)], {"cpu"}, task_id="phase19-workflow")
        for _ in range(100):
            current = queue.get(task.task_id)
            if current and current.status in {"COMPLETED", "FAILED"}:
                break
        current = queue.get(task.task_id)
        queue.shutdown()
        ok = current is not None and current.status == "COMPLETED" and current.result and current.result.get("ok") is True
        return {"phase": 19, "status": "PASS" if ok else "FAIL", "task_id": task.task_id, "task_status": current.status if current else "UNKNOWN"}


def main() -> int:
    p18 = phase18_brain_git_only()
    p19 = phase19_brain_scheduler_only()
    print({"phase18": p18, "phase19": p19})
    return 0 if p18["status"] == "PASS" and p19["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
