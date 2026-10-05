from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import inspect
import uuid
from typing import Any, Callable

from .audit_chain import AuditChain
from .persistent_state import SQLiteStateStore
from .lease import TaskLease


@dataclass(frozen=True)
class ChunkResult:
    chunk_id: str
    status: str
    output: Any = None
    error: str | None = None


class ParallelChunkRunner:
    """Bounded dependency-aware runner with durable, resumable checkpoints."""

    def __init__(self, store: SQLiteStateStore, audit: AuditChain, lease: TaskLease | None = None) -> None:
        self.store = store
        self.audit = audit
        self.lease = lease or TaskLease(store, audit)

    def _key(self, run_id: str, chunk_id: str) -> str:
        return f"pipeline.chunk:{run_id}:{chunk_id}"

    @staticmethod
    def _accepts_dependencies(execute: Callable[..., Any]) -> bool:
        """Preserve the original execute(chunk) API while supporting execute(chunk, deps)."""
        try:
            signature = inspect.signature(execute)
            parameters = list(signature.parameters.values())
            if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in parameters):
                return True
            positional = [
                p for p in parameters
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            return len(positional) >= 2
        except (TypeError, ValueError):
            return True

    def run(
        self,
        run_id: str,
        chunks: list[str],
        execute: Callable[..., Any],
        verify: Callable[[str, Any], bool],
        *,
        dependencies: dict[str, list[str]] | None = None,
        max_workers: int = 4,
        lease_ttl_seconds: float = 300.0,
    ) -> list[ChunkResult]:
        if not run_id:
            raise ValueError("run_id is required")
        if not chunks:
            return []
        if len(set(chunks)) != len(chunks):
            raise ValueError("chunk ids must be unique")
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be positive")
        owner = f"parallel-runner:{uuid.uuid4().hex}"

        deps = dependencies or {}
        known = set(chunks)
        for chunk_id, required in deps.items():
            if chunk_id not in known:
                raise ValueError(f"dependency declared for unknown chunk: {chunk_id}")
            if chunk_id in required:
                raise ValueError(f"chunk cannot depend on itself: {chunk_id}")
            if any(dep not in known for dep in required):
                raise ValueError(f"unknown dependency for chunk: {chunk_id}")

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

        accepts_dependencies = self._accepts_dependencies(execute)

        while pending:
            ready = [
                chunk_id for chunk_id in chunks
                if chunk_id in pending
                and all(dep in results and results[dep].status == "SUCCESS"
                        for dep in deps.get(chunk_id, []))
            ]
            if not ready:
                for chunk_id in sorted(pending):
                    results[chunk_id] = ChunkResult(
                        chunk_id, "FAILED", error="dependency not satisfied"
                    )
                    self.store.set(
                        self._key(run_id, chunk_id),
                        {"status": "FAILED", "error": "dependency not satisfied"},
                    )
                    self.audit.record("pipeline.chunk.blocked",
                                      {"run_id": run_id, "chunk_id": chunk_id})
                break

            def one(chunk_id: str) -> ChunkResult:
                task_id = f"{run_id}:{chunk_id}"
                lease_result = self.lease.acquire(task_id, owner, ttl_seconds=lease_ttl_seconds)
                if not lease_result.acquired:
                    error = "chunk lease not acquired"
                    self.audit.record("pipeline.chunk.lease_denied", {"run_id": run_id, "chunk_id": chunk_id})
                    return ChunkResult(chunk_id, "FAILED", error=error)

                self.audit.record(
                    "pipeline.chunk.started",
                    {"run_id": run_id, "chunk_id": chunk_id,
                     "dependencies": deps.get(chunk_id, [])},
                )
                try:
                    dependency_outputs = {dep: outputs[dep] for dep in deps.get(chunk_id, [])}
                    result = execute(chunk_id, dependency_outputs) if accepts_dependencies else execute(chunk_id)
                    if not verify(chunk_id, result):
                        raise RuntimeError("chunk independent verification failed")
                    if not self.lease.is_owned(task_id, owner):
                        raise RuntimeError("chunk lease lost before commit")
                    self.store.set(self._key(run_id, chunk_id), {"status": "SUCCESS", "output": result})
                    self.audit.record("pipeline.chunk.verified", {"run_id": run_id, "chunk_id": chunk_id})
                    return ChunkResult(chunk_id, "SUCCESS", output=result)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    if self.lease.is_owned(task_id, owner):
                        self.store.set(self._key(run_id, chunk_id), {"status": "FAILED", "error": error})
                    self.audit.record("pipeline.chunk.failed", {"run_id": run_id, "chunk_id": chunk_id, "error": error})
                    return ChunkResult(chunk_id, "FAILED", error=error)
                finally:
                    self.lease.release(task_id, owner)

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
