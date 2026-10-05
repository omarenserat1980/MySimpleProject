import json
import os
import time
from pathlib import Path

from brain_v12.local_worker import brain_local_worker as worker


def test_stale_running_job_is_recovered_to_queue(tmp_path, monkeypatch):
    root = tmp_path / "worker"
    monkeypatch.setenv("BRAIN_LOCAL_WORKER_ROOT", str(root))
    monkeypatch.setenv("BRAIN_LOCAL_WORKER_RECOVERY_TTL_SECONDS", "30")
    old_root = worker.ROOT
    old_dirs = (worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED)
    try:
        worker.ROOT = root
        worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED = (
            root / x for x in ("queued", "running", "completed", "failed")
        )
        worker.setup()
        job = worker.RUNNING / "crash-job.json"
        job.write_text(json.dumps({
            "job_id": "crash-job",
            "task": "python_version",
            "params": {},
        }), encoding="utf-8")
        old = time.time() - 60
        os.utime(job, (old, old))

        recovered = worker.recover_stale_jobs()

        assert recovered == ["crash-job.json"]
        assert (worker.QUEUED / "crash-job.json").exists()
        assert not job.exists()
    finally:
        worker.ROOT = old_root
        worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED = old_dirs


def test_recovered_job_executes_after_restart(tmp_path, monkeypatch):
    root = tmp_path / "worker"
    monkeypatch.setenv("BRAIN_LOCAL_WORKER_ROOT", str(root))
    old_root = worker.ROOT
    old_dirs = (worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED)
    try:
        worker.ROOT = root
        worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED = (
            root / x for x in ("queued", "running", "completed", "failed")
        )
        worker.setup()
        job = worker.RUNNING / "restart-job.json"
        job.write_text(json.dumps({
            "job_id": "restart-job",
            "task": "python_version",
            "params": {},
        }), encoding="utf-8")
        old = time.time() - 60
        os.utime(job, (old, old))

        assert worker.recover_stale_jobs() == ["restart-job.json"]
        worker.process(worker.QUEUED / "restart-job.json")

        result = json.loads((worker.COMPLETED / "restart-job.json").read_text(encoding="utf-8"))
        assert result["status"] == "VERIFIED"
        assert result["job_id"] == "restart-job"
        assert result["evidence"]["python"]
    finally:
        worker.ROOT = old_root
        worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED = old_dirs


def test_base_expansion_integrity_executes_as_brain_worker_task(tmp_path, monkeypatch):
    root = tmp_path / "worker"
    monkeypatch.setenv("BRAIN_LOCAL_WORKER_ROOT", str(root))
    old_root = worker.ROOT
    old_dirs = (worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED)
    try:
        worker.ROOT = root
        worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED = (
            root / x for x in ("queued", "running", "completed", "failed")
        )
        worker.setup()

        job = worker.QUEUED / "base-expansion-integrity.json"
        job.write_text(json.dumps({
            "job_id": "base-expansion-integrity",
            "task": "brain_base_expansion_integrity",
            "params": {},
        }), encoding="utf-8")

        worker.process(job)

        result = json.loads(
            (worker.COMPLETED / "base-expansion-integrity.json").read_text(encoding="utf-8")
        )
        assert result["status"] == "VERIFIED"
        assert result["worker_id"] == worker.WORKER_ID
        assert result["evidence"]["provider"] == "brain-local-worker"
        assert result["evidence"]["status"] in {"VERIFIED", "FAILED"}
        assert "returncode" in result["evidence"]
        assert (Path(__file__).resolve().parents[1] / "brain6_artifacts" /
                "base_expansion" / "integrity_report.json").exists()
    finally:
        worker.ROOT = old_root
        worker.QUEUED, worker.RUNNING, worker.COMPLETED, worker.FAILED = old_dirs
