"""Create a small, deterministic metadata bundle for execution evidence."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class EvidenceBundle:
    task_id: str
    status: str
    created_at: str
    evidence: Mapping[str, Any]

    def serialize(self) -> str:
        return json.dumps(
            {"schema": "brain.execution-evidence.v1", "task_id": self.task_id,
             "status": self.status, "created_at": self.created_at,
             "evidence": dict(self.evidence)},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.serialize().encode("utf-8")).hexdigest()


def build_evidence_bundle(task_id: str, status: str, created_at: str,
                          evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not task_id.strip() or not status.strip() or not created_at.strip():
        raise ValueError("EVIDENCE_METADATA_REQUIRED")
    bundle = EvidenceBundle(task_id, status, created_at, evidence)
    serialized = bundle.serialize()
    return {"bundle": json.loads(serialized), "sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            "signature_verified": False, "execution_verified": False}
