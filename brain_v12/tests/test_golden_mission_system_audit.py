import json
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
        "LEGACY_REQUIREMENTS.md", "TODO_FROM_LEGACY.md",
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
    evidence_path = tmp_path / ".brain/state/production_runtime_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(json.dumps({"status": "VERIFIED", "checks": [{"name": "api", "passed": True}]}), encoding="utf-8")
    report = audit_repository(tmp_path)
    assert report["audit_status"] == "PASS"
    assert report["launch_readiness"] == "READY"
    assert all(item["source_present"] for item in report["project_lanes"].values())
    assert report["workflows"][0]["launch_policy"] == "REVIEW_BEFORE_MANUAL_LAUNCH"


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
