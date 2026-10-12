#!/usr/bin/env python3
"""Brain Merge Request Executor: guarded GitHub PR merge through the existing Brain pipeline.

Safe by default: without --execute this tool only evaluates and reports readiness.
It never bypasses branch protection, required checks, reviews, or GitHub permissions.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class MergeGateError(RuntimeError):
    pass


def gh_json(args: list[str]) -> Any:
    proc = subprocess.run(["gh", *args], text=True, capture_output=True, check=False)
    if proc.returncode:
        raise MergeGateError(proc.stderr.strip() or proc.stdout.strip() or "GH_COMMAND_FAILED")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise MergeGateError("GH_INVALID_JSON") from exc


def run_gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], text=True, capture_output=True, check=False)
    if proc.returncode:
        raise MergeGateError(proc.stderr.strip() or proc.stdout.strip() or "GH_COMMAND_FAILED")
    return proc.stdout.strip()


def evaluate(pr: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pr.get("state") != "OPEN":
        blockers.append("PR_NOT_OPEN")
    if pr.get("isDraft"):
        blockers.append("PR_IS_DRAFT")
    if pr.get("mergeable") != "MERGEABLE":
        blockers.append("PR_NOT_CONFIRMED_MERGEABLE")
    if pr.get("reviewDecision") != "APPROVED":
        blockers.append("REVIEW_NOT_APPROVED")

    checks = pr.get("statusCheckRollup") or []
    if not checks:
        blockers.append("NO_CHECK_EVIDENCE")
    else:
        for check in checks:
            state = check.get("conclusion") or check.get("state")
            name = check.get("name") or check.get("context") or "unnamed-check"
            if state not in ("SUCCESS", "success"):
                blockers.append(f"CHECK_NOT_SUCCESS:{name}:{state or 'UNKNOWN'}")
    return blockers


def audit(record: dict[str, Any], path: str | None) -> None:
    line = json.dumps(record, sort_keys=True)
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", help="Pull request number or URL")
    parser.add_argument("--repo", default=os.getenv("GH_REPO"), help="owner/repo; defaults to current gh repository")
    parser.add_argument("--method", choices=("squash", "merge", "rebase"), default="squash")
    parser.add_argument("--execute", action="store_true", help="Actually merge after every gate passes; default is dry-run")
    parser.add_argument("--expected-head", help="Optional expected PR head SHA; abort if the head differs")
    parser.add_argument("--audit-file", default="brain6_artifacts/merge_requests/audit.jsonl")
    args = parser.parse_args()

    view_args = ["pr", "view", args.pr, "--json",
                 "number,title,state,isDraft,mergeable,mergeStateStatus,reviewDecision,headRefOid,baseRefName,statusCheckRollup,url"]
    if args.repo:
        view_args += ["--repo", args.repo]

    try:
        pr = gh_json(view_args)
        blockers = evaluate(pr)
        head = pr.get("headRefOid")
        if args.expected_head and head != args.expected_head:
            blockers.append("EXPECTED_HEAD_SHA_MISMATCH")

        record: dict[str, Any] = {
            "schema": "brain.merge-request.v1",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repository": args.repo,
            "pr_number": pr.get("number"),
            "url": pr.get("url"),
            "title": pr.get("title"),
            "head_sha": head,
            "base_branch": pr.get("baseRefName"),
            "method": args.method,
            "mode": "execute" if args.execute else "dry_run",
            "ready": not blockers,
            "blockers": blockers,
            "merged": False,
        }

        if blockers:
            record["status"] = "BLOCKED"
            audit(record, args.audit_file)
            return 2

        if not args.execute:
            record["status"] = "READY_DRY_RUN"
            audit(record, args.audit_file)
            return 0

        latest = gh_json(view_args)
        latest_blockers = evaluate(latest)
        if latest.get("headRefOid") != head:
            latest_blockers.append("HEAD_CHANGED_BEFORE_MERGE")
        if latest_blockers:
            record.update(status="BLOCKED_ON_RECHECK", ready=False, blockers=latest_blockers)
            audit(record, args.audit_file)
            return 2

        merge_args = ["pr", "merge", args.pr, f"--{args.method}"]
        if args.repo:
            merge_args += ["--repo", args.repo]
        run_gh(merge_args)

        verify_args = ["pr", "view", args.pr, "--json", "state,mergedAt,mergeCommit,url"]
        if args.repo:
            verify_args += ["--repo", args.repo]
        verified = gh_json(verify_args)
        record["postcondition"] = verified
        record["merged"] = verified.get("state") == "MERGED" or bool(verified.get("mergedAt"))
        record["status"] = "MERGED_VERIFIED" if record["merged"] else "MERGE_NOT_VERIFIED"
        audit(record, args.audit_file)
        return 0 if record["merged"] else 3
    except MergeGateError as exc:
        audit({
            "schema": "brain.merge-request.v1",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ERROR",
            "error": str(exc),
            "merged": False,
        }, args.audit_file)
        return 4


if __name__ == "__main__":
    sys.exit(main())
