"""Evidence-first diagnostics for failed Brain tasks."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def emit_task_failure_diagnostic(
    task: dict[str, Any],
    error: str,
    *,
    phase: str = "TASK_FAILURE",
    extra: dict[str, Any] | None = None,
) -> str:
    """Persist a diagnostic artifact before a failed task can terminate."""
    root = Path(os.getenv("BRAIN_EVIDENCE_DIR", "brain6_artifacts/diagnostics"))
    root.mkdir(parents=True, exist_ok=True)
    task_id = str(task.get("id", "unknown"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    payload = {
        "schema": "brain.task_failure_diagnostic.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "task": {
            "id": task_id,
            "title": task.get("title", ""),
            "status": task.get("status", ""),
            "attempts": task.get("attempts", 0),
        },
        "error": str(error),
        "solution_run": task.get("solution_run"),
        "extra": extra or {},
    }
    target = root / f"{stamp}-{task_id}.json"
    fd, tmp_name = tempfile.mkstemp(prefix=".diagnostic-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return str(target)
