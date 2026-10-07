"""Bounded source explorer for Brain Habitat."""
from __future__ import annotations

from pathlib import Path


class SourceExplorer:
    DEFAULT_EXTENSIONS = {".py", ".kt", ".java", ".json", ".yaml", ".yml", ".md", ".sh", ".gradle", ".xml"}

    def __init__(self, roots, max_file_bytes: int = 512_000):
        self.roots = [Path(r).resolve() for r in roots]
        self.max_file_bytes = max_file_bytes

    def _resolve(self, path: str | Path) -> Path:
        target = Path(path).resolve()
        for root in self.roots:
            try:
                target.relative_to(root)
                return target
            except ValueError:
                continue
        raise PermissionError("source path is outside registered roots")

    def list_files(self, root_index: int = 0, extensions=None, limit: int = 500) -> list[str]:
        if root_index < 0 or root_index >= len(self.roots):
            raise IndexError("invalid source root")
        allowed = set(extensions or self.DEFAULT_EXTENSIONS)
        root = self.roots[root_index]
        result = []
        for path in root.rglob("*"):
            if len(result) >= limit:
                break
            if path.is_file() and path.suffix.lower() in allowed and path.stat().st_size <= self.max_file_bytes:
                result.append(str(path))
        return sorted(result)

    def read(self, path: str | Path, max_bytes: int | None = None) -> str:
        target = self._resolve(path)
        size = target.stat().st_size
        limit = self.max_file_bytes if max_bytes is None else min(max_bytes, self.max_file_bytes)
        if size > limit:
            raise ValueError("source file exceeds read limit")
        return target.read_text(encoding="utf-8")
