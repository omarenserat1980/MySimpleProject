from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path


def phase20_brain_artifact_only() -> dict:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        artifact = root / "brain_artifact.bin"
        manifest = root / "manifest.json"
        payload = b"BRAIN_PHASE_20_ARTIFACT\n"
        artifact.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        manifest.write_text(
            json.dumps(
                {
                    "producer": "brain",
                    "phase": 20,
                    "artifact": artifact.name,
                    "sha256": digest,
                    "size": len(payload),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        loaded = json.loads(manifest.read_text(encoding="utf-8"))
        actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
        ok = (
            loaded["producer"] == "brain"
            and loaded["phase"] == 20
            and loaded["size"] == artifact.stat().st_size
            and loaded["sha256"] == actual
            and actual == digest
        )
        return {
            "phase": 20,
            "status": "PASS" if ok else "FAIL",
            "artifact": artifact.name,
            "sha256": actual,
            "verified": ok,
        }


if __name__ == "__main__":
    result = phase20_brain_artifact_only()
    print(result)
    raise SystemExit(0 if result["status"] == "PASS" else 1)
