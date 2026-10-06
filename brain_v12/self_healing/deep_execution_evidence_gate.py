"""Evidence gate for deep execution batches.

A batch is not VERIFIED merely because its executor returned success. The gate
requires completed operations, zero failures, checkpoint persistence, and an
explicit evidence record.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class DeepEvidenceGate:
    schema = "brain-deep-evidence-gate/v1"

    def __init__(self, state_dir: str | Path = ".brain/state/deep") -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_path = self.state_dir / "deep_execution_evidence.json"

    def evaluate(self, state: dict[str, Any]) -> dict[str, Any]:
        last = state.get("last_run", {})
        executed = int(last.get("executed", 0))
        failed = int(last.get("failed", 0))
        checkpoint = self.state_dir / "deep_execution_checkpoint.json"
        checkpoint_ok = checkpoint.is_file() and checkpoint.stat().st_size > 0

        # PLANNED is intentionally not accepted as proof of completion.
        history = state.get("history", [])
        verified_count = sum(
            1 for item in history[-executed:] if item.get("result", {}).get("status")
            in {"PASS", "VERIFIED", "COMPLETED"}
        )
        verified = executed > 0 and failed == 0 and verified_count == executed and checkpoint_ok

        evidence = {
            "schema": self.schema,
            "timestamp": time.time(),
            "status": "VERIFIED" if verified else "FAILED",
            "verified_completed_allowed": verified,
            "checks": {
                "executed_gt_zero": executed > 0,
                "zero_failures": failed == 0,
                "all_operations_verified": verified_count == executed,
                "checkpoint_persisted": checkpoint_ok,
            },
            "summary": {
                "depth": state.get("depth"),
                "executed": executed,
                "verified": verified_count,
                "failed": failed,
                "checkpoint": str(checkpoint),
            },
        }
        self.evidence_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return evidence
