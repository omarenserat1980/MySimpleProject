from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class RunLog:
    """Append-only stdout/stderr log storage owned by Brain Git."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, run_id: int, stream: str, text: str) -> None:
        if stream not in {"stdout", "stderr"}:
            raise ValueError("invalid stream")
        path = self.root / f"{run_id}.{stream}.log"
        with path.open("a", encoding="utf-8") as handle:
            timestamp = datetime.now(timezone.utc).isoformat()
            handle.write(f"[{timestamp}] {text}")
            if text and not text.endswith("\n"):
                handle.write("\n")

    def read(self, run_id: int, stream: str) -> str:
        if stream not in {"stdout", "stderr"}:
            raise ValueError("invalid stream")
        path = self.root / f"{run_id}.{stream}.log"
        return path.read_text(encoding="utf-8") if path.exists() else ""
