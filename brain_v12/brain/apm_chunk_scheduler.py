"""Download-Manager-style chunk scheduler for large Brain stages."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Chunk:
    id: str
    stage_id: str
    index: int
    input_fingerprint: str = ""


class ChunkScheduler:
    """Run independent chunks with bounded retries and verified checkpoints."""

    def __init__(self, chunks: list[Chunk], state_dir: str, max_workers: int = 4,
                 retry_limit: int = 1):
        self.chunks = {c.id: c for c in chunks}
        if len(self.chunks) != len(chunks):
            raise ValueError("duplicate chunk id")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if max_workers < 1 or retry_limit < 0:
            raise ValueError("invalid scheduler limits")
        self.max_workers = max_workers
        self.retry_limit = retry_limit

    def _fingerprint(self, chunk: Chunk) -> str:
        payload = {
            "id": chunk.id,
            "stage_id": chunk.stage_id,
            "index": chunk.index,
            "input_fingerprint": chunk.input_fingerprint,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _path(self, chunk: Chunk) -> Path:
        return self.state_dir / f"chunk_{chunk.id.replace('/', '_')}.json"

    def _cached(self, chunk: Chunk) -> dict[str, Any] | None:
        path = self._path(chunk)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if data.get("status") == "VERIFIED_COMPLETED" and data.get("fingerprint") == self._fingerprint(chunk):
            return data
        return None

    def run(
        self,
        executor: Callable[[Chunk], dict[str, Any]],
        verifier: Callable[[Chunk, dict[str, Any]], dict[str, Any] | bool],
    ) -> dict[str, Any]:
        completed: set[str] = set()
        blocked: set[str] = set()
        evidence: dict[str, Any] = {}
        attempts = {cid: 0 for cid in self.chunks}

        for chunk in self.chunks.values():
            cached = self._cached(chunk)
            if cached:
                completed.add(chunk.id)
                evidence[chunk.id] = cached

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            running: dict[Any, Chunk] = {}
            for chunk in self.chunks.values():
                if chunk.id in completed:
                    continue
                if len(running) >= self.max_workers:
                    break
                attempts[chunk.id] += 1
                running[pool.submit(executor, chunk)] = chunk

            while running:
                future = next(as_completed(list(running)))
                chunk = running.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

                verification = verifier(chunk, result)
                verified = bool(verification) if isinstance(verification, bool) else bool(verification.get("verified"))
                if verified:
                    record = {
                        "chunk_id": chunk.id,
                        "stage_id": chunk.stage_id,
                        "status": "VERIFIED_COMPLETED",
                        "fingerprint": self._fingerprint(chunk),
                        "attempt": attempts[chunk.id],
                        "result": result,
                        "verification": verification,
                        "evidence_ref": (
                            verification.get("evidence_ref")
                            if isinstance(verification, dict) else None
                        ) or f"chunk://{chunk.id}/verified",
                    }
                    self._path(chunk).write_text(json.dumps(record, indent=2), encoding="utf-8")
                    completed.add(chunk.id)
                    evidence[chunk.id] = record
                elif attempts[chunk.id] <= self.retry_limit:
                    attempts[chunk.id] += 1
                    running[pool.submit(executor, chunk)] = chunk
                else:
                    blocked.add(chunk.id)
                    self._path(chunk).write_text(json.dumps({
                        "chunk_id": chunk.id,
                        "stage_id": chunk.stage_id,
                        "status": "FAILED",
                        "fingerprint": self._fingerprint(chunk),
                        "attempt": attempts[chunk.id],
                        "result": result,
                        "verification": verification,
                    }, indent=2), encoding="utf-8")

                for candidate in self.chunks.values():
                    if candidate.id in completed or candidate.id in blocked:
                        continue
                    if candidate.id in {c.id for c in running.values()}:
                        continue
                    if len(running) >= self.max_workers:
                        break
                    attempts[candidate.id] += 1
                    running[pool.submit(executor, candidate)] = candidate

        return {
            "status": "VERIFIED_COMPLETED" if len(completed) == len(self.chunks) else "BLOCKED",
            "total": len(self.chunks),
            "completed": sorted(completed),
            "blocked": sorted(blocked),
            "attempts": attempts,
            "evidence": evidence,
        }
