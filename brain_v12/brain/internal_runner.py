from __future__ import annotations

"""Brain-owned execution runner.

This runner is deliberately independent of GitHub Actions. GitHub may record
source, evidence and verification, but execution is owned by Brain Runtime.

The runner fails closed: it never silently falls back to a GitHub-hosted runner.
"""

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import platform
import socket
import subprocess
import time
from typing import Sequence


INTERNAL_RUNNER_ID = os.environ.get("BRAIN_INTERNAL_RUNNER_ID", socket.gethostname())
INTERNAL_RUNNER_LABELS = frozenset(
    filter(None, os.environ.get(
        "BRAIN_INTERNAL_RUNNER_LABELS",
        "brain-internal,linux,x64,qemu,windows-real-boot"
    ).split(","))
)


@dataclass(frozen=True)
class InternalRunner:
    runner_id: str = INTERNAL_RUNNER_ID
    labels: frozenset[str] = INTERNAL_RUNNER_LABELS
    state: str = "OFFLINE"
    metadata: dict[str, str] = field(default_factory=dict)

    def capabilities(self) -> set[str]:
        return {
            "brain-internal-execution",
            "windows-server-2025-real-boot",
            "qemu",
        }

    def status(self) -> dict:
        from .internal_runner_preflight import inspect_runner
        preflight = inspect_runner(self.runner_id)
        return {
            "runner_id": self.runner_id,
            "state": "ONLINE" if preflight.verified else "OFFLINE",
            "labels": sorted(self.labels),
            "capabilities": sorted(self.capabilities()),
            "host_os": platform.system(),
            "host_arch": platform.machine(),
            "python": platform.python_version(),
            "qemu": self._binary("qemu-system-x86_64"),
            "preflight": preflight.evidence(),
        }

    @staticmethod
    def _binary(name: str) -> bool:
        from shutil import which
        return which(name) is not None

    def require(self, capability: str) -> None:
        from .internal_runner_preflight import inspect_runner
        preflight = inspect_runner(self.runner_id)
        if not preflight.verified:
            raise RuntimeError("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED:" + ",".join(preflight.reasons))
        if capability not in self.capabilities():
            raise RuntimeError(f"INTERNAL_RUNNER_MISSING_CAPABILITY:{capability}")

    def run(self, argv: Sequence[str], *, cwd: str | Path | None = None,
            timeout: int = 3600) -> dict:
        if not argv:
            raise ValueError("EMPTY_COMMAND")
        started = time.time()
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "runner_id": self.runner_id,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_seconds": round(time.time() - started, 3),
        }


def write_status(path: str | Path) -> dict:
    status = InternalRunner().status()
    Path(path).write_text(
        json.dumps(status, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return status


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="+")
    parser.add_argument("--cwd")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args()

    result = InternalRunner().run(args.command, cwd=args.cwd, timeout=args.timeout)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else result["returncode"] or 1)
