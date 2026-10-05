from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from .audit_chain import AuditChain
from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class ChunkResult:
    chunk_id: str
    status: str
    output: Any = None
    error: str | None = None


class ParallelChunkRunner:
    """Download-manager-style bounded parallel work runner.

    Independent chunks run concurrently. Each verified chunk is checkpointed
    durably, so a restart resumes only unfinished chunks instead of rebuilding
    the entire stage.
    """

    def __init__(self, store: SQLiteStateStore, audit: AuditChain) -> None:
        self.store = store
        self.audit = audit

    def _key(self, run_id: str, chunk_id: str) -> str:
        return f"pipeline.chunk:{run_id}:{chunk_id}"

    def run(
        self,
        run_id: str,
        chunks: list[str],
        execute: Callable[[str], Any],
        verify: Callable[[str, Any], bool],
        *,
        max_workers: int = 4,
    ) -> list[ChunkResult]:
        if not run_id:
            raise ValueError("run_id is required")
        if not chunks:
            return []
        if len(set(chunks)) != len(chunks):
            raise ValueError("chunk ids must be unique")
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")

        pending = []
        results: dict[str, ChunkResult] = {}

        for chunk_id in chunks:
            saved = self.store.get(self._key(run_id, chunk_id))
            if saved and saved.get("status") == "SUCCESS":
                results[chunk_id] = ChunkResult(
                    chunk_id, "SUCCESS", output=saved.get("output")
                )
            else:
                pending.append(chunk_id)

        def one(chunk_id: str) -> ChunkResult:
            self.audit.record(
                "pipeline.chunk.started",
                {"run_id": run_id, "chunk_id": chunk_id},
            )
            try:
                output = execute(chunk_id)
                if not verify(chunk_id, output):
                    raise RuntimeError("chunk independent verification failed")
                self.store.set(
                    self._key(run_id, chunk_id),
                    {"status": "SUCCESS", "output": output},
                )
                self.audit.record(
                    "pipeline.chunk.verified",
                    {"run_id": run_id, "chunk_id": chunk_id},
                )
                return ChunkResult(chunk_id, "SUCCESS", output=output)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                self.store.set(
                    self._key(run_id, chunk_id),
                    {"status": "FAILED", "error": error},
                )
                self.audit.record(
                    "pipeline.chunk.failed",
                    {"run_id": run_id, "chunk_id": chunk_id, "error": error},
                )
                return ChunkResult(chunk_id, "FAILED", error=error)

        with ThreadPoolExecutor(max_workers=min(max_workers, len(pending))) as pool:
            futures = {pool.submit(one, chunk_id): chunk_id for chunk_id in pending}
            for future in as_completed(futures):
                result = future.result()
                results[result.chunk_id] = result

        return [results[chunk_id] for chunk_id in chunks]


__all__ = ["ChunkResult", "ParallelChunkRunner"]
