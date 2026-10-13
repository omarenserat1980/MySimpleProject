import pytest

from brain_v12.business.revenue_realization_gate import RevenueGateError, RevenueRealizationGate


@pytest.fixture
def evidence():
    return {
        "task": {"task_id": "task-1", "opportunity_id": "opp-1", "order_id": "order-1",
                 "expected_amount": "12.50", "currency": "JOD", "mode": "production"},
        "worker": {"status": "COMPLETED", "execution_kind": "real", "execution_id": "exec-1",
                   "task_id": "task-1", "opportunity_id": "opp-1", "evidence_ref": "worker-log-1"},
        "delivery": {"status": "ACCEPTED", "task_id": "task-1", "opportunity_id": "opp-1",
                     "execution_id": "exec-1", "evidence_ref": "delivery-1"},
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


def test_costs_are_separate_and_idempotent(tmp_path):
    gate = RevenueRealizationGate(tmp_path / "ledger.sqlite")
    args = dict(task_id="task-1", opportunity_id="opp-1", amount="2.00",
                currency="JOD", evidence_ref="receipt-1", idempotency_key="cost-1")
    assert gate.record_cost(**args)["duplicate"] is False
    assert gate.record_cost(**args)["duplicate"] is True
    summary = gate.summary()
    assert summary["realized_revenue_gross"] == []
    assert summary["operating_costs_separate"][0]["amount"] == 2.0
