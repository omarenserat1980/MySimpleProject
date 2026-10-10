"""Assemble fresh live-probe and independently recorded drill evidence.

This tool never performs a restart or restores a backup. It only combines
proof records created by the operator after those drills actually ran.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_AGE_SECONDS = 24 * 60 * 60


def _load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON must be an object")
    return value


def _fresh_timestamp(value: Any) -> bool:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return False
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
        return 0 <= age <= MAX_AGE_SECONDS
    except (TypeError, ValueError, OverflowError):
        return False


def _valid_drill(payload: dict[str, Any], name: str, host: str) -> dict[str, Any]:
    if payload.get("source") != name:
        raise ValueError(f"{name}: incorrect source")
    if payload.get("target_host") != host:
        raise ValueError(f"{name}: target_host does not match live probe")
    if not _fresh_timestamp(payload.get("checked_at")):
        raise ValueError(f"{name}: evidence timestamp missing, stale, naive, or in the future")
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError(f"{name}: checks must be a list")
    matches = [item for item in checks if isinstance(item, dict) and item.get("name") == name]
    if len(matches) != 1:
        raise ValueError(f"{name}: exactly one named check is required")
    check = matches[0]
    if check.get("passed") is not True:
        raise ValueError(f"{name}: check did not pass")
    if not isinstance(check.get("evidence_ref"), str) or not check["evidence_ref"].strip():
        raise ValueError(f"{name}: evidence_ref is required")
    digest = check.get("evidence_sha256")
    if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
        raise ValueError(f"{name}: valid lowercase SHA-256 evidence_sha256 is required")
    return {
        "name": name,
        "passed": True,
        "evidence_ref": check["evidence_ref"],
        "evidence_sha256": digest,
        "checked_at": payload["checked_at"],
    }


def assemble(probe: dict[str, Any], restart: dict[str, Any], restore: dict[str, Any]) -> dict[str, Any]:
    if probe.get("source") != "live_read_only_runtime_probe" or probe.get("status") != "PARTIAL":
        raise ValueError("live probe must have source live_read_only_runtime_probe and status PARTIAL")
    host = probe.get("target_host")
    if not isinstance(host, str) or not host.strip():
        raise ValueError("live probe target_host is required")
    if not _fresh_timestamp(probe.get("checked_at")):
        raise ValueError("live probe evidence is stale or has an invalid timestamp")
    safety = probe.get("safety")
    if not isinstance(safety, dict) or any(safety.get(k) is not False for k in (
        "executes_missions", "changes_service_state", "stores_control_key"
    )):
        raise ValueError("live probe safety assertions are missing or unsafe")
    probe_checks = probe.get("checks")
    required_runtime = {"runtime_api_readiness", "runtime_worker_status"}
    if not isinstance(probe_checks, list):
        raise ValueError("live probe checks must be a list")
    by_name = {item.get("name"): item for item in probe_checks if isinstance(item, dict)}
    if set(by_name) != required_runtime or any(by_name[name].get("passed") is not True for name in required_runtime):
        raise ValueError("live probe must contain exactly two passing runtime checks")
    for name in required_runtime:
        if not isinstance(by_name[name].get("response_sha256"), str) or not HASH_RE.fullmatch(by_name[name]["response_sha256"]):
            raise ValueError(f"{name}: valid response SHA-256 is required")
    restart_check = _valid_drill(restart, "mission_persistence_restart", host)
    restore_check = _valid_drill(restore, "restore_drill", host)
    return {
        "schema_version": 1,
        "status": "VERIFIED",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": "assembled_live_runtime_and_drills",
        "target_host": host,
        "checks": [
            by_name["runtime_api_readiness"],
            by_name["runtime_worker_status"],
            restart_check,
            restore_check,
        ],
        "safety": {
            "executes_missions": False,
            "changes_service_state": False,
            "stores_control_key": False,
            "restart_and_restore_are_operator_supplied_evidence": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", required=True, help="JSON from the read-only live runtime probe")
    parser.add_argument("--restart-evidence", required=True, help="Evidence record created after an actual service restart")
    parser.add_argument("--restore-evidence", required=True, help="Evidence record created after an actual checkpoint restore")
    parser.add_argument("--output", default=".brain/state/production_runtime_evidence.json")
    args = parser.parse_args()
    try:
        report = assemble(_load(args.probe), _load(args.restart_evidence), _load(args.restore_evidence))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print("EVIDENCE_MANIFEST_SHA256=" + hashlib.sha256(rendered.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
