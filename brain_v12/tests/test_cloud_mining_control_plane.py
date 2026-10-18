from brain_v12.brain.cloud_mining_control_plane import CloudMiningControlPlane, CloudWorker


def _planned_job():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=True))
    return cp, cp.plan("w1")


def _ready_job():
    return _planned_job()


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
    cp, job = _planned_job()
    ok, reason = cp.admit(job.job_id, on_github_actions=True)
    assert not ok
    assert reason == "github_actions_mining_forbidden"


def test_worker_identity_cannot_be_reassigned_to_another_owner_or_kind():
    cp = CloudMiningControlPlane()
    cp.register_worker(CloudWorker("w1", "vm", "region-a", "owner-a", enabled=True))
    for replacement in (
        CloudWorker("w1", "vm", "region-b", "owner-b", enabled=True),
        CloudWorker("w1", "android", "region-a", "owner-a", enabled=True),
    ):
        try:
            cp.register_worker(replacement)
        except ValueError as exc:
            assert "worker identity conflict" in str(exc)
        else:
            raise AssertionError("worker identity must not be reassigned")
    # Safe operational updates for the same owner and kind are allowed.
    cp.register_worker(CloudWorker("w1", "VM", "region-b", "owner-a", enabled=False))
    assert cp.workers["w1"].kind == "vm"
    assert cp.workers["w1"].enabled is False


def test_disabled_worker_cannot_run_a_previously_planned_job():
    cp, job = _planned_job()
    cp.register_worker(CloudWorker("w1", "vm", "user-region", "owner", enabled=False))
    ok, reason = cp.admit(job.job_id)
    assert not ok
    assert reason == "worker_disabled"


def test_resource_limits_are_enforced_and_execution_stays_blocked():
    cp, job = _planned_job()
    assert job.status == "BLOCKED_BACKEND_NOT_IMPLEMENTED"
    assert cp.admit(job.job_id, cpu_percent=50.0) == (
        False, "brain_owned_mining_backend_not_implemented"
    )
    assert cp.admit(job.job_id, cpu_percent=50.1) == (False, "cpu_limit_reached")
    assert cp.admit(job.job_id, temperature_c=75.0) == (False, "thermal_limit_reached")


def test_plan_uses_brain_owned_software_runtime_only():
    cp, job = _planned_job()
    assert job.miner == "brain-native-backend-pending"
    assert job.mode == "plan-only"
    assert job.status == "BLOCKED_BACKEND_NOT_IMPLEMENTED"
    snapshot = cp.snapshot()
    assert snapshot["execution"] == "brain_owned_software_runtime_plan_only"
    assert snapshot["physical_devices_role"] == "connectivity_observation_only"
    assert snapshot["external_miner_execution"] == "FORBIDDEN"


def test_physical_devices_cannot_register_as_mining_compute_workers():
    cp = CloudMiningControlPlane()
    for worker in (
        CloudWorker("phone", "android", "region", "owner", enabled=True),
        CloudWorker("asic", "asic", "region", "owner", enabled=True),
        CloudWorker("desktop", "desktop", "region", "owner", enabled=True),
    ):
        try:
            cp.register_worker(worker)
        except ValueError as exc:
            assert "physical devices are gateways only" in str(exc)
        else:
            raise AssertionError("physical device must not register as mining compute worker")


def test_invalid_telemetry_is_rejected():
    cp, job = _planned_job()
    for kwargs in (
        {"cpu_percent": float("nan")},
        {"temperature_c": float("inf")},
        {"cpu_percent": -1},
        {"cpu_percent": 101},
        {"temperature_c": True},
        {"cpu_percent": True},
    ):
        ok, reason = cp.admit(job.job_id, **kwargs)
        assert not ok
        assert reason.startswith("invalid_")


def test_evidence_is_labeled_unverified_and_not_revenue():
    cp, job = _planned_job()
    ev = cp.evidence(job.job_id, 1000, 5, 1)
    assert ev["schema"] == "brain-mining-evidence/v1"
    assert ev["status"] == "MINING_EVIDENCE_ONLY"
    assert ev["evidence_source"] == "caller_supplied_unverified_telemetry"
    assert ev["financial_state"] == "NOT_VERIFIED"
    assert ev["payout_verified"] is False
    assert ev["worker_id"] == "w1"


def test_transaction_reference_is_not_verified_receipt():
    cp, job = _planned_job()
    ev = cp.evidence(job.job_id, 1000, 5, 1, payout_tx_id=" tx-123 ")
    assert ev["payout_tx_id"] == "tx-123"
    assert ev["status"] == "PAYOUT_TX_REFERENCE_PRESENT"
    assert ev["financial_state"] == "NOT_VERIFIED"
    assert ev["payout_verified"] is False
    assert ev["status"] != "VERIFIED_RECEIVED"


def test_invalid_hashrate_and_share_counts_are_rejected():
    cp, job = _planned_job()
    for args in (
        (-1, 1, 0),
        (float("nan"), 1, 0),
        (float("inf"), 1, 0),
        (True, 1, 0),
        ("100", 1, 0),
        (100, -1, 0),
        (100, 1, -1),
        (100, True, 0),
        (100, 1, False),
    ):
        try:
            cp.evidence(job.job_id, *args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid telemetry accepted: {args}")


def test_blank_transaction_reference_is_rejected():
    cp, job = _planned_job()
    try:
        cp.evidence(job.job_id, 1, 1, 0, payout_tx_id="   ")
    except ValueError:
        pass
    else:
        raise AssertionError("blank payout transaction reference accepted")


def test_invalid_worker_limits_are_rejected():
    cp = CloudMiningControlPlane()
    for worker in (
        CloudWorker("w1", "vm", "region", "owner", max_cpu_percent=0),
        CloudWorker("w2", "vm", "region", "owner", max_cpu_percent=float("nan")),
        CloudWorker("w3", "vm", "region", "owner", max_temperature_c=0),
        CloudWorker("w4", "vm", "region", "owner", max_temperature_c=float("inf")),
    ):
        try:
            cp.register_worker(worker)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid worker limits must be rejected")


def test_snapshot_exposes_machine_readable_blockers_without_claiming_live_mining():
    cp = CloudMiningControlPlane()
    snapshot = cp.snapshot()
    assert snapshot["worker_count"] == 0
    assert snapshot["enabled_worker_count"] == 0
    assert snapshot["execution_ready"] is False
    assert snapshot["live_mining_verified"] is False
    assert snapshot["accepted_shares_independently_verified"] is False
    assert snapshot["revenue_realized"] is False
    assert "NO_REGISTERED_WORKERS" in snapshot["blockers"]
    assert "NATIVE_MINING_BACKEND_NOT_IMPLEMENTED" in snapshot["blockers"]
    assert "VERIFIED_STRATUM_SESSION_REQUIRED" in snapshot["blockers"]
    assert "INDEPENDENT_ACCEPTED_SHARE_PROOF_REQUIRED" in snapshot["blockers"]
    assert "INDEPENDENT_PAYOUT_RECONCILIATION_REQUIRED" in snapshot["blockers"]


def test_snapshot_reports_worker_and_blocked_job_counts():
    cp, job = _planned_job()
    snapshot = cp.snapshot()
    assert snapshot["worker_count"] == 1
    assert snapshot["enabled_worker_count"] == 1
    assert snapshot["job_count"] == 1
    assert snapshot["blocked_job_count"] == 1
    assert "NO_REGISTERED_WORKERS" not in snapshot["blockers"]
    assert "NATIVE_MINING_BACKEND_NOT_IMPLEMENTED" in snapshot["blockers"]
