from brain_v12.brain.advanced_worker import AdvancedWorker, REAL_BOOT_CAPABILITY, REAL_BOOT_GATES


def real_facts():
    return {name: True for name in REAL_BOOT_GATES}


def test_register_heartbeat_renews_lease_without_public_last_seen():
    worker = AdvancedWorker("brain-worker-01", {"python", "diagnostics"}, lease_seconds=10)
    registered = worker.register(now=100)
    assert registered["online"] is True
    assert registered["heartbeat_count"] == 1
    assert "last_seen" not in registered and "last_heartbeat" not in registered
    renewed = worker.heartbeat(now=105)
    assert renewed["online"] is True
    assert renewed["lease_until"] == 115
    assert renewed["heartbeat_count"] == 2


def test_lease_expiry_requires_reregistration():
    worker = AdvancedWorker("brain-worker-02", {"python"}, lease_seconds=5)
    worker.register(now=100)
    assert worker.snapshot(now=106)["online"] is False
    try:
        worker.heartbeat(now=106)
    except RuntimeError as exc:
        assert "LEASE_EXPIRED" in str(exc)
    else:
        raise AssertionError("expired worker heartbeat should be rejected")


def test_simulator_cannot_advertise_real_boot_capability():
    try:
        AdvancedWorker("sim-01", {REAL_BOOT_CAPABILITY}, mode="simulator")
    except ValueError as exc:
        assert "SIMULATOR_CANNOT_ADVERTISE_REAL_BOOT" in str(exc)
    else:
        raise AssertionError("simulator must not advertise real boot")


def test_real_boot_admission_fails_closed_without_all_real_gates():
    worker = AdvancedWorker("real-01", {REAL_BOOT_CAPABILITY}, mode="real_executor")
    worker.register(host_facts={"host_identity_verified": True}, now=100)
    result = worker.admit_task({"task_id": "boot-01", "capability": REAL_BOOT_CAPABILITY}, now=101)
    assert result["admitted"] is False
    assert "KVM_RUNTIME_VERIFIED_NOT_VERIFIED" in result["reasons"]
    assert result["windows_boot_verified"] is False


def test_real_boot_admission_needs_every_gate_but_is_not_execution():
    worker = AdvancedWorker("real-02", {REAL_BOOT_CAPABILITY}, mode="real_executor")
    worker.register(host_facts=real_facts(), now=100)
    result = worker.admit_task({"task_id": "boot-02", "capability": REAL_BOOT_CAPABILITY}, now=101)
    assert result["admitted"] is True
    assert result["decision"] == "ADMISSION_ONLY_NOT_EXECUTED"
    assert result["windows_boot_verified"] is False


def test_missing_task_id_and_capability_are_rejected():
    worker = AdvancedWorker("worker-03", {"python"})
    worker.register(now=10)
    result = worker.admit_task({}, now=11)
    assert result["admitted"] is False
    assert "TASK_ID_REQUIRED" in result["reasons"]
    assert "CAPABILITY_NOT_ADVERTISED" in result["reasons"]


def test_heartbeat_replaces_stale_host_facts():
    worker = AdvancedWorker("real-03", {REAL_BOOT_CAPABILITY}, mode="real_executor")
    worker.register(host_facts=real_facts(), now=100)
    updated = worker.heartbeat(host_facts={"host_identity_verified": True}, now=101)
    result = worker.admit_task({"task_id": "boot-03", "capability": REAL_BOOT_CAPABILITY}, now=102)
    assert updated["online"] is True
    assert result["admitted"] is False
    assert "KVM_RUNTIME_VERIFIED_NOT_VERIFIED" in result["reasons"]
