"""Brain self-monitor: read-only health/evidence checks for the Brain runtime."""
from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


class BrainSelfMonitor:
    """Inspect repository layout without mutating files or runtime state.

    The app passes its own brain_v12 directory as root, while other callers
    may pass the repository root. Normalize both layouts to canonical paths.
    """

    def __init__(self, root=None):
        requested = Path(root or os.getcwd()).expanduser().resolve()
        if requested.name == "brain_v12" and (requested / "brain").is_dir():
            self.app_root = requested
            self.repo_root = requested.parent
            self.root_mode = "application_root"
        elif (requested / "brain_v12").is_dir():
            self.repo_root = requested
            self.app_root = requested / "brain_v12"
            self.root_mode = "repository_root"
        else:
            # Preserve an honest degraded result for unexpected layouts.
            self.repo_root = requested
            self.app_root = requested / "brain_v12"
            self.root_mode = "unknown_root"

    def _check(self, name, fn):
        try:
            value = fn()
            return {"name": name, "ok": bool(value), "detail": value}
        except Exception as exc:
            # This snapshot is exposed by an unauthenticated read-only route;
            # never include exception text that may contain local paths.
            return {
                "name": name,
                "ok": False,
                "detail": "CHECK_FAILED",
                "error_type": type(exc).__name__,
            }

    def _is_git_repository(self):
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(self.repo_root),
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def snapshot(self):
        checks = [
            self._check("brain_root", lambda: self.app_root.is_dir()),
            self._check("brain_git", lambda: (self.app_root / "brain_git").is_dir()),
            self._check(
                "supervisor",
                lambda: (self.app_root / "brain" / "brain_supervisor.py").is_file(),
            ),
            self._check("git_repository", self._is_git_repository),
        ]
        ok = all(item["ok"] for item in checks)
        now = time.time()
        return {
            "ok": ok,
            "status": "HEALTHY" if ok else "DEGRADED",
            "timestamp": now,
            "observed_at_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            # Do not disclose absolute server filesystem paths in API output.
            "root_mode": self.root_mode,
            "checks": checks,
        }
