import math

import pytest

from brain_v12.brain.mining_controller import (
    HardwareProfile,
    MiningPolicy,
    can_start,
    choose_plan,
    evidence_record,
    profitability_gate,
)


def test_randomx_plan_is_cpu_first_and_plan_only():
    hw = HardwareProfile("linux", "aarch64", 8, 7.5, ())
    plan = choose_plan(hw, "randomx")
    assert plan.miner == "xmrig"
    assert plan.mode == "fast"
    assert plan.execution_mode == "PLAN_ONLY"
    assert not plan.external_miner_execution_allowed
    assert "compatibility recommendation only" in plan.reason


def test_mining_disabled_by_default():
    ok, reason = can_start(
        MiningPolicy(),
        worker_is_user_owned=True,
        running_on_github_actions=False,
    )
    assert not ok
    assert reason == "mining_disabled_by_default"


def test_github_actions_is_blocked():
    policy = MiningPolicy(enabled=True, allow_github_actions=False)
    ok, reason = can_start(
        policy,
        worker_is_user_owned=True,
        running_on_github_actions=True,
    )
    assert not ok
    assert reason == "github_actions_mining_forbidden"


def test_profitability_gate():
    result = profitability_gate(1.0, 0.2, 0.1, 0.1)
    assert result["net_per_hour"] == 0.6
    assert result["profitable"]
    assert result["estimate_only"]
    assert not result["realized_revenue_verified"]


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf, True, "1.0"])
def test_profitability_gate_rejects_non_finite_or_non_numeric_inputs(bad_value):
    with pytest.raises(ValueError):
        profitability_gate(bad_value, 0.0)


@pytest.mark.parametrize(
    "args",
    [
        (-1.0, 0.0),
        (1.0, -0.1),
        (1.0, 0.0, -0.1),
        (1.0, 0.0, 0.0, -0.1),
        (1.0, 0.0, 0.0, 0.0, -0.1),
    ],
)
def test_profitability_gate_rejects_negative_values(args):
    with pytest.raises(ValueError):
        profitability_gate(*args)


def test_zero_gross_revenue_is_never_profitable():
    result = profitability_gate(0.0, 0.0)
    assert result["net_per_hour"] == 0.0
    assert not result["profitable"]


def test_payment_evidence_required_for_verified_received():
    ev = evidence_record(
        worker_id="worker-01",
        algorithm="randomx",
        runtime_seconds=600,
        hashrate=1000,
        accepted_shares=10,
        rejected_shares=1,
        verified_received=0.0,
    )
    assert ev["status"] == "MINING_EVIDENCE_ONLY"


def test_enabled_policy_still_blocks_when_native_backend_is_missing():
    policy = MiningPolicy(enabled=True, allow_github_actions=False)
    ok, reason = can_start(
        policy,
        worker_is_user_owned=True,
        running_on_github_actions=False,
    )
    assert not ok
    assert reason == "brain_owned_mining_backend_not_implemented"


def test_backend_prerequisites_do_not_directly_authorize_execution():
    policy = MiningPolicy(enabled=True, allow_github_actions=False)
    ok, reason = can_start(
        policy,
        worker_is_user_owned=True,
        running_on_github_actions=False,
        brain_owned_backend_implemented=True,
        backend_attested=True,
        pool_endpoint_verified=True,
        credentials_in_secret_store=True,
        resource_budget_verified=True,
        explicit_user_approval=True,
    )
    assert not ok
    assert reason == "separate_execution_review_required"


def test_profitability_gate_rejects_arithmetic_overflow():
    with pytest.raises(ValueError, match="overflowed"):
        profitability_gate(1.0, 1e308, 1e308)

    with pytest.raises(ValueError, match="overflowed"):
        profitability_gate(5e-324, 1e308)


def test_profitability_gate_rejects_integer_too_large_for_float():
    with pytest.raises(ValueError, match="finite number"):
        profitability_gate(10**1000, 0.0)
