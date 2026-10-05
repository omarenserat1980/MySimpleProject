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
    """Bounded dependency-aware parallel runner with durable chunk checkpoints."""

    def __init__(self, store: SQLiteStateStore, audit: AuditChain) -> None:
        self.store = store
        self.audit = audit

    def _key(self, run_id: str, chunk_id: str) -> str:
        return f"pipeline.chunk:{run_id}:{chunk_id}"

    def run(
        self,
        run_id: str,
        chunks: list[str],
        execute: Callable[[str, dict[str, Any]], Any],
        verify: Callable[[str, Any], bool],
        *,
        dependencies: dict[str, list[str]] | None = None,
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

        deps = dependencies or {}
        known = set(chunks)
        for chunk_id, required in deps.items():
            if chunk_id not in known:
                raise ValueError(f"dependency declared for unknown chunk: {chunk_id}")
            if chunk_id in required:
                raise ValueError(f"chunk cannot depend on itself: {chunk_id}")
            if any(dep not in known for dep in required):
                raise ValueError(f"unknown dependency for chunk: {chunk_id}")

        # Detect dependency cycles before any side effect starts.
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("dependency cycle detected")
            if node in visited:
                return
            visiting.add(node)
            for dep in deps.get(node, []):
                visit(dep)
            visiting.remove(node)
            visited.add(node)

        for chunk_id in chunks:
            visit(chunk_id)

        results: dict[str, ChunkResult] = {}
        outputs: dict[str, Any] = {}
        pending = set(chunks)

        for chunk_id in chunks:
            saved = self.store.get(self._key(run_id, chunk_id))
            if saved and saved.get("status") == "SUCCESS":
                result = ChunkResult(chunk_id, "SUCCESS", output=saved.get("output"))
                results[chunk_id] = result
                outputs[chunk_id] = result.output
                pending.discard(chunk_id)

        while pending:
            ready = [
                chunk_id for chunk_id in chunks
                if chunk_id in pending
                and all(dep in results and results[dep].status == "SUCCESS"
                        for dep in deps.get(chunk_id, []))
            ]

            if not ready:
                blocked = sorted(pending)
                for chunk_id in blocked:
                    results[chunk_id] = ChunkResult(
                        chunk_id, "FAILED", error="dependency not satisfied"
                    )
                    self.store.set(
                        self._key(run_id, chunk_id),
                        {"status": "FAILED", "error": "dependency not satisfied"},
                    )
                    self.audit.record(
                        "pipeline.chunk.blocked",
                        {"run_id": run_id, "chunk_id": chunk_id},
                    )
                break

            def one(chunk_id: str) -> ChunkResult:
                self.audit.record(
                    "pipeline.chunk.started",
                    {"run_id": run_id, "chunk_id": chunk_id,
                     "dependencies": deps.get(chunk_id, [])},
                )
                try:
                    dependency_outputs = {
                        dep: outputs[dep] for dep in deps.get(chunk_id, [])
                    }
                    result = execute(chunk_id, dependency_outputs)
                    if not verify(chunk_id, result):
                        raise RuntimeError("chunk independent verification failed")
                    self.store.set(
                        self._key(run_id, chunk_id),
                        {"status": "SUCCESS", "output": result},
                    )
                    self.audit.record(
                        "pipeline.chunk.verified",
                        {"run_id": run_id, "chunk_id": chunk_id},
                    )
                    return ChunkResult(chunk_id, "SUCCESS", output=result)
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

            with ThreadPoolExecutor(max_workers=min(max_workers, len(ready))) as pool:
                futures = {pool.submit(one, chunk_id): chunk_id for chunk_id in ready}
                for future in as_completed(futures):
                    result = future.result()
                    results[result.chunk_id] = result
                    pending.discard(result.chunk_id)
                    if result.status == "SUCCESS":
                        outputs[result.chunk_id] = result.output

            failed = {chunk_id for chunk_id in results
                      if results[chunk_id].status == "FAILED"}
            for chunk_id in list(pending):
                if any(dep in failed for dep in deps.get(chunk_id, [])):
                    pending.remove(chunk_id)
                    results[chunk_id] = ChunkResult(
                        chunk_id, "FAILED", error="dependency failed"
                    )
                    self.store.set(
                        self._key(run_id, chunk_id),
                        {"status": "FAILED", "error": "dependency failed"},
                    )
                    self.audit.record(
                        "pipeline.chunk.blocked",
                        {"run_id": run_id, "chunk_id": chunk_id,
                         "reason": "dependency failed"},
                    )

        return [results[chunk_id] for chunk_id in chunks]


__all__ = ["ChunkResult", "ParallelChunkRunner"]
