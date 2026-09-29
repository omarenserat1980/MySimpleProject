from __future__ import annotations
import hashlib, os
from pathlib import Path

class ArtifactStore:
    def __init__(self, root: str = "./brain_git_data/artifacts"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, run_id: str, name: str, data: bytes) -> dict:
        safe = Path(name).name
        target = self.root / run_id / safe
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {"run_id": run_id, "name": safe, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}

    def get(self, run_id: str, name: str) -> bytes:
        target = self.root / run_id / Path(name).name
        if not target.exists():
            raise FileNotFoundError(name)
        return target.read_bytes()
