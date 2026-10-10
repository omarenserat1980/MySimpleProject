"""Read-only inventory and fail-closed launch readiness audit for Electronic Brain."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_LANES = {
    "brain_core": ["brain_v12/app.py", "brain_v12/brain"],
    "cloud_runtime": [".github/workflows/brain-github-cloud.yml", ".github/workflows/brain-github-supervisor.yml"],
    "media_cinema": ["brain_v12/movie_summary_factory", ".github/workflows/brain-release-gate.yml"],
    "device_bridge": ["brain_v12/brain/device_bridge.py", ".github/workflows/brain-android-executor.yml"],
    "knowledge_quran": ["brain_v12", ".github/workflows/brain-quran-layer-audit.yml"],
    "economics_commercial": ["brain_v12/brain/economic_ledger.py", ".github/workflows/commercial-evidence-gate.yml"],
    "customer_marketing": ["brain_v12/brain/synthetic_customer.py", ".github/workflows/brain-customer-portal-smoke.yml"],
    "recovery_security": ["recovery", ".github/workflows/brain-golden-recovery.yml"],
    "windows_virtualization": ["brain_v12/virtual_hardware", ".github/workflows/brain-windows-real-boot.yml"],
}
CORE_DOCS = ["README.md", "PROJECT_MASTER_SPEC.md", "PROJECT_ROADMAP.md", "DECISIONS.md", "CHANGELOG.md"]
LEGACY_DOCS = ["LEGACY_REQUIREMENTS.md", "TODO_FROM_LEGACY.md"]
RISK_TOKENS = ("deploy", "publish", "payment", "payout", "mining", "provision", "real-boot", "launch", "withdraw", "commercial")

def _present(root: Path, relative: str) -> bool:
    return (root / relative).exists()

def _legacy_restored(root: Path, relative: str) -> bool:
    path = root / relative
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "RESTORATION_STATUS: COMPLETE" in content and "RESTORATION_STATUS: INCOMPLETE" not in content

def _workflow_record(path: Path, root: Path) -> dict[str, Any]:
    text = (root / path).read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?m)^name:\s*(.+?)\s*$", text)
    name = match.group(1).strip().strip("'\"") if match else path.stem
    triggers = []
    for trigger in ("pull_request", "push", "workflow_dispatch", "schedule", "workflow_run", "workflow_call"):
        if re.search(r"(?m)^\s{0,4}" + re.escape(trigger) + r":", text):
            triggers.append(trigger)
    flags = [token for token in RISK_TOKENS if token in (path.stem + " " + name).lower()]
    return {
        "path": path.as_posix(), "name": name, "triggers": triggers,
        "manual_dispatch": "workflow_dispatch" in triggers,
        "name_based_review_flags": flags,
        "launch_policy": "REVIEW_BEFORE_MANUAL_LAUNCH" if flags else "CI_OR_READ_ONLY_CANDIDATE",
        "classification_note": "Name-based heuristic only; inspect workflow steps before external side effects.",
    }

def audit_repository(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    wfroot = root / ".github" / "workflows"
    paths = sorted(wfroot.glob("*.yml")) + sorted(wfroot.glob("*.yaml"))
    workflows = [_workflow_record(p.relative_to(root), root) for p in paths]
    lanes = {name: {"required_paths": required, "source_present": all(_present(root, p) for p in required)}
             for name, required in PROJECT_LANES.items()}
    core_docs = {p: _present(root, p) for p in CORE_DOCS}
    legacy_docs = {p: _legacy_restored(root, p) for p in LEGACY_DOCS}
    evidence_candidates = [".brain/state/production_runtime_evidence.json", "brain6_artifacts/evidence/live_runtime_evidence.json"]
    evidence = []
    for relative in evidence_candidates:
        path = root / relative
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            checks = payload.get("checks", [])
            required_checks = {
                "runtime_api_readiness",
                "runtime_worker_status",
                "mission_persistence_restart",
                "restore_drill",
            }
            named_checks = {
                item.get("name"): item for item in checks
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            } if isinstance(checks, list) else {}
            checked_at = None
            fresh = False
            try:
                checked_at = datetime.fromisoformat(str(payload.get("checked_at", "")).replace("Z", "+00:00"))
                if checked_at.tzinfo is not None:
                    age_seconds = (datetime.now(timezone.utc) - checked_at.astimezone(timezone.utc)).total_seconds()
                    fresh = 0 <= age_seconds <= 24 * 60 * 60
            except (TypeError, ValueError, OverflowError):
                pass
            safety = payload.get("safety", {})
            valid = (
                payload.get("status") == "VERIFIED"
                and payload.get("source") == "live_read_only_runtime_probe"
                and bool(payload.get("target_host"))
                and fresh
                and isinstance(safety, dict)
                and safety.get("executes_missions") is False
                and safety.get("changes_service_state") is False
                and safety.get("stores_control_key") is False
                and required_checks.issubset(named_checks)
                and all(named_checks[name].get("passed") is True for name in required_checks)
                and all(
                    isinstance(named_checks[name].get("response_sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", named_checks[name]["response_sha256"])
                    for name in ("runtime_api_readiness", "runtime_worker_status")
                )
            )
            evidence.append({
                "path": relative,
                "valid": valid,
                "fresh_within_24h": fresh,
                "check_count": len(checks) if isinstance(checks, list) else 0,
                "missing_required_checks": sorted(required_checks - set(named_checks)),
            })
        except (OSError, ValueError, TypeError):
            evidence.append({"path": relative, "valid": False, "check_count": 0})
    missing_core = [p for p, exists in core_docs.items() if not exists]
    missing_legacy = [p for p, exists in legacy_docs.items() if not exists]
    missing_lanes = [name for name, data in lanes.items() if not data["source_present"]]
    blockers = []
    if missing_core:
        blockers.append({"code": "CORE_DOCUMENTATION_MISSING", "items": missing_core})
    if missing_legacy:
        blockers.append({"code": "LEGACY_REQUIREMENTS_NOT_RESTORED", "items": missing_legacy})
    if missing_lanes:
        blockers.append({"code": "PROJECT_SOURCE_INCOMPLETE", "items": missing_lanes})
    if not any(item["valid"] for item in evidence):
        blockers.append({"code": "LIVE_RUNTIME_EVIDENCE_MISSING", "items": evidence_candidates})
    return {
        "schema_version": 1,
        "audit_status": "PASS" if workflows and not missing_core else "FAIL",
        "launch_readiness": "READY" if not blockers else "BLOCKED",
        "source_of_truth": "Git repository",
        "workflow_count": len(workflows), "workflows": workflows,
        "project_lanes": lanes, "core_documentation": core_docs,
        "legacy_documentation": legacy_docs, "runtime_evidence": evidence,
        "launch_blockers": blockers,
        "safety": {"dispatches_workflows": False, "deploys_services": False,
                   "reads_secrets": False, "source_presence_is_runtime_proof": False},
    }

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = audit_repository(args.root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["audit_status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
