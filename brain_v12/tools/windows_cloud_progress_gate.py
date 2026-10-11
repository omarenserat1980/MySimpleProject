#!/usr/bin/env python3
"""Single-pass, fail-closed progress report for Brain Windows Cloud.

Read-only: this tool does not create secrets, enroll nodes, provision VMs, or
change cloud resources. It gathers current readiness endpoints and emits the
next actionable blocker without dumping configuration or secret values.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINTS = (
    ("/api/brain/windows/cloud/readiness", "provider"),
    ("/api/brain/windows/cloud/secrets/readiness", "enrollment"),
    ("/api/brain/windows/cloud/status", "guest"),
    ("/api/brain/windows/status", "datacenter"),
)


def find_repo_root(start: Path | None = None) -> Path | None:
    """Find the checkout from cwd or this file; never assume ~/downloads is a repo."""
    candidates = [start or Path.cwd(), Path(__file__).resolve()]
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.is_file():
            candidate = candidate.parent
        for parent in (candidate, *candidate.parents):
            if (parent / ".git").exists() and (parent / "brain_v12").is_dir():
                return parent
    return None


def _get_json(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status < 200 or response.status >= 300:
                return {"http_status": response.status, "reachable": False, "reason": "HTTP_NOT_SUCCESS"}
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                return {"http_status": response.status, "reachable": True, "reason": "JSON_NOT_OBJECT"}
            return {"http_status": response.status, "reachable": True, "data": payload}
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "reachable": False, "reason": "HTTP_ERROR"}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {"http_status": None, "reachable": False, "reason": "UNREACHABLE_OR_INVALID_JSON"}


def summarize(base_url: str, results: dict[str, dict[str, Any]], repo_root: Path | None) -> dict[str, Any]:
    provider = results.get("provider", {})
    enrollment = results.get("enrollment", {})
    guest = results.get("guest", {})
    datacenter = results.get("datacenter", {})
    p = provider.get("data", {})
    e = enrollment.get("data", {})
    g = guest.get("data", {})
    d = datacenter.get("data", {})

    blockers: list[dict[str, str]] = []
    if repo_root is None:
        blockers.append({
            "code": "REPOSITORY_NOT_FOUND",
            "action": "Run from the checkout: cd ~/MySimpleProject; git pull --ff-only origin main",
        })
    if not provider.get("reachable"):
        blockers.append({
            "code": "BRAIN_API_UNREACHABLE",
            "action": "Start/verify the Brain API on port 8012, then rerun this read-only report.",
        })
    else:
        readiness = p.get("provider_readiness", {})
        if p.get("ready") is not True:
            reason = readiness.get("reason") or p.get("reason") or "PROVIDER_NOT_READY"
            blockers.append({
                "code": str(reason),
                "action": "Choose/configure an actually available provider adapter (terraform or opennebula); review cost and plan before any apply.",
            })
    if not enrollment.get("reachable"):
        blockers.append({
            "code": "ENROLLMENT_READINESS_UNREACHABLE",
            "action": "Restore the Brain API and rerun this report.",
        })
    elif e.get("ready") is not True:
        missing = e.get("missing", [])
        blockers.append({
            "code": "WINDOWS_GUEST_ENROLLMENT_NOT_READY",
            "action": "After a real Windows Server 2025 x86_64 VM exists, configure the missing enrollment/control settings via the authenticated admin flow; never invent tokens.",
            "missing": ", ".join(str(x) for x in missing) if isinstance(missing, list) else "see readiness endpoint",
        })
    if not guest.get("reachable"):
        blockers.append({
            "code": "WINDOWS_CLOUD_STATUS_UNREACHABLE",
            "action": "Restore the Brain API and rerun this report.",
        })
    elif g.get("verified") is not True:
        blockers.append({
            "code": str(g.get("status") or "WINDOWS_CLOUD_GUEST_NOT_VERIFIED"),
            "action": "Provisioning alone is insufficient: enroll the real guest and wait for a fresh authenticated heartbeat.",
        })
    if not datacenter.get("reachable"):
        blockers.append({
            "code": "DATACENTER_STATUS_UNREACHABLE",
            "action": "Restore the Brain API and rerun this report.",
        })
    elif d.get("status") == "EMPTY" or not d.get("windows_vms"):
        blockers.append({
            "code": "DATACENTER_HAS_NO_WINDOWS_VM",
            "action": "No VM is registered. Do not claim boot; complete provider and enrollment prerequisites first.",
        })

    return {
        "tool": "BRAIN_WINDOWS_CLOUD_PROGRESS_GATE",
        "mode": "READ_ONLY",
        "base_url": base_url.rstrip("/"),
        "repository_found": repo_root is not None,
        "repository_root": str(repo_root) if repo_root else None,
        "endpoints": {
            key: {
                "http_status": value.get("http_status"),
                "reachable": value.get("reachable", False),
                "status": (
                    value.get("data", {}).get("status")
                    or value.get("data", {}).get("reason")
                    or value.get("data", {}).get("provider_readiness", {}).get("reason")
                ) if isinstance(value.get("data", {}), dict) else None,
            }
            for key, value in results.items()
        },
        "blocker_count": len(blockers),
        "blockers": blockers,
        "windows_boot_proven": False,
        "security": "No secret values are read, emitted, or changed; no cloud resources are provisioned.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("BRAIN_API_URL", "http://127.0.0.1:8012"),
                        help="Brain API base URL (default: BRAIN_API_URL or localhost:8012)")
    parser.add_argument("--timeout", type=float, default=3.0, help="Per-endpoint timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")
    args = parser.parse_args(argv)
    repo_root = find_repo_root()
    results = {key: _get_json(args.base_url, path, max(0.1, args.timeout)) for path, key in ENDPOINTS}
    report = summarize(args.base_url, results, repo_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("BRAIN WINDOWS CLOUD PROGRESS GATE (READ-ONLY)")
        print(f"Repository: {report['repository_root'] or 'NOT FOUND'}")
        print(f"API: {args.base_url.rstrip('/')}")
        for name, state in report["endpoints"].items():
            print(f"{name}: HTTP {state['http_status'] if state['http_status'] is not None else 'NO RESPONSE'}; "
                  f"reachable={state['reachable']}; status={state['status'] or 'UNKNOWN'}")
        print(f"BLOCKERS={report['blocker_count']}")
        for index, blocker in enumerate(report["blockers"], 1):
            print(f"{index}. {blocker['code']}")
            if blocker.get("missing"):
                print(f"   missing: {blocker['missing']}")
            print(f"   next: {blocker['action']}")
        print("WINDOWS_BOOT_PROVEN=false")
        print(report["security"])
    return 0 if report["blocker_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
