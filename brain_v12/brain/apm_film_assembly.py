"""Assembly and Cinematic Master QC gate for segmented films."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence
import hashlib
import json
import time


@dataclass(frozen=True)
class SegmentArtifact:
    id: str
    index: int
    path: str
    duration_s: float


class FilmAssemblyGate:
    def __init__(self, state_dir: str):
        self.state_dir = Path(state_dir)

    def _manifest_path(self) -> Path:
        return self.state_dir / "film_assembly_manifest.json"

    def _fingerprint(self, artifacts: Sequence[SegmentArtifact]) -> str:
        payload = [{"id": a.id, "index": a.index, "path": a.path, "duration_s": a.duration_s}
                   for a in artifacts]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def assemble(
        self,
        *,
        film_id: str,
        expected_segments: int,
        verified_segments: Sequence[SegmentArtifact],
        assembler: Callable[[Sequence[SegmentArtifact], str], dict[str, Any]],
        master_qc: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        artifacts = sorted(verified_segments, key=lambda a: a.index)

        if len(artifacts) != expected_segments:
            return {
                "status": "BLOCKED",
                "reason": "SEGMENT_EVIDENCE_INCOMPLETE",
                "expected_segments": expected_segments,
                "verified_segments": len(artifacts),
            }

        indexes = [a.index for a in artifacts]
        if indexes != list(range(expected_segments)):
            return {
                "status": "BLOCKED",
                "reason": "SEGMENT_INDEX_GAP",
                "indexes": indexes,
            }

        for artifact in artifacts:
            if not Path(artifact.path).is_file():
                return {
                    "status": "BLOCKED",
                    "reason": "SEGMENT_FILE_MISSING",
                    "segment_id": artifact.id,
                }

        fingerprint = self._fingerprint(artifacts)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "status": "ASSEMBLY_READY",
            "film_id": film_id,
            "expected_segments": expected_segments,
            "segments": [a.__dict__ for a in artifacts],
            "fingerprint": fingerprint,
            "created_at": time.time(),
        }
        self._manifest_path().write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        assembled = assembler(artifacts, str(self.state_dir))
        if assembled.get("status") != "VERIFIED_COMPLETED":
            manifest["status"] = "ASSEMBLY_FAILED"
            manifest["assembly"] = assembled
            self._manifest_path().write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            return manifest

        qc = master_qc(assembled)
        manifest["assembly"] = assembled
        manifest["master_qc"] = qc
        manifest["status"] = "VERIFIED_COMPLETED" if qc.get("accepted") else "MASTER_QC_REJECTED"
        manifest["completed_at"] = time.time()
        self._manifest_path().write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return manifest
