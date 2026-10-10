import json
from datetime import datetime, timezone
from pathlib import Path

from brain_v12.brain.golden_mission_system_audit import audit_repository


def _touch(root: Path, relative: str, text: str = "present\n") -> None:
    path = root / relative
    if relative.endswith("/"):
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_audit_inventories_workflows_and_fails_closed_without_runtime_evidence(tmp_path):
    _touch(tmp_path, ".github/workflows/check.yml", "name: Check\non:\n  pull_request:\n  workflow_dispatch:\n")
    for path in ("README.md", "PROJECT_MASTER_SPEC.md", "PROJECT_ROADMAP.md", "DECISIONS.md", "CHANGELOG.md"):
        _touch(tmp_path, path)
    report = audit_repository(tmp_path)
    assert report["audit_status"] == "PASS"
    assert report["workflow_count"] == 1
    assert report["workflows"][0]["triggers"] == ["pull_request", "workflow_dispatch"]
    assert report["launch_readiness"] == "BLOCKED"
    blocker_codes = {item["code"] for item in report["launch_blockers"]}
    assert "LEGACY_REQUIREMENTS_NOT_RESTORED" in blocker_codes
    assert "LIVE_RUNTIME_EVIDENCE_MISSING" in blocker_codes
    assert report["safety"]["dispatches_workflows"] is False


def test_audit_requires_complete_source_lanes_and_explicit_runtime_evidence(tmp_path):
    _touch(tmp_path, ".github/workflows/brain-deploy.yml", "name: Brain Deploy\non:\n  workflow_dispatch:\n")
    for path in (
        "README.md", "PROJECT_MASTER_SPEC.md", "PROJECT_ROADMAP.md", "DECISIONS.md", "CHANGELOG.md",
        "brain_v12/app.py", "brain_v12/brain/device_bridge.py",
        ".github/workflows/brain-github-cloud.yml", ".github/workflows/brain-github-supervisor.yml",
        "brain_v12/movie_summary_factory", ".github/workflows/brain-release-gate.yml",
        ".github/workflows/brain-android-executor.yml", ".github/workflows/brain-quran-layer-audit.yml",
        "brain_v12/brain/economic_ledger.py", ".github/workflows/commercial-evidence-gate.yml",
        "brain_v12/brain/synthetic_customer.py", ".github/workflows/brain-customer-portal-smoke.yml",
        "recovery", ".github/workflows/brain-golden-recovery.yml",
        "brain_v12/virtual_hardware", ".github/workflows/brain-windows-real-boot.yml",
    ):
        _touch(tmp_path, path)
    _touch(tmp_path, "LEGACY_REQUIREMENTS.md", "RESTORATION_STATUS: COMPLETE\n")
    _touch(tmp_path, "TODO_FROM_LEGACY.md", "RESTORATION_STATUS: COMPLETE\n")
    evidence_path = tmp_path / ".brain/state/production_runtime_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(json.dumps({
        "status": "VERIFIED",
        "source": "assembled_live_runtime_and_drills",
        "target_host": "brain-test.internal",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "executes_missions": False,
            "changes_service_state": False,
            "stores_control_key": False,
        },
        "checks": [
            {"name": "runtime_api_readiness", "passed": True, "response_sha256": "a" * 64},
            {"name": "runtime_worker_status", "passed": True, "response_sha256": "b" * 64},
            {"name": "mission_persistence_restart", "passed": True, "evidence_ref": "restart-drill.log", "evidence_sha256": "c" * 64},
            {"name": "restore_drill", "passed": True, "evidence_ref": "restore-drill.log", "evidence_sha256": "d" * 64},
        ],
    }), encoding="utf-8")
    report = audit_repository(tmp_path)
    assert report["audit_status"] == "PASS"
    assert report["launch_readiness"] == "READY"
    assert all(item["source_present"] for item in report["project_lanes"].values())
    deploy_workflow = next(item for item in report["workflows"] if item["path"].endswith("brain-deploy.yml"))
    assert deploy_workflow["launch_policy"] == "REVIEW_BEFORE_MANUAL_LAUNCH"


def test_legacy_recovery_placeholders_do_not_satisfy_launch_gate(tmp_path):
    _touch(tmp_path, ".github/workflows/check.yml", "name: Check\non:\n  pull_request:\n")
    for path in ("README.md", "PROJECT_MASTER_SPEC.md", "PROJECT_ROADMAP.md", "DECISIONS.md", "CHANGELOG.md"):
        _touch(tmp_path, path)
    _touch(tmp_path, "LEGACY_REQUIREMENTS.md", "RESTORATION_STATUS: INCOMPLETE\n")
    _touch(tmp_path, "TODO_FROM_LEGACY.md", "RESTORATION_STATUS: INCOMPLETE\n")
    report = audit_repository(tmp_path)
    assert report["legacy_documentation"]["LEGACY_REQUIREMENTS.md"] is False
    assert report["legacy_documentation"]["TODO_FROM_LEGACY.md"] is False
    assert "LEGACY_REQUIREMENTS_NOT_RESTORED" in {item["code"] for item in report["launch_blockers"]}

def test_invalid_runtime_evidence_never_unlocks_launch(tmp_path):
    _touch(tmp_path, ".github/workflows/check.yml", "name: Check\non:\n  pull_request:\n")
    for path in ("README.md", "PROJECT_MASTER_SPEC.md", "PROJECT_ROADMAP.md", "DECISIONS.md", "CHANGELOG.md"):
        _touch(tmp_path, path)
    evidence_path = tmp_path / ".brain/state/production_runtime_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(json.dumps({"status": "VERIFIED", "checks": [{"name": "api", "passed": False}]}), encoding="utf-8")
    report = audit_repository(tmp_path)
    assert report["launch_readiness"] == "BLOCKED"
    assert "LIVE_RUNTIME_EVIDENCE_MISSING" in {item["code"] for item in report["launch_blockers"]}



def test_stale_or_wrong_source_runtime_evidence_does_not_unlock_launch(tmp_path):
    from datetime import timedelta

    _touch(tmp_path, ".github/workflows/check.yml", "name: Check\non:\n  pull_request:\n")
    for path in ("README.md", "PROJECT_MASTER_SPEC.md", "PROJECT_ROADMAP.md", "DECISIONS.md", "CHANGELOG.md"):
        _touch(tmp_path, path)
    evidence_path = tmp_path / ".brain/state/production_runtime_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(json.dumps({
        "status": "VERIFIED",
        "source": "manual",
        "target_host": "brain-test.internal",
        "checked_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "safety": {"executes_missions": False, "changes_service_state": False, "stores_control_key": False},
        "checks": [
            {"name": "runtime_api_readiness", "passed": True, "response_sha256": "a" * 64},
            {"name": "runtime_worker_status", "passed": True, "response_sha256": "b" * 64},
            {"name": "mission_persistence_restart", "passed": True, "evidence_ref": "restart-drill.log", "evidence_sha256": "c" * 64},
            {"name": "restore_drill", "passed": True, "evidence_ref": "restore-drill.log", "evidence_sha256": "d" * 64},
        ],
    }), encoding="utf-8")
    report = audit_repository(tmp_path)
    assert report["launch_readiness"] == "BLOCKED"
    assert "LIVE_RUNTIME_EVIDENCE_MISSING" in {item["code"] for item in report["launch_blockers"]}
