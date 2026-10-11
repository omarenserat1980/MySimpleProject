#!/usr/bin/env python3
"""Fast, fail-closed Golden Loop evidence triage for Electronic Brain.

This tool only reads local JSON evidence. It never issues contracts, changes secrets,
starts VMs, calls cloud APIs, or declares success from missing evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

SCHEMA = "brain.golden-loop-accelerator.v1"
CANDIDATES = {
    "runner": {"runner-health.json", "brain-runner-health.json", "runner_watch.json"},
    "executor": {"cloud-executor-gate.json", "cloud_executor_gate.json"},
    "contract": {"windows-execution-contract-gate.json", "windows-contract-gate.json"},
    "boot": {"windows-boot-evidence.json", "windows_boot_evidence.json"},
    "completion": {"windows-completion-gate.json", "windows_completion_gate.json"},
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"_parse_error": type(exc).__name__}
    return data if isinstance(data, dict) else {"_parse_error": "JSON_ROOT_NOT_OBJECT"}


def run_id_of(data: dict[str, Any]) -> str | None:
    for key in ("workflow_run_id", "run_id", "github_run_id"):
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    nested = data.get("control")
    if isinstance(nested, dict):
        value = nested.get("workflow_run_id") or nested.get("run_id")
        if value not in (None, ""):
            return str(value)
    return None


def passed(kind: str, data: dict[str, Any]) -> bool:
    if data.get("_parse_error"):
        return False
    if kind == "runner":
        health = str(data.get("health", data.get("status", ""))).upper()
        probe = str(data.get("execution_probe", "")).upper()
        runtime = str(data.get("runtime_surface", data.get("runtime_probe", ""))).upper()
        return (
            health in {"VERIFIED", "READY", "PASS", "HEALTHY"}
            and data.get("online") is True
            and probe in {"PASS", "SUCCESS", "VERIFIED"}
            and runtime in {"PASS", "SUCCESS", "VERIFIED"}
        )
    if kind == "executor":
        return data.get("verified") is True and bool(
            data.get("executor_id") or data.get("executor") or data.get("host")
            or data.get("executor_host") or data.get("hostname")
        )
    if kind == "contract":
        status = str(data.get("status", data.get("result", ""))).upper()
        return data.get("verified") is True or status in {"VERIFIED", "VALID", "CONTRACT_VERIFIED"}
    if kind == "boot":
        guest = data.get("guest") if isinstance(data.get("guest"), dict) else {}
        marker = (
            data.get("boot_verified") is True
            or data.get("WINDOWS_BOOT_VERIFIED") is True
            or guest.get("boot_verified") is True
            or data.get("status") == "WINDOWS_BOOT_VERIFIED"
        )
        os_name = str(
            data.get("caption")
            or data.get("os_caption")
            or data.get("operating_system")
            or guest.get("os_caption")
            or guest.get("os")
            or ""
        ).lower()
        boot_time = data.get("boot_time") or data.get("last_boot_up_time") or guest.get("boot_time")
        return marker and "windows server 2025" in os_name and bool(boot_time)
    if kind == "completion":
        status = str(data.get("status", "")).upper()
        return status == "WINDOWS_BOOT_VERIFIED" and not data.get("reasons")
    return False


def find_evidence(root: Path) -> dict[str, list[Path]]:
    found = {kind: [] for kind in CANDIDATES}
    for path in root.rglob("*.json"):
        if not path.is_file():
            continue
        name = path.name.lower()
        for kind, names in CANDIDATES.items():
            if name in names:
                found[kind].append(path)
    for paths in found.values():
        paths.sort(key=lambda p: (p.stat().st_mtime_ns, str(p)), reverse=True)
    return found


def inspect(root: Path, expected_run_id: str | None = None) -> dict[str, Any]:
    found = find_evidence(root)
    gates: dict[str, Any] = {}
    all_run_ids: dict[str, str] = {}
    for kind, paths in found.items():
        entries = []
        for path in paths:
            data = read_json(path)
            rid = run_id_of(data)
            entry = {
                "path": str(path),
                "run_id": rid,
                "passed": passed(kind, data),
                "parse_error": data.get("_parse_error"),
            }
            entries.append(entry)
            if rid:
                all_run_ids[str(path)] = rid
        # A passing file is preferred, but only if it matches an explicit run ID when supplied.
        eligible = [e for e in entries if e["passed"] and (not expected_run_id or e["run_id"] == expected_run_id)]
        selected = eligible[0] if eligible else (entries[0] if entries else None)
        gates[kind] = {
            "status": "PASS" if selected and selected["passed"] and (not expected_run_id or selected["run_id"] == expected_run_id) else "BLOCKED",
            "selected": selected,
            "candidate_count": len(entries),
            "candidates": entries[:10],
        }

    ids = sorted(set(all_run_ids.values()))
    mismatched = bool(expected_run_id and any(rid != expected_run_id for rid in ids))
    cross_run = len(ids) > 1
    blockers = []
    actions = {
        "runner": "Restore runner-watch token/registration; require online=true, execution_probe=PASS, and runtime_surface=PASS.",
        "executor": "Run the trusted executor attestation and QEMU/KVM capability gate on the designated host.",
        "contract": "Issue a real short-lived contract through the authenticated Control Plane using owner-approved identity, checkpoint, lease, and signing configuration; verify it locally.",
        "boot": "Run the guest evidence collector only after contract and executor gates pass; capture Windows Server 2025 boot evidence from the installed disk.",
        "completion": "Run the independent Windows completion gate on evidence bound to the same workflow run and installed disk.",
    }
    for kind in ("runner", "executor", "contract", "boot", "completion"):
        if gates[kind]["status"] != "PASS":
            blockers.append({"gate": kind, "reason": "PASSING_EVIDENCE_MISSING_OR_INVALID", "next_action": actions[kind]})
    if cross_run:
        blockers.insert(0, {
            "gate": "evidence_binding",
            "reason": "CANDIDATES_SPAN_MULTIPLE_WORKFLOW_RUN_IDS",
            "next_action": "Select evidence from one workflow run/attempt; do not combine artifacts from separate runs.",
        })
    if mismatched:
        blockers.insert(0, {
            "gate": "evidence_binding",
            "reason": "EXPECTED_RUN_ID_MISMATCH",
            "next_action": "Collect artifacts for the requested workflow run ID; discard cross-run evidence from the completion decision.",
        })
    ready = not blockers and all(g["status"] == "PASS" for g in gates.values())
    return {
        "schema": SCHEMA,
        "status": "GOLDEN_LOOP_VERIFIED" if ready else "GOLDEN_LOOP_BLOCKED",
        "root": str(root),
        "expected_run_id": expected_run_id,
        "observed_run_ids": ids,
        "cross_run_candidates_detected": cross_run,
        "gates": gates,
        "blockers_in_priority_order": blockers,
        "safety": {
            "read_only": True,
            "issued_or_modified_contract": False,
            "changed_secrets": False,
            "started_vm_or_cloud_resource": False,
            "missing_evidence_means_pass": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Artifact/download root to scan recursively")
    parser.add_argument("--expected-run-id", help="Require evidence to match this workflow run ID")
    parser.add_argument("--output", help="Optional path to write the JSON report")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"schema": SCHEMA, "status": "ERROR", "error": "ROOT_NOT_DIRECTORY", "root": str(root)}))
        return 4
    report = inspect(root, args.expected_run_id)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        destination = Path(args.output).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(rendered + os.linesep, encoding="utf-8")
        temporary.replace(destination)
    print(rendered)
    return 0 if report["status"] == "GOLDEN_LOOP_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
