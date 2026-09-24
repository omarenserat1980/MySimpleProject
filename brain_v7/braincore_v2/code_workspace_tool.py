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

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        backup_dir: str = ".brain_backups",
        allowed_prefixes: Iterable[str] = (),
    ) -> None:
        configured = root or os.getenv("BRAIN_CODE_ROOT") or os.getcwd()
        self.root = Path(configured).resolve()
        self.backup_dir = self.root / backup_dir
        self.allowed_prefixes = tuple(
            p.replace("\\", "/").strip("/")+ "/" for p in allowed_prefixes if p
        )
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
        normalized = relative.replace("\\", "/").lstrip("/")
        if self.allowed_prefixes and not any(normalized.startswith(prefix) for prefix in self.allowed_prefixes):
            raise PermissionError("path is outside configured code allowlist")
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
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                raise SyntaxError(str(exc)) from exc


    def _manifest(self, paths: Iterable[str]) -> dict[str, str]:
        manifest = {}
        for relative in sorted(set(paths)):
            path = self._safe_path(relative)
            if path.exists() and path.is_file():
                manifest[relative] = self._sha256(path.read_bytes())
        return manifest

    def checkpoint(self, paths: Iterable[str] = ()) -> dict:
        """Create a restorable file snapshot with a tamper-evident manifest."""
        import json
        import time
        requested = list(paths)
        if not requested:
            requested = [
                str(p.relative_to(self.root))
                for p in self.root.rglob("*")
                if p.is_file() and self.backup_dir not in p.parents
                and (not self.allowed_prefixes or any(str(p.relative_to(self.root)).replace('\\\\','/').startswith(prefix) for prefix in self.allowed_prefixes))
            ]
        manifest = self._manifest(requested)
        payload = json.dumps(manifest, sort_keys=True).encode("utf-8")
        manifest_hash = self._sha256(payload)
        checkpoint_id = "cp-" + manifest_hash[:16]
        target = self.backup_dir / checkpoint_id
        target.mkdir(parents=True, exist_ok=True)
        (target / "manifest.json").write_bytes(payload)
        for relative in manifest:
            source = self._safe_path(relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        return {
            "checkpoint_id": checkpoint_id,
            "files": sorted(manifest),
            "manifest_sha256": manifest_hash,
            "created_at": time.time(),
        }

    def dry_run(self, changes: Iterable[CodeChange], *, validate_python: bool = True) -> dict:
        """Preview and validate changes without modifying source files."""
        changes = list(changes)
        planned = self.plan(changes)
        if validate_python:
            import ast
            for change in changes:
                if change.path.endswith(".py"):
                    ast.parse(change.content, filename=change.path)
        return {"status": "VALID", "changes": planned, "writes": 0}

    def diff(self, changes: Iterable[CodeChange]) -> list[dict]:
        """Return unified diffs before applying changes."""
        import difflib
        output = []
        for change in changes:
            path = self._safe_path(change.path)
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            lines = list(difflib.unified_diff(
                old.splitlines(), change.content.splitlines(),
                fromfile="a/" + change.path, tofile="b/" + change.path, lineterm=""
            ))
            output.append({"path": change.path, "changed": bool(lines), "diff": lines})
        return output

    def restore(self, checkpoint_id: str) -> list[ChangeResult]:
        """Restore the files recorded by a checkpoint."""
        import json
        if not checkpoint_id.startswith("cp-") or "/" in checkpoint_id or "\\" in checkpoint_id:
            raise ValueError("invalid checkpoint")
        target = self.backup_dir / checkpoint_id
        manifest_path = target / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("checkpoint manifest not found")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        changes = []
        for relative in manifest:
            source = target / relative
            changes.append(CodeChange(
                relative,
                source.read_text(encoding="utf-8"),
                "checkpoint restore",
            ))
        return self.apply(changes)

    def verify(self, paths: Iterable[str] = ()) -> dict:
        """Verify readability and Python syntax without changing files."""
        selected = list(paths)
        if not selected:
            selected = [
                str(p.relative_to(self.root))
                for p in self.root.rglob("*.py")
                if self.backup_dir not in p.parents
                and (not self.allowed_prefixes or any(str(p.relative_to(self.root)).replace('\\\\','/').startswith(prefix) for prefix in self.allowed_prefixes))
            ]
        errors = []
        checked = 0
        for relative in selected:
            try:
                path = self._safe_path(relative)
                if not path.exists():
                    errors.append({"path": relative, "error": "missing"})
                    continue
                if relative.endswith(".py"):
                    import ast
                    ast.parse(path.read_text(encoding="utf-8"), filename=relative)
                checked += 1
            except Exception as exc:
                errors.append({"path": relative, "error": str(exc)})
        return {"status": "PASS" if not errors else "FAIL", "checked": checked, "errors": errors}

    def snapshot(self) -> dict:
        return {
            "workspace": str(self.root),
            "backup_dir": str(self.backup_dir),
            "audit_entries": len(self.audit),
            "protected_files": sorted(PROTECTED_NAMES),
            "allowed_prefixes": list(self.allowed_prefixes),
            "atomic_writes": True,
            "python_validation": True,
            "remote_push": False,
            "credential_storage": False,
            "shell_command_execution": False,
            "last_changes": [asdict(x) for x in self.audit[-20:]],
        }
