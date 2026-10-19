import pytest

from brain_v12.brain.prototype_capabilities import (
    EvidenceEnginePrototype,
    MiningSupervisorPrototype,
    MiningTelemetry,
    RecoveryManagerPrototype,
    ResourceBudgetPrototype,
    TaskOrchestratorPrototype,
    TaskState,
    VisualAgentPrototype,
    VisualObservation,
)


def test_task_orchestrator_enforces_verified_completion_path():
    tasks = TaskOrchestratorPrototype()
    assert tasks.create("task-1") is TaskState.PENDING
    tasks.transition("task-1", TaskState.RUNNING)
    with pytest.raises(ValueError, match="INVALID_TASK_STATE_TRANSITION"):
        tasks.transition("task-1", TaskState.COMPLETED)
    tasks.transition("task-1", TaskState.VERIFIED)
    tasks.transition("task-1", TaskState.COMPLETED)


def test_resource_budget_prevents_overcommit_and_supports_release():
    budget = ResourceBudgetPrototype({"cpu_units": 4})
    budget.reserve("cpu_units", 3)
    with pytest.raises(ValueError, match="RESOURCE_BUDGET_EXCEEDED"):
        budget.reserve("cpu_units", 2)
    budget.release("cpu_units", 1)
    assert budget.reserved["cpu_units"] == 2


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf"), True, 0, -1])
def test_resource_budget_rejects_invalid_reservation_amounts(amount):
    budget = ResourceBudgetPrototype({"cpu_units": 4})
    with pytest.raises(ValueError, match="INVALID_RESOURCE_AMOUNT"):
        budget.reserve("cpu_units", amount)


@pytest.mark.parametrize("capacity", [float("nan"), float("inf"), float("-inf"), True, -1])
def test_resource_budget_rejects_invalid_capacities(capacity):
    with pytest.raises(ValueError, match="INVALID_RESOURCE_CAPACITY"):
        ResourceBudgetPrototype({"cpu_units": capacity})


def test_resource_budget_rejects_non_finite_or_overcommitted_initial_reservations():
    with pytest.raises(ValueError, match="INVALID_RESERVED_RESOURCE_AMOUNT"):
        ResourceBudgetPrototype({"cpu_units": 4}, {"cpu_units": float("nan")})
    with pytest.raises(ValueError, match="RESOURCE_BUDGET_EXCEEDED"):
        ResourceBudgetPrototype({"cpu_units": 4}, {"cpu_units": 5})


def test_evidence_engine_hash_chain_detects_tampering():
    evidence = EvidenceEnginePrototype()
    evidence.record(kind="test", source="pytest", payload={"passed": True}, evidence_class="local_test")
    evidence.record(kind="status", source="simulator", payload={"state": "ready"})
    assert evidence.verify_chain()
    evidence.records[0]["payload"]["passed"] = False
    assert not evidence.verify_chain()


def test_evidence_engine_isolates_nested_payload_from_caller_mutation():
    payload = {"nested": {"state": "ready"}}
    evidence = EvidenceEnginePrototype()
    returned = evidence.record(kind="status", source="test", payload=payload, evidence_class="local_test")
    payload["nested"]["state"] = "tampered"
    returned["payload"]["nested"]["state"] = "also-tampered"
    assert evidence.records[0]["payload"]["nested"]["state"] == "ready"
    assert evidence.verify_chain()


@pytest.mark.parametrize("payload", [
    {"value": float("nan")},
    {"value": float("inf")},
    {"value": object()},
])
def test_evidence_engine_rejects_non_canonical_payload_values(payload):
    evidence = EvidenceEnginePrototype()
    with pytest.raises(ValueError, match="INVALID_EVIDENCE_PAYLOAD"):
        evidence.record(kind="test", source="pytest", payload=payload)


def test_visual_agent_does_not_claim_screen_capture_and_rejects_low_confidence():
    low = VisualAgentPrototype.assess(VisualObservation("unknown", 0.3))
    assert low["decision"] == "STOP_FOR_REVIEW"
    assert low["screen_capture_performed"] is False
    assert low["device_state_independently_verified"] is False
    high = VisualAgentPrototype.assess(VisualObservation("ready", 0.99))
    assert high["decision"] == "ACCEPT_OBSERVATION"


def test_recovery_manager_uses_bounded_retries_and_stops_on_verified_result():
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("temporary")
        return "ok"

    result = RecoveryManagerPrototype(max_attempts=3).run(operation, verify=lambda x: x == "ok")
    assert result["status"] == "VERIFIED"
    assert result["attempts"] == 2
    assert attempts["count"] == 2


def test_recovery_manager_stops_after_retry_bound():
    result = RecoveryManagerPrototype(max_attempts=2).run(lambda: False, verify=bool)
    assert result["status"] == "FAILED"
    assert result["attempts"] == 2


def test_mining_supervisor_never_promotes_simulation_to_real_mining():
    result = MiningSupervisorPrototype.assess(MiningTelemetry(
        simulated=True, transport_connected=True, tls_authenticated=True,
        worker_active=True, accepted_shares_reported=10,
        independent_pool_confirmation=True, revenue_confirmed=True,
    ))
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False
    assert result["status"] == "NOT_VERIFIED"


def test_mining_supervisor_requires_independent_pool_evidence():
    result = MiningSupervisorPrototype.assess(MiningTelemetry(
        simulated=False, transport_connected=True, tls_authenticated=True,
        worker_active=True, accepted_shares_reported=1,
        independent_pool_confirmation=False,
    ))
    assert result["real_mining_verified"] is False
    assert "independent_pool_confirmation" in result["missing_evidence"]


def test_mining_supervisor_never_trusts_caller_supplied_success_flags():
    result = MiningSupervisorPrototype.assess(MiningTelemetry(
        simulated=False, transport_connected=True, tls_authenticated=True,
        worker_active=True, accepted_shares_reported=1,
        independent_pool_confirmation=True, revenue_confirmed=True,
    ))
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False
    assert result["status"] == "NOT_VERIFIED"
    assert "trusted_server_side_evidence_verifier_not_bound" in result["missing_evidence"]
    assert "Caller-supplied telemetry is not proof" in result["verification_boundary"]


@pytest.mark.parametrize("counter", [-1, True, False, 1.5, "1", None])
def test_mining_supervisor_rejects_invalid_share_counters(counter):
    with pytest.raises(ValueError, match="INVALID_SHARE_COUNTER"):
        MiningSupervisorPrototype.assess(MiningTelemetry(
            accepted_shares_reported=counter,
        ))


def test_mining_supervisor_rejects_wrong_telemetry_type():
    with pytest.raises(ValueError, match="INVALID_MINING_TELEMETRY"):
        MiningSupervisorPrototype.assess({"accepted_shares_reported": 1})


def test_mining_supervisor_fails_closed_when_transport_is_unavailable():
    result = MiningSupervisorPrototype.assess(MiningTelemetry())
    assert result["stop_required"] is True
    assert result["real_mining_verified"] is False

def test_durable_evidence_adapter_persists_and_verifies_in_temporary_sqlite(tmp_path):
    from brain_v12.brain.evidence_store import EvidenceStore
    from brain_v12.brain.prototype_capabilities import DurableEvidenceAdapter

    store = EvidenceStore(tmp_path / "evidence.sqlite3")
    try:
        adapter = DurableEvidenceAdapter(store)
        result = adapter.record(
            task_id="isolated-task",
            kind="test",
            source="pytest",
            payload={"nested": {"state": "ready"}},
            evidence_class="local_test",
        )
        assert result["status"] == "PERSISTED_AND_HASH_VERIFIED"
        assert result["independent_evidence"] is False
        saved = store.get(result["evidence_id"])
        assert saved is not None
        assert saved["verification_status"] == "VERIFIED"
        assert saved["payload"]["payload"]["nested"]["state"] == "ready"
    finally:
        store.close()


def test_durable_evidence_adapter_fails_closed_on_append_and_verifier_errors():
    from brain_v12.brain.prototype_capabilities import DurableEvidenceAdapter

    class BrokenStore:
        def append(self, **kwargs):
            raise RuntimeError("isolated append failure")

    result = DurableEvidenceAdapter(BrokenStore()).record(
        task_id="task", kind="test", source="pytest", payload={}
    )
    assert result["status"] == "PERSISTENCE_FAILED"
    assert result["independent_evidence"] is False


def test_durable_evidence_adapter_requires_exact_verified_status():
    from brain_v12.brain.prototype_capabilities import DurableEvidenceAdapter

    class InconsistentStore:
        def append(self, **kwargs):
            return {"evidence_id": "ev-test", "sha256": "abc"}

        def verify_hash(self, evidence_id):
            return {"ok": True, "status": "TAMPERED"}

    result = DurableEvidenceAdapter(InconsistentStore()).record(
        task_id="task", kind="test", source="pytest", payload={}
    )
    assert result["status"] == "INTEGRITY_CHECK_FAILED"
    assert result["independent_evidence"] is False


@pytest.mark.parametrize("evidence_class", [None, [], {}, 1, True])
def test_durable_evidence_adapter_rejects_non_string_evidence_class(evidence_class):
    from brain_v12.brain.prototype_capabilities import DurableEvidenceAdapter

    class NeverCalledStore:
        def append(self, **kwargs):
            raise AssertionError("invalid evidence class must be rejected before persistence")

    with pytest.raises(ValueError, match="INVALID_EVIDENCE_CLASS"):
        DurableEvidenceAdapter(NeverCalledStore()).record(
            task_id="task", kind="test", source="pytest", payload={},
            evidence_class=evidence_class,
        )


def test_durable_evidence_adapter_fails_closed_when_verifier_raises():
    from brain_v12.brain.prototype_capabilities import DurableEvidenceAdapter

    class VerifierRaisesStore:
        def append(self, **kwargs):
            return {"evidence_id": "ev-test", "sha256": "abc"}

        def verify_hash(self, evidence_id):
            raise RuntimeError("isolated verifier failure")

    result = DurableEvidenceAdapter(VerifierRaisesStore()).record(
        task_id="task", kind="test", source="pytest", payload={}
    )
    assert result["status"] == "HASH_VERIFICATION_FAILED"
    assert result["independent_evidence"] is False


@pytest.mark.parametrize("record", [None, {}, {"evidence_id": "", "sha256": "abc"},
                                    {"evidence_id": "ev-test", "sha256": ""}])
def test_durable_evidence_adapter_rejects_malformed_append_results(record):
    from brain_v12.brain.prototype_capabilities import DurableEvidenceAdapter

    class MalformedStore:
        def append(self, **kwargs):
            return record

    result = DurableEvidenceAdapter(MalformedStore()).record(
        task_id="task", kind="test", source="pytest", payload={}
    )
    assert result["status"] == "PERSISTENCE_RESULT_INVALID"
    assert result["independent_evidence"] is False

@pytest.mark.parametrize(
    "verification",
    [
        {"ok": True, "status": "VERIFIED", "evidence_id": "ev-other", "sha256": "abc"},
        {"ok": True, "status": "VERIFIED", "evidence_id": "ev-test", "sha256": "different"},
        {"ok": True, "status": "VERIFIED"},
    ],
)
def test_durable_evidence_adapter_binds_verification_to_persisted_record(verification):
    from brain_v12.brain.prototype_capabilities import DurableEvidenceAdapter

    class MismatchedVerifierStore:
        def append(self, **kwargs):
            return {"evidence_id": "ev-test", "sha256": "abc"}

        def verify_hash(self, evidence_id):
            return verification

    result = DurableEvidenceAdapter(MismatchedVerifierStore()).record(
        task_id="task", kind="test", source="pytest", payload={}
    )
    assert result["status"] == "INTEGRITY_CHECK_FAILED"
    assert result["independent_evidence"] is False

