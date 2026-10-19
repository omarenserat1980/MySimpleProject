from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / ".github" / "workflows" / "brain-braiins-live-evidence-probe.yml"


def test_live_evidence_probe_is_manual_and_read_only():
    workflow = PROBE.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow


def test_live_evidence_probe_does_not_start_or_configure_mining():
    workflow = PROBE.read_text(encoding="utf-8").lower()
    assert "stratum" not in workflow
    assert "miner start" not in workflow
    assert "pool settings" in workflow
    assert "no shares were submitted" in workflow


def test_missing_live_configuration_does_not_gate_ci():
    workflow = PROBE.read_text(encoding="utf-8")
    assert "LIVE_EVIDENCE_UNAVAILABLE" in workflow
    assert "exit 0" in workflow
    assert "does not affect CI status" in workflow


def test_pool_telemetry_never_implies_brain_work_or_revenue():
    workflow = PROBE.read_text(encoding="utf-8")
    assert "brain_runtime_activity_verified" in workflow
    assert "accepted_share_submission_verified" in workflow
    assert "payout_verified" in workflow
    assert "revenue_verified" in workflow
    assert "A successful workflow run is not mining proof." in workflow


def test_pool_token_is_environment_only_and_not_printed():
    workflow = PROBE.read_text(encoding="utf-8")
    assert "BRAIINS_POOL_API_TOKEN: ${{ secrets.BRAIINS_POOL_API_TOKEN }}" in workflow
    assert "echo \"$BRAIINS_POOL_API_TOKEN\"" not in workflow
    assert "echo \"$BRAIINS_POOL_WORKER_ID\"" not in workflow
