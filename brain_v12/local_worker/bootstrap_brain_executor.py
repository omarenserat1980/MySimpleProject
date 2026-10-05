#!/usr/bin/env python3
"""Bootstrap and run the Brain-owned local execution authority."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from platform_foundation.brain_execution_authority import BrainExecutionAuthority
from brain_v12.local_worker.brain_local_worker import main


def bootstrap() -> dict[str, object]:
    worker_id = os.environ.get("BRAIN_WORKER_ID", "brain-local-01")
    authority = BrainExecutionAuthority(executor_id=worker_id)
    return authority.heartbeat()


if __name__ == "__main__":
    payload = bootstrap()
    print("BRAIN_EXECUTOR_READY")
    print(payload)
    main()
