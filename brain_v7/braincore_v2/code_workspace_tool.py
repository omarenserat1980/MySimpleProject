"""Controlled code workspace tool for the Electronic Brain.

The tool gives the brain a bounded ability to inspect, save, validate, and
apply source-code changes inside an explicitly configured workspace.

It does not store credentials, push to remote repositories, delete arbitrary
files, or execute shell commands supplied by a task. Writes are atomic and
Python changes are syntax-checked before a successful result is returned.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import os
import py_compile
import tempfile
from typing import Iterable, Mapping


PROTECTED_NAMES = {
    ".env", ".env.local", ".env.production",
    "credentials.json", "secrets.json",
}


@dataclass(frozen=True)
class CodeChange:
    path: str
    content: str
    reason: str = ""


@dataclass(frozen=True)
class ChangeResult:
    path: str
    status: str
    old_sha256: str
    new_sha256: str
    backup_path: str = ""
    error: str = ""


class CodeWorkspaceTool:
    """Bounded source-code persistence and change executor."""

    def __init__(self, root: str | Path | None = None, *, backup_dir: str = ".brain_backups") -> None:
        configured = root or os.getenv("BRAIN_CODE_ROOT") or os.getcwd()
        self.root = Path(configured).resolve()
        self.backup_dir = self.root / backup_dir
        self.audit: list[ChangeResult] = []

    def _safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("path escapes configured code workspace")
        rel_parts = Path(relative).parts
        if any(part in PROTECTED_NAMES for part in rel_parts):
            raise PermissionError("protected credential file")
        if candidate == self.backup_dir or self.backup_dir in candidate.parents:
            raise PermissionError("backup area is not editable")
        return candidate

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def read(self, relative: str) -> str:
        path = self._safe_path(relative)
        return path.read_text(encoding="utf-8")

    def plan(self, changes: Iterable[CodeChange]) -> list[dict]:
        planned = []
        for change in changes:
            path = self._safe_path(change.path)
            old = path.read_bytes() if path.exists() else b""
            planned.append({
                "path": change.path,
                "exists": path.exists(),
                "old_sha256": self._sha256(old),
                "new_sha256": self._sha256(change.content.encode("utf-8")),
                "reason": change.reason,
            })
        return planned

    def apply(self, changes: Iterable[CodeChange], *, validate_python: bool = True) -> list[ChangeResult]:
        changes = list(changes)
        results: list[ChangeResult] = []
        written: list[tuple[Path, bytes | None]] = []
        try:
            for change in changes:
                path = self._safe_path(change.path)
                old = path.read_bytes() if path.exists() else None
                new = change.content.encode("utf-8")
                if old == new:
                    result = ChangeResult(change.path, "UNCHANGED", self._sha256(new), self._sha256(new))
                    results.append(result)
                    continue

                path.parent.mkdir(parents=True, exist_ok=True)
                backup_path = ""
                if old is not None:
                    self.backup_dir.mkdir(parents=True, exist_ok=True)
                    digest = self._sha256(old)[:12]
                    backup = self.backup_dir / f"{path.name}.{digest}.bak"
                    backup.write_bytes(old)
                    backup_path = str(backup.relative_to(self.root))

                with tempfile.NamedTemporaryFile(
                    "wb", delete=False, dir=str(path.parent),
                    prefix=f".{path.name}.", suffix=".tmp",
                ) as handle:
                    handle.write(new)
                    temp_name = handle.name
                os.replace(temp_name, path)
                written.append((path, old))

                results.append(ChangeResult(
                    change.path, "APPLIED",
                    self._sha256(old or b""),
                    self._sha256(new),
                    backup_path,
                ))

            if validate_python:
                self._validate_python([r.path for r in results if r.status == "APPLIED"])

            self.audit.extend(results)
            return results
        except Exception as exc:
            for path, old in reversed(written):
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(old)
            failed = ChangeResult(
                "<transaction>", "ROLLED_BACK", "", "", error=str(exc)
            )
            self.audit.extend(results + [failed])
            raise

    def _validate_python(self, paths: Iterable[str]) -> None:
        for relative in paths:
            if not relative.endswith(".py"):
                continue
            path = self._safe_path(relative)
            py_compile.compile(str(path), doraise=True)

    def snapshot(self) -> dict:
        return {
            "workspace": str(self.root),
            "backup_dir": str(self.backup_dir),
            "audit_entries": len(self.audit),
            "protected_files": sorted(PROTECTED_NAMES),
            "atomic_writes": True,
            "python_validation": True,
            "remote_push": False,
            "credential_storage": False,
            "shell_command_execution": False,
            "last_changes": [asdict(x) for x in self.audit[-20:]],
        }
