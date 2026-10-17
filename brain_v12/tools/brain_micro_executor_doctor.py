#!/usr/bin/env python3
"""Read-only preflight for the Brain Micro-Executor.

This tool is deliberately diagnostic-only: it does not register a device worker,
poll tasks, execute jobs, modify configuration, or contact a remote service.
It helps replace repeated Desktop Commander inspections with a local Termux run.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path


REQUIRED_PATHS = (
    "brain_v12/app.py",
    "brain_v12/tools/brain_runtime_launcher.sh",
)

OPTIONAL_PATHS = (
    "brain_v12/tools/brain_device_bridge_doctor.py",
    "brain_v12/docs/SOFTWARE_ONLY_NODES.md",
)


def find_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() and (candidate / "brain_v12").is_dir():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="repository root (auto-detected by default)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve() if args.root else find_root(Path.cwd().resolve())
    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    record("python", sys.version_info >= (3, 10), platform.python_version())
    record("android_termux", "com.termux" in os.environ.get("PREFIX", ""),
           "Termux detected" if "com.termux" in os.environ.get("PREFIX", "") else "not detected (desktop/CI is allowed)")
    record("repository_root", root is not None and root.is_dir(),
           str(root) if root else "not found; run from inside the repository or pass --root")

    if root:
        for relative in REQUIRED_PATHS:
            path = root / relative
            record("required_file:" + relative, path.is_file(), "present" if path.is_file() else "missing")

        for relative in OPTIONAL_PATHS:
            path = root / relative
            # Optional compatibility/documentation files may differ between local
            # checkouts and cloud branches; report without failing the preflight.
            record("optional_file:" + relative, True,
                   "present" if path.is_file() else "absent (informational; not required)")

        git_dir = root / ".git"
        if git_dir.is_file():
            record("git_worktree", True, "worktree .git file detected")
        elif git_dir.is_dir():
            record("git_worktree", True, "repository .git directory detected")

    summary = {
        "component": "BRAIN_MICRO_EXECUTOR_DOCTOR",
        "mode": "READ_ONLY",
        "task_polling": False,
        "worker_registration": False,
        "remote_requests": False,
        "configuration_changes": False,
        "checks_passed": sum(bool(item["ok"]) for item in checks),
        "checks_total": len(checks),
        "checks": checks,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print("BRAIN MICRO-EXECUTOR DOCTOR — READ ONLY")
        print("No task polling, worker registration, remote requests, or configuration changes.")
        for item in checks:
            label = "PASS" if item["ok"] else ("INFO" if item["name"].startswith("optional_file:") else "FAIL")
            print(f'{label} {item["name"]}: {item["detail"]}')
        print(f'CHECKS: {summary["checks_passed"]}/{summary["checks_total"]} passed')
        print("NOTE: this preflight is not proof of Android virtualization or real device execution.")

    # Termux detection and optional files are informational. Required runtime files
    # must exist, otherwise callers should treat this preflight as failed.
    required_files_ok = root is not None and all((root / relative).is_file() for relative in REQUIRED_PATHS)
    return 0 if sys.version_info >= (3, 10) and root is not None and required_files_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
