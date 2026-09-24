"""Safe repository change tool for the Electronic Brain.

This module gives the brain an explicit, auditable interface for proposing,
validating, and applying code changes. It never stores credentials and it
cannot execute arbitrary shell commands.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Optional


ALLOWED_PREFIXES = ("brain_v7/braincore_v2/",)
BLOCKED_NAMES = {".env", "credentials.json", "secrets.json", "token.json"}


@dataclass(frozen=True)
class CodeChange:
    path: str
    content: str
    expected_sha256: Optional[str] = None
    reason: str = ""


@dataclass(frozen=True)
class ChangeResult:
    status: str
    path: str
    content_sha256: str
    reason: str


class CodeChangeTool:
    """Policy-aware code storage/change planner.

    The actual GitHub API call remains an integration concern. This class
    validates a proposed change and produces a deterministic change record.
    """

    def validate(self, change: CodeChange) -> None:
        path = PurePosixPath(change.path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe repository path")
        if not any(change.path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            raise ValueError("path outside brain_v7/braincore_v2 is not allowed")
        if path.name in BLOCKED_NAMES:
            raise ValueError("credential/secret files are blocked")
        if len(change.content.encode("utf-8")) > 1_000_000:
            raise ValueError("change is too large")
        if not change.reason.strip():
            raise ValueError("change reason is required")

    def fingerprint(self, content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()

    def prepare(self, change: CodeChange) -> dict:
        self.validate(change)
        digest = self.fingerprint(change.content)
        return {
            "path": change.path,
            "content_sha256": digest,
            "expected_sha256": change.expected_sha256,
            "reason": change.reason,
            "action": "UPDATE_OR_CREATE",
        }

    def result(self, change: CodeChange, status: str = "PREPARED") -> ChangeResult:
        self.validate(change)
        return ChangeResult(
            status=status,
            path=change.path,
            content_sha256=self.fingerprint(change.content),
            reason=change.reason,
        )

    def snapshot(self) -> dict:
        return {
            "allowed_prefixes": list(ALLOWED_PREFIXES),
            "blocked_names": sorted(BLOCKED_NAMES),
            "credential_storage": False,
            "arbitrary_shell_execution": False,
        }


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    action: str
    message: str
    commit_sha: Optional[str] = None
    output: str = ""


class WorkspaceCodeExecutor(CodeChangeTool):
    """Execute validated changes inside a configured local Git workspace.

    The brain may write code, run an allowlisted test command, commit the
    result, and optionally push through the workspace's preconfigured Git
    remote. Credentials are never read, printed, or stored by this class.
    """

    ALLOWED_TESTS = (
        ("pytest", "python -m pytest -q"),
        ("compile", "python -m compileall -q brain_v7"),
    )

    def __init__(self, repo_root: str):
        import subprocess
        from pathlib import Path
        self.repo_root = Path(repo_root).resolve()
        self.repo = self.repo_root
        self._subprocess = subprocess

    def _safe_path(self, relative: str):
        from pathlib import Path, PurePosixPath
        rel = PurePosixPath(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("unsafe repository path")
        path = (self.repo_root / Path(*rel.parts)).resolve()
        if self.repo_root not in path.parents and path != self.repo_root:
            raise ValueError("path escapes repository")
        if rel.name in BLOCKED_NAMES:
            raise ValueError("credential/secret files are blocked")
        return path

    def apply(self, change: CodeChange) -> ExecutionResult:
        self.validate(change)
        path = self._safe_path(change.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(change.content, encoding="utf-8")
        return ExecutionResult(True, "write", f"wrote {change.path}")

    def run_test(self, name: str = "pytest") -> ExecutionResult:
        commands = dict(self.ALLOWED_TESTS)
        if name not in commands:
            return ExecutionResult(False, "test", "test is not allowlisted")
        proc = self._subprocess.run(
            ["bash", "-lc", commands[name]],
            cwd=self.repo_root, text=True, capture_output=True, timeout=300,
        )
        output = (proc.stdout + "\n" + proc.stderr)[-12000:]
        return ExecutionResult(
            proc.returncode == 0, "test",
            "passed" if proc.returncode == 0 else f"failed ({proc.returncode})",
            output=output,
        )

    def commit(self, message: str) -> ExecutionResult:
        if not message.strip():
            return ExecutionResult(False, "commit", "empty commit message")
        add = self._subprocess.run(
            ["git", "add", "--", "brain_v7"],
            cwd=self.repo_root, text=True, capture_output=True, timeout=60,
        )
        if add.returncode:
            return ExecutionResult(False, "commit", add.stderr.strip())
        commit = self._subprocess.run(
            ["git", "commit", "-m", message[:200]],
            cwd=self.repo_root, text=True, capture_output=True, timeout=120,
        )
        if commit.returncode:
            return ExecutionResult(False, "commit", commit.stderr.strip())
        rev = self._subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_root, text=True, capture_output=True, timeout=30,
        )
        return ExecutionResult(
            True, "commit", "committed",
            commit_sha=rev.stdout.strip() if rev.returncode == 0 else None,
        )

    def push(self) -> ExecutionResult:
        import os
        if os.getenv("BRAIN_ALLOW_GIT_PUSH", "0") != "1":
            return ExecutionResult(False, "push", "push is disabled; set BRAIN_ALLOW_GIT_PUSH=1 in the deployment environment")
        proc = self._subprocess.run(
            ["git", "push"],
            cwd=self.repo_root, text=True, capture_output=True, timeout=180,
        )
        return ExecutionResult(
            proc.returncode == 0, "push",
            "pushed" if proc.returncode == 0 else proc.stderr.strip(),
            output=(proc.stdout + "\n" + proc.stderr)[-12000:],
        )

    def execute_pipeline(self, change: CodeChange, message: str, test: str = "pytest", push: bool = False) -> dict:
        """Write -> test -> commit -> optional push; stop on the first failure."""
        applied = self.apply(change)
        if not applied.ok:
            return {"ok": False, "steps": [asdict(applied)]}
        tested = self.run_test(test)
        if not tested.ok:
            return {"ok": False, "steps": [asdict(applied), asdict(tested)]}
        committed = self.commit(message)
        if not committed.ok:
            return {"ok": False, "steps": [asdict(applied), asdict(tested), asdict(committed)]}
        steps = [asdict(applied), asdict(tested), asdict(committed)]
        if push:
            pushed = self.push()
            steps.append(asdict(pushed))
            return {"ok": pushed.ok, "steps": steps}
        return {"ok": True, "steps": steps}
