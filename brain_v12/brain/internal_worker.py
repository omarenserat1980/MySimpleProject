"""Brain-owned local task worker.

Run on the machine that should execute Brain tasks, not on a hosted control
plane. The worker consumes the same durable queue as the Brain API and records
a local evidence file for every attempted task.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path

from .internal_task_runtime import InternalTaskRuntime
from .execution_gateway import BrainExecutionGateway


def build_runtime() -> InternalTaskRuntime:
    root = os.getenv(
        "BRAIN_INTERNAL_RUNTIME_ROOT",
        str(Path(__file__).resolve().parents[1] / ".brain" / "internal_runtime"),
    )
    return InternalTaskRuntime(root=root, gateway=BrainExecutionGateway())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Brain's local task queue worker")
    parser.add_argument("--once", action="store_true", help="process at most one pending task")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    poll_seconds = max(0.25, min(args.poll_seconds, 60.0))
    timeout = max(1, min(args.timeout, 3600))
    runtime = build_runtime()
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print(json.dumps({
        "event": "BRAIN_LOCAL_WORKER_STARTED",
        "runtime": runtime.status(),
        "mode": "once" if args.once else "continuous",
    }, ensure_ascii=False), flush=True)

    while not stopping:
        pending = runtime.pending()
        if pending:
            result = runtime.run_one(timeout=timeout)
            print(json.dumps({"event": "BRAIN_TASK_RESULT", "result": result},
                             ensure_ascii=False), flush=True)
            if args.once:
                return 0 if result.get("state") == "COMPLETED" else 1
        else:
            if args.once:
                print(json.dumps({"event": "BRAIN_WORKER_IDLE",
                                  "status": runtime.status()}, ensure_ascii=False))
                return 0
            time.sleep(poll_seconds)

    print(json.dumps({"event": "BRAIN_LOCAL_WORKER_STOPPED"}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
