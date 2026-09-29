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
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--workflow", required=True)
    p.add_argument("--ref", default="main")
    p.add_argument("--brain-command", default=r"\AUTO1000")
    p.add_argument("--auto-confirm", default="true")
    args = p.parse_args()

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN_OR_GH_TOKEN_REQUIRED", file=sys.stderr)
        return 2

    url = f"https://api.github.com/repos/{args.repo}/actions/workflows/{args.workflow}/dispatches"
    payload = {
        "ref": args.ref,
        "inputs": {
            "brain_command": args.brain_command,
            "auto_confirm": args.auto_confirm.lower(),
        },
    }
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
    print(f"WORKFLOW={args.workflow}")
    print(f"REF={args.ref}")
    print(f"BRAIN_COMMAND={args.brain_command}")
    print(f"AUTO_CONFIRM={args.auto_confirm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
