from brain_v12.brain.cloud_mining_control_plane import CloudMiningControlPlane, CloudWorker


def _ready_job():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=True))
    return cp, cp.plan("w1")


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
    cp, job = _ready_job()
    ok, reason = cp.admit(job.job_id, on_github_actions=True)
    assert not ok
    assert reason == "github_actions_mining_forbidden"


def test_disabled_worker_cannot_run_a_previously_planned_job():
    cp, job = _ready_job()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=False))
    ok, reason = cp.admit(job.job_id)
    assert not ok
    assert reason == "worker_disabled"


def test_non_finite_temperature_is_rejected():
    cp, job = _ready_job()
    ok, reason = cp.admit(job.job_id, temperature_c=float("nan"))
    assert not ok
    assert reason == "invalid_temperature"


def test_evidence_is_labeled_unverified_and_not_revenue():
    cp, job = _ready_job()
    ev = cp.evidence(job.job_id, 1000, 5, 1)
    assert ev["schema"] == "brain-mining-evidence/v1"
    assert ev["status"] == "MINING_EVIDENCE_ONLY"
    assert ev["evidence_source"] == "caller_supplied_unverified_telemetry"
    assert ev["financial_state"] == "NOT_VERIFIED"
    assert ev["worker_id"] == "w1"


def test_transaction_reference_is_not_verified_receipt():
    cp, job = _ready_job()
    ev = cp.evidence(job.job_id, 1000, 5, 1, payout_tx_id=" tx-123 ")
    assert ev["payout_tx_id"] == "tx-123"
    assert ev["status"] == "PAYOUT_TX_REFERENCE_PRESENT"
    assert ev["financial_state"] == "NOT_VERIFIED"
    assert ev["status"] != "VERIFIED_RECEIVED"


def test_invalid_telemetry_is_rejected():
    cp, job = _ready_job()
    for hashrate, accepted, rejected in (
        (-1, 1, 0),
        (float("nan"), 1, 0),
        (float("inf"), 1, 0),
        (100, -1, 0),
        (100, 1, -1),
        (100, True, 0),
    ):
        try:
            cp.evidence(job.job_id, hashrate, accepted, rejected)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid telemetry must be rejected")


def test_empty_payout_reference_is_rejected():
    cp, job = _ready_job()
    try:
        cp.evidence(job.job_id, 100, 1, 0, payout_tx_id="   ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty transaction references must be rejected")


def test_invalid_worker_limits_are_rejected():
    cp = CloudMiningControlPlane()
    for worker in (
        CloudWorker("w1", "vm", "region", "owner", max_cpu_percent=0),
        CloudWorker("w2", "vm", "region", "owner", max_cpu_percent=float("nan")),
        CloudWorker("w3", "vm", "region", "owner", max_temperature_c=0),
    ):
        try:
            cp.register_worker(worker)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid worker limits must be rejected")
