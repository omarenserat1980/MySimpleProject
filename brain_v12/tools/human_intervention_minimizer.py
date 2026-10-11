#!/usr/bin/env python3
"""Minimize human intervention by applying only safe, pre-authorized local repairs.

This tool diagnoses the Electronic Brain runner/boot blockers. It can create a
fresh side-by-side checkout when the current checkout has diverged, but it never
overwrites a working tree, creates credentials, writes GitHub secrets, fabricates
signed execution contracts, grants permissions, provisions paid cloud resources,
or claims a Windows boot without guest evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_URL = "https://github.com/omarenserat1980/MySimpleProject.git"
SECRET_TOOL = "scripts/github/create_runner_watch_secret.sh"
DEFAULT_CLEAN_DIR = Path.home() / "MySimpleProject-main-clean"


def _run(args: list[str], cwd: Path | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, check=False)


def inspect_checkout(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path), "is_git_repo": False, "remote_ok": False,
        "branch": None, "head": None, "origin_main": None,
        "diverged": None, "secret_tool_present": False,
        "safe_actions": [], "human_required": [],
    }
    if not path.exists() or not (path / ".git").exists():
        result["human_required"].append("CHECKOUT_NOT_FOUND_OR_NOT_GIT")
        return result
    result["is_git_repo"] = True
    remote = _run(["git", "remote", "get-url", "origin"], path)
    result["remote_ok"] = remote.returncode == 0 and remote.stdout.strip().rstrip("/") in {
        REPO_URL, REPO_URL.removesuffix(".git"), "git@github.com:omarenserat1980/MySimpleProject.git"
    }
    if not result["remote_ok"]:
        result["human_required"].append("ORIGIN_REPOSITORY_NOT_CONFIRMED")
        return result
    branch = _run(["git", "branch", "--show-current"], path)
    head = _run(["git", "rev-parse", "HEAD"], path)
    status = _run(["git", "status", "--porcelain"], path)
    result["branch"] = branch.stdout.strip() if branch.returncode == 0 else None
    result["head"] = head.stdout.strip() if head.returncode == 0 else None
    result["working_tree_dirty"] = bool(status.stdout.strip())
    result["secret_tool_present"] = (path / SECRET_TOOL).is_file()

    fetch = _run(["git", "fetch", "--quiet", "origin", "main"], path, timeout=45)
    if fetch.returncode != 0:
        result["human_required"].append("GIT_FETCH_FAILED_CHECK_NETWORK_OR_AUTH")
    else:
        remote_head = _run(["git", "rev-parse", "origin/main"], path)
        counts = _run(["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"], path)
        result["origin_main"] = remote_head.stdout.strip() if remote_head.returncode == 0 else None
        if counts.returncode == 0:
            parts = counts.stdout.split()
            ahead, behind = (int(parts[0]), int(parts[1])) if len(parts) == 2 else (0, 0)
            result["ahead_by"], result["behind_by"] = ahead, behind
            result["diverged"] = ahead > 0 and behind > 0
            if result["diverged"]:
                result["safe_actions"].append("CREATE_SIDE_BY_SIDE_CLEAN_CHECKOUT")
            elif behind > 0 and not result["working_tree_dirty"]:
                result["safe_actions"].append("FAST_FORWARD_UPDATE_POSSIBLE")
            elif behind > 0 and result["working_tree_dirty"]:
                result["human_required"].append("DIRTY_CHECKOUT_NOT_AUTO_UPDATED")
    if not result["secret_tool_present"]:
        result["safe_actions"].append("FETCH_TOOL_FROM_CLEAN_CHECKOUT")
    result["human_required"].extend([
        "OWNER_AUTHORIZED_RUNNER_READ_TOKEN_AND_ACTIONS_SECRET_WRITE",
        "REAL_CONTROL_PLANE_ISSUED_SIGNED_WINDOWS_EXECUTION_CONTRACT",
        "TRUSTED_RUNNER_ONLINE_AND_REAL_GUEST_BOOT_EVIDENCE",
    ])
    result["safe_actions"] = list(dict.fromkeys(result["safe_actions"]))
    result["human_required"] = list(dict.fromkeys(result["human_required"]))
    return result


def create_clean_checkout(destination: Path) -> dict[str, Any]:
    if destination.exists():
        return {"action": "CREATE_SIDE_BY_SIDE_CLEAN_CHECKOUT", "status": "SKIPPED",
                "reason": "DESTINATION_ALREADY_EXISTS", "path": str(destination)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    proc = _run(["git", "clone", "--branch", "main", "--single-branch", REPO_URL, str(destination)], timeout=120)
    if proc.returncode != 0:
        return {"action": "CREATE_SIDE_BY_SIDE_CLEAN_CHECKOUT", "status": "FAILED",
                "reason": "GIT_CLONE_FAILED", "exit_code": proc.returncode}
    tool_exists = (destination / SECRET_TOOL).is_file()
    return {"action": "CREATE_SIDE_BY_SIDE_CLEAN_CHECKOUT",
            "status": "SUCCESS" if tool_exists else "INCOMPLETE",
            "path": str(destination), "secret_tool_present": tool_exists,
            "head": _run(["git", "rev-parse", "HEAD"], destination).stdout.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Existing checkout to inspect")
    parser.add_argument("--repair-safe", action="store_true",
                        help="Create a separate clean main checkout only when divergence/missing tool warrants it")
    parser.add_argument("--destination", type=Path, default=DEFAULT_CLEAN_DIR,
                        help="New checkout destination; an existing destination is never overwritten")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    report = inspect_checkout(args.repo.resolve())
    actions: list[dict[str, Any]] = []
    if args.repair_safe and (
        report.get("diverged") is True or report.get("secret_tool_present") is False
    ):
        actions.append(create_clean_checkout(args.destination.expanduser().resolve()))
    report["auto_repair_results"] = actions
    report["decision"] = "HUMAN_INTERVENTION_REQUIRED" if report["human_required"] else "AUTONOMOUS"
    report["safety_rule"] = "Never create credentials/contracts, change permissions, or claim real boot without evidence."
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if not any(x.get("status") == "FAILED" for x in actions) else 2


if __name__ == "__main__":
    raise SystemExit(main())
