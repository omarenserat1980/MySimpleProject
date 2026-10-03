from brain_v12.brain.cloud_mining_control_plane import CloudMiningControlPlane, CloudWorker

def test_cloud_worker_must_be_enabled_before_job():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner"))
    try:
        cp.plan("w1")
    except PermissionError:
        pass
    else:
        raise AssertionError("disabled worker must not receive a job")

def test_github_actions_is_never_admitted():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=True))
    job = cp.plan("w1")
    ok, reason = cp.admit(job.job_id, on_github_actions=True)
    assert not ok
    assert reason == "github_actions_mining_forbidden"

def test_payment_evidence_requires_transaction_id():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=True))
    job = cp.plan("w1")
    ev = cp.evidence(job.job_id, 1000, 5, 1)
    assert ev["status"] == "MINING_EVIDENCE_ONLY"


def test_transaction_reference_is_not_verified_receipt():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=True))
    job = cp.plan("w1")
    ev = cp.evidence(job.job_id, 1000, 5, 1, payout_tx_id="tx-123")
    assert ev["status"] == "PAYOUT_TX_REFERENCE_PRESENT"
    assert ev["status"] != "VERIFIED_RECEIVED"
