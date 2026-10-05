"""Long-lived Brain Cloud Worker.

Runs the Brain-owned durable queue inside a cloud VM/container. It does not
register as a GitHub Actions runner and does not require GitHub to execute.
The heartbeat is the runtime attestation used by the API; configuration flags
alone never prove that the worker is online.
"""
from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

from ..brain.internal_task_runtime import InternalTaskRuntime


def _heartbeat_path(root: Path) -> Path:
    return root / "cloud-worker-heartbeat.json"


def _write_heartbeat(path: Path, state: str, **extra: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "service": "brain-cloud-runtime",
        "state": state,
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "timestamp": time.time(),
        **extra,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def run_forever() -> None:
    os.environ.setdefault("BRAIN_INTERNAL_RUNNER_FLAG", "1")
    root = Path(os.getenv("BRAIN_RUNTIME_ROOT", "/var/lib/brain/runtime"))
    runtime = InternalTaskRuntime(root)
    heartbeat = _heartbeat_path(root)
    poll = max(1, int(os.getenv("BRAIN_WORKER_POLL_SECONDS", "2")))
    timeout = int(os.getenv("BRAIN_TASK_TIMEOUT", "3600"))
    print("BRAIN_CLOUD_RUNTIME=STARTING", flush=True)
    _write_heartbeat(heartbeat, "RUNNING", poll_seconds=poll)
    try:
        while True:
            _write_heartbeat(heartbeat, "RUNNING", poll_seconds=poll)
            result = runtime.run_one(timeout=timeout)
            if result.get("state") != "IDLE":
                print(
                    f"BRAIN_CLOUD_TASK state={result.get('state')} "
                    f"task_id={result.get('task_id')} "
                    f"evidence={result.get('evidence_ref')}",
                    flush=True,
                )
            time.sleep(poll)
    except BaseException as exc:
        _write_heartbeat(heartbeat, "FAILED", error=str(exc)[:1000])
        raise


if __name__ == "__main__":
    run_forever()
