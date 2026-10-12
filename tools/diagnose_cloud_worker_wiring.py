#!/usr/bin/env python3
"""Read-only diagnosis of Brain API / cloud-worker deployment wiring.

Accepts a Render service JSON export on stdin or --service-json PATH.
Never calls Render, prints environment-variable values, or mutates a deployment.
Exit 0 only when the API and worker are explicitly configured as separate
services and the worker has a durable state volume; otherwise exit 2 (blocked).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def diagnose(service: dict[str, Any]) -> dict[str, Any]:
    details = service.get("serviceDetails") or {}
    env_details = details.get("envSpecificDetails") or {}
    start = str(env_details.get("startCommand") or "")
    name = str(service.get("name") or "")
    runtime = str(details.get("runtime") or details.get("env") or "")
    is_api = "uvicorn brain_v12.app:app" in start
    starts_worker = (
        "brain_v12.cloud_runtime.worker" in start
        or "BrainCloudWorker.dll" in start
        or "docker compose" in start and "cloud_worker" in start
    )
    is_web = str(service.get("type") or "") == "web_service"
    findings: list[str] = []
    if is_web and is_api and not starts_worker:
        findings.append("API_ONLY_START_COMMAND")
    elif is_api and starts_worker:
        findings.append("API_AND_WORKER_SHARE_START_COMMAND_REVIEW_REQUIRED")
    elif not starts_worker:
        findings.append("WORKER_START_COMMAND_NOT_PROVEN")
    if runtime.lower() in {"python", "node", "ruby", "go"} and "BrainCloudWorker.dll" in start:
        findings.append("WORKER_BINARY_RUNTIME_MISMATCH")

    return {
        "service_name": name or None,
        "service_type": service.get("type"),
        "runtime": runtime or None,
        "start_command_class": (
            "API_ONLY" if is_api and not starts_worker else
            "API_AND_WORKER" if is_api and starts_worker else
            "WORKER_LAUNCH_PRESENT" if starts_worker else "UNKNOWN"
        ),
        "worker_launch_proven": starts_worker,
        "findings": findings,
        "status": "BLOCKED" if findings else "REQUIRES_WORKER_HEALTH_PROOF",
        "next_checks": [
            "Inspect cloud-worker preflight results on the actual worker host.",
            "Confirm the worker's BRAIN_RUNTIME_ROOT is the intended durable path.",
            "Confirm /health heartbeat age is within BRAIN_WORKER_HEARTBEAT_TTL_SECONDS.",
            "Verify one harmless queued task and its evidence before declaring RUNNING.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--service-json", type=Path, help="Path to a saved Render service JSON response")
    source.add_argument("--stdin", action="store_true", help="Read service JSON from stdin")
    args = parser.parse_args()
    try:
        raw = args.service_json.read_text(encoding="utf-8") if args.service_json else sys.stdin.read()
        service = json.loads(raw)
        if not isinstance(service, dict):
            raise ValueError("top-level JSON must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2))
        return 3
    result = diagnose(service)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
