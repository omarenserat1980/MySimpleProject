import pytest

from brain_v12.business.revenue_realization_gate import RevenueGateError, RevenueRealizationGate


@pytest.fixture
def evidence():
    return {
        "task": {"task_id": "task-1", "opportunity_id": "opp-1", "order_id": "order-1",
                 "expected_amount": "12.50", "currency": "JOD", "mode": "production"},
        "worker": {"status": "COMPLETED", "execution_kind": "real", "execution_id": "exec-1",
                   "task_id": "task-1", "opportunity_id": "opp-1", "evidence_ref": "worker-log-1",
                   "mode": "production"},
        "delivery": {"status": "ACCEPTED", "task_id": "task-1", "opportunity_id": "opp-1",
                     "execution_id": "exec-1", "evidence_ref": "delivery-1", "mode": "production"},
        "payment": {"verification_status": "INDEPENDENTLY_VERIFIED", "settlement_status": "SETTLED",
                    "order_id": "order-1", "task_id": "task-1", "opportunity_id": "opp-1",
                    "provider": "paytabs", "transaction_id": "txn-1", "evidence_ref": "provider-proof-1",
                    "amount": "12.50", "currency": "JOD", "mode": "production"},
    }


def test_all_evidence_records_one_revenue_and_retry_is_idempotent(tmp_path, evidence):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    kwargs = {**evidence, "idempotency_key": "realize-1"}
    first = gate.realize(**kwargs)
    second = gate.realize(**kwargs)
    assert first["status"] == "REVENUE_REALIZED" and first["duplicate"] is False
    assert second["duplicate"] is True
    assert gate.summary()["realized_revenue_gross"][0]["entries"] == 1


@pytest.mark.parametrize("change,error", [
    (("worker", "execution_kind", "simulation"), "REAL_WORKER_EXECUTION_REQUIRED"),
    (("worker", "task_id", "other-task"), "WORKER_TASK_MISMATCH"),
    (("delivery", "execution_id", "other-exec"), "DELIVERY_EXECUTION_MISMATCH"),
    (("payment", "verification_status", "UNVERIFIED"), "INDEPENDENT_PAYMENT_PROOF_REQUIRED"),
    (("payment", "amount", "12.51"), "PAYMENT_AMOUNT_MISMATCH"),
    (("payment", "currency", "USD"), "PAYMENT_CURRENCY_MISMATCH"),
])
def test_rejects_invalid_evidence(tmp_path, evidence, change, error):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    part, field, value = change
    evidence[part][field] = value
    with pytest.raises(RevenueGateError, match=error):
        gate.realize(**evidence, idempotency_key="attempt")


def test_provider_transaction_cannot_be_counted_twice(tmp_path, evidence):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    gate.realize(**evidence, idempotency_key="first")
    with pytest.raises(RevenueGateError, match="DUPLICATE_REVENUE_KEY_OR_TRANSACTION"):
        gate.realize(**evidence, idempotency_key="second")


def test_simulation_mode_never_counts_as_revenue(tmp_path, evidence):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    evidence["payment"]["mode"] = "simulation"
    with pytest.raises(RevenueGateError, match="SIMULATED_PAYMENT_REJECTED"):
        gate.realize(**evidence, idempotency_key="demo")


@pytest.mark.parametrize(("part", "error"), [
    ("task", "PRODUCTION_TASK_MODE_REQUIRED"),
    ("worker", "PRODUCTION_WORKER_MODE_REQUIRED"),
    ("delivery", "PRODUCTION_DELIVERY_MODE_REQUIRED"),
    ("payment", "PRODUCTION_PAYMENT_MODE_REQUIRED"),
])
def test_missing_evidence_mode_fails_closed(tmp_path, evidence, part, error):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    evidence[part].pop("mode", None)
    with pytest.raises(RevenueGateError, match=error):
        gate.realize(**evidence, idempotency_key="missing-mode")


def test_costs_are_separate_and_idempotent(tmp_path):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    args = dict(task_id="task-1", opportunity_id="opp-1", amount="2.00",
                currency="JOD", evidence_ref="receipt-1", idempotency_key="cost-1")
    assert gate.record_cost(**args)["duplicate"] is False
    assert gate.record_cost(**args)["duplicate"] is True
    summary = gate.summary()
    assert summary["realized_revenue_gross"] == []
    assert summary["operating_costs_separate"][0]["amount"] == 2.0


def test_activity_records_without_payment_proof_and_never_counts_as_revenue(tmp_path):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    result = gate.record_activity(
        idempotency_key="mining-session-1",
        activity={
            "activity_kind": "MINING_SESSION",
            "mode": "live",
            "activity_status": "OBSERVED",
            "worker_id": "worker-test-1",
            "hashrate": {"value": 125.5, "unit": "H/s"},
            "sha256d_result": {"attempts": 1000, "source": "test-fixture"},
            "accepted_shares": 0,
            "rejected_shares": 1,
            "estimated_amount": "0.02",
            "estimated_currency": "BTC",
            "evidence_ref": "telemetry-test-1",
        },
    )
    assert result["status"] == "ACTIVITY_RECORDED"
    assert result["revenue_status"] == "NOT_REALIZED"
    assert result["payment_status"] == "PAYMENT_UNVERIFIED"
    assert result["estimated_earnings_status"] == "ESTIMATED_UNVERIFIED"
    summary = gate.summary()
    assert summary["realized_revenue_gross"] == []
    assert summary["estimated_earnings_unverified"] == [
        {"currency": "BTC", "mode": "live", "activity_status": "OBSERVED",
         "amount": 0.02, "entries": 1}
    ]
    assert summary["mining_activity_separate"][0]["entries"] == 1


def test_simulation_activity_is_recordable_but_labeled_simulated(tmp_path):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    result = gate.record_activity(
        idempotency_key="sim-1",
        activity={
            "activity_kind": "SIMULATION",
            "mode": "simulation",
            "activity_status": "SIMULATED",
            "hashrate": {"value": 9999, "unit": "H/s"},
        },
    )
    assert result["status"] == "ACTIVITY_RECORDED"
    assert result["mode"] == "simulation"
    assert result["revenue_status"] == "NOT_REALIZED"
    assert gate.summary()["realized_revenue_gross"] == []


def test_activity_idempotency_and_conflict(tmp_path):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    activity = {"activity_kind": "SHARE", "mode": "live", "activity_status": "SUBMITTED",
                "accepted_shares": 0, "rejected_shares": 1}
    first = gate.record_activity(activity=activity, idempotency_key="share-1")
    retry = gate.record_activity(activity=activity, idempotency_key="share-1")
    assert first["duplicate"] is False
    assert retry["duplicate"] is True
    with pytest.raises(RevenueGateError, match="DUPLICATE_ACTIVITY_KEY_CONFLICT"):
        gate.record_activity(
            activity={**activity, "rejected_shares": 2},
            idempotency_key="share-1",
        )


def test_invalid_activity_measurement_is_rejected_without_revenue(tmp_path):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    with pytest.raises(RevenueGateError, match="INVALID_HASHRATE_VALUE"):
        gate.record_activity(
            idempotency_key="bad-hashrate",
            activity={"activity_kind": "HASHRATE", "mode": "live",
                      "hashrate": {"value": float("nan"), "unit": "H/s"}},
        )
    assert gate.summary()["realized_revenue_gross"] == []


def test_simulated_estimates_are_not_aggregated_with_live_estimates(tmp_path):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    gate.record_activity(
        idempotency_key="live-estimate",
        activity={"activity_kind": "MINING_SESSION", "mode": "live",
                  "activity_status": "OBSERVED", "estimated_amount": "0.10",
                  "estimated_currency": "BTC"},
    )
    gate.record_activity(
        idempotency_key="sim-estimate",
        activity={"activity_kind": "SIMULATION", "mode": "simulation",
                  "activity_status": "SIMULATED", "estimated_amount": "9.99",
                  "estimated_currency": "BTC"},
    )
    estimates = gate.summary()["estimated_earnings_unverified"]
    assert estimates == [
        {"currency": "BTC", "mode": "live", "activity_status": "OBSERVED",
         "amount": 0.1, "entries": 1},
        {"currency": "BTC", "mode": "simulation", "activity_status": "SIMULATED",
         "amount": 9.99, "entries": 1},
    ]
    assert gate.summary()["realized_revenue_gross"] == []
