"""Integration boundary tests: no mining/revenue claim without Brain-owned execution.

All telemetry below is synthetic test input. The native Brain mining backend is
not implemented, so this suite must never promote a planned job to real mining
or realized revenue.
"""
from brain_v12.brain.cloud_mining_control_plane import CloudMiningControlPlane, CloudWorker


def _planned_job():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("brain-vm-01", "vm", "brain-region", "brain", enabled=True))
    return cp, cp.plan("brain-vm-01")


def test_planned_job_cannot_be_admitted_without_brain_native_backend():
    cp, job = _planned_job()
    assert job.status == "BLOCKED_BACKEND_NOT_IMPLEMENTED"
    admitted, reason = cp.admit(job.job_id, on_github_actions=False, temperature_c=40.0)
    assert admitted is False
    assert reason == "brain_owned_mining_backend_not_implemented"

    evidence = cp.evidence(
        job.job_id, hashrate=1000.0, accepted=12, rejected=1, payout_tx_id="synthetic-test-tx"
    )
    assert evidence["evidence_source"] == "caller_supplied_unverified_telemetry"
    assert evidence["financial_state"] == "NOT_VERIFIED"
    assert evidence["payout_verified"] is False
    assert evidence["status"] == "PAYOUT_TX_REFERENCE_PRESENT"


def test_github_actions_mining_path_is_blocked():
    cp, job = _planned_job()
    admitted, reason = cp.admit(job.job_id, on_github_actions=True)
    assert admitted is False
    assert reason == "github_actions_mining_forbidden"


def test_physical_device_cannot_be_registered_as_compute_worker():
    cp = CloudMiningControlPlane()
    try:
        cp.register_worker(CloudWorker("asic-01", "asic", "region", "owner", enabled=True))
    except ValueError as exc:
        assert "physical devices are gateways only" in str(exc)
    else:
        raise AssertionError("physical ASIC must be a gateway, not a mining compute worker")
