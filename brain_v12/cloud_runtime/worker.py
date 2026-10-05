"""Long-lived Brain Cloud Worker.

Runs the Brain-owned durable queue inside a cloud VM/container. It does not
register as a GitHub Actions runner and does not require GitHub to execute.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from ..brain.internal_task_runtime import InternalTaskRuntime


def run_forever() -> None:
    os.environ.setdefault("BRAIN_INTERNAL_RUNNER_FLAG", "1")
    root = Path(os.getenv("BRAIN_RUNTIME_ROOT", "/var/lib/brain/runtime"))
    runtime = InternalTaskRuntime(root)
    poll = max(1, int(os.getenv("BRAIN_WORKER_POLL_SECONDS", "2")))
    print("BRAIN_CLOUD_RUNTIME=STARTING", flush=True)
    while True:
        result = runtime.run_one(timeout=int(os.getenv("BRAIN_TASK_TIMEOUT", "3600")))
        if result.get("state") != "IDLE":
            print(
                f"BRAIN_CLOUD_TASK state={result.get('state')} "
                f"task_id={result.get('task_id')} "
                f"evidence={result.get('evidence_ref')}",
                flush=True,
            )
        time.sleep(poll)


if __name__ == "__main__":
    run_forever()
