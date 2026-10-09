from __future__ import annotations

import json
import tempfile
from pathlib import Path

from platform_foundation.persistent_state import SQLiteStateStore


def phase21_restart_recovery() -> dict:
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "brain_state.db"

        first = SQLiteStateStore(db)
        checkpoint = {
            "pipeline": "phase-21-proof",
            "stage": 21,
            "status": "CHECKPOINTED",
            "next_action": "RESUME",
        }
        first.set("brain_checkpoint", checkpoint)
        assert first.get("brain_checkpoint") == checkpoint
        first.close()

        # Simulated process restart: a new runtime opens the same durable state.
        second = SQLiteStateStore(db)
        restored = second.get("brain_checkpoint")
        ready = second.is_ready()
        second.close()

        ok = ready and restored == checkpoint and restored["next_action"] == "RESUME"
        evidence = {
            "phase": 21,
            "status": "PASS" if ok else "FAIL",
            "persistence": "sqlite",
            "checkpoint_restored": restored == checkpoint,
            "resume_action": restored.get("next_action") if restored else None,
        }
        return evidence


if __name__ == "__main__":
    result = phase21_restart_recovery()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
