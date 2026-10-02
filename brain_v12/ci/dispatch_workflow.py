#!/usr/bin/env python3
"""Brain Cloud workflow_dispatch client.

Requires GITHUB_TOKEN (or GH_TOKEN) with Actions write permission.
This is the direct Brain-side bridge for GitHub Actions workflow_dispatch.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request


# Explicit Brain-owned workflow allowlist. ChatGPT may select only these IDs.
ALLOWED_WORKFLOWS = {
    "brain-reasoning-loop": ".github/workflows/brain-reasoning-loop.yml",
    "reflection-e2e": ".github/workflows/reflection-e2e.yml",
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--workflow", required=True, choices=sorted(ALLOWED_WORKFLOWS))
    p.add_argument("--ref", default="main")
    p.add_argument("--input", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--wait", action="store_true", help="Wait for a newly dispatched run to complete.")
    p.add_argument("--wait-timeout", type=int, default=600)
    p.add_argument("--poll-seconds", type=int, default=10)
    args = p.parse_args()

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN_OR_GH_TOKEN_REQUIRED", file=sys.stderr)
        return 2

    workflow_file = ALLOWED_WORKFLOWS[args.workflow]
    url = f"https://api.github.com/repos/{args.repo}/actions/workflows/{workflow_file}/dispatches"
    inputs = {}
    for raw in args.input:
        if "=" not in raw:
            print(f"INVALID_INPUT: {raw}", file=sys.stderr)
            return 2
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            print(f"INVALID_INPUT_KEY: {raw}", file=sys.stderr)
            return 2
        inputs[key] = value
    payload = {"ref": args.ref, "inputs": inputs}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "Brain-Cloud-Workflow-Dispatcher",
        },
    )
    dispatch_started = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (201, 204):
                print(f"WORKFLOW_DISPATCH_FAILED_HTTP_{resp.status}", file=sys.stderr)
                return 1
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        print(f"WORKFLOW_DISPATCH_FAILED_HTTP_{exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"WORKFLOW_DISPATCH_NETWORK_ERROR: {exc}", file=sys.stderr)
        return 1

    print("WORKFLOW_DISPATCH=SUCCESS")
    print(f"REPOSITORY={args.repo}")
    print(f"WORKFLOW_ID={args.workflow}")
    print(f"WORKFLOW_FILE={workflow_file}")
    print(f"REF={args.ref}")
    for key, value in inputs.items():
        print(f"INPUT_{key}={value}")

    if not args.wait:
        return 0

    if args.wait_timeout < 1 or args.poll_seconds < 1:
        print("INVALID_WAIT_CONFIGURATION", file=sys.stderr)
        return 2

    deadline = time.monotonic() + args.wait_timeout
    runs_url = (
        f"https://api.github.com/repos/{args.repo}/actions/workflows/"
        f"{workflow_file}/runs?branch={args.ref}&per_page=10"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Brain-Cloud-Workflow-Dispatcher",
    }

    while time.monotonic() < deadline:
        try:
            poll_req = urllib.request.Request(runs_url, method="GET", headers=headers)
            with urllib.request.urlopen(poll_req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            print(f"WORKFLOW_MONITOR_POLL_ERROR: {exc}", file=sys.stderr)
            time.sleep(args.poll_seconds)
            continue

        candidates = []
        for run in data.get("workflow_runs", []):
            created = run.get("created_at", "")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if created_dt >= dispatch_started:
                        candidates.append(run)
                except ValueError:
                    pass

        if candidates:
            run = sorted(candidates, key=lambda x: x.get("created_at", ""), reverse=True)[0]
            run_id = run.get("id")
            status = run.get("status")
            conclusion = run.get("conclusion")
            print(f"WORKFLOW_RUN_ID={run_id}")
            print(f"WORKFLOW_RUN_STATUS={status}")
            print(f"WORKFLOW_RUN_CONCLUSION={conclusion}")
            if status == "completed":
                if conclusion == "success":
                    print("WORKFLOW_MONITOR=SUCCESS")
                    return 0
                print("WORKFLOW_MONITOR=FAILED")
                return 1

        time.sleep(args.poll_seconds)

    print("WORKFLOW_MONITOR=TIMEOUT", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
