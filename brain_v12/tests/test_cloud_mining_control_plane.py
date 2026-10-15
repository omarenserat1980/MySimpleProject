from brain_v12.brain.cloud_mining_control_plane import CloudMiningControlPlane, CloudWorker


def _planned_job():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=True))
    return cp, cp.plan("w1")


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


def test_cpu_and_thermal_limits_are_enforced():
    cp, job = _planned_job()
    assert cp.admit(job.job_id, cpu_percent=50.0)[0]
    assert cp.admit(job.job_id, cpu_percent=50.1) == (False, "cpu_limit_reached")
    assert cp.admit(job.job_id, temperature_c=75.0) == (False, "thermal_limit_reached")


def test_invalid_telemetry_is_rejected():
    cp, job = _planned_job()
    for kwargs in ({"cpu_percent": float("nan")}, {"temperature_c": float("inf")}):
        ok, reason = cp.admit(job.job_id, **kwargs)
        assert not ok
        assert reason.startswith("invalid_")


def test_payment_evidence_requires_transaction_id_for_reference_status():
    cp, job = _ready_job()
    ev = cp.evidence(job.job_id, 1000, 5, 1)
    assert ev["status"] == "MINING_EVIDENCE_ONLY"
    assert ev["financial_state"] == "NOT_VERIFIED"


def test_transaction_reference_is_not_verified_receipt():
    cp, job = _ready_job()
    ev = cp.evidence(job.job_id, 1000, 5, 1, payout_tx_id=" tx-123 ")
    assert ev["payout_tx_id"] == "tx-123"
    assert ev["status"] == "PAYOUT_TX_REFERENCE_PRESENT"
    assert ev["financial_state"] == "NOT_VERIFIED"
    assert ev["status"] != "VERIFIED_RECEIVED"


def test_invalid_hashrate_and_share_counts_are_rejected():
    cp, job = _ready_job()
    for args in ((-1, 1, 0), (float("nan"), 1, 0), (float("inf"), 1, 0), (1, -1, 0), (1, 1.5, 0), (1, True, 0)):
        try:
            cp.evidence(job.job_id, *args)
        except ValueError:
            continue
        raise AssertionError(f"invalid telemetry accepted: {args}")


def test_blank_transaction_reference_is_rejected():
    cp, job = _planned_job()
    try:
        cp.evidence(job.job_id, 1, 1, 0, payout_tx_id="   ")
    except ValueError:
        pass
    else:
        raise AssertionError("blank payout transaction reference accepted")



def test_disabled_worker_cannot_run_a_previously_planned_job():
    cp, job = _ready_job()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=False))
    ok, reason = cp.admit(job.job_id)
    assert not ok
    assert reason == "worker_disabled"


def test_evidence_is_labeled_unverified_and_not_revenue():
    cp, job = _ready_job()
    ev = cp.evidence(job.job_id, 1000, 5, 1)
    assert ev["schema"] == "brain-mining-evidence/v1"
    assert ev["status"] == "MINING_EVIDENCE_ONLY"
    assert ev["evidence_source"] == "caller_supplied_unverified_telemetry"
    assert ev["financial_state"] == "NOT_VERIFIED"
    assert ev["worker_id"] == "w1"


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
