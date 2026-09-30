from brain_v12.brain.mining_controller import (
    HardwareProfile,
    MiningPolicy,
    can_start,
    choose_plan,
    evidence_record,
    profitability_gate,
)


def test_randomx_plan_is_cpu_first():
    hw = HardwareProfile("linux", "aarch64", 8, 7.5, ())
    plan = choose_plan(hw, "randomx")
    assert plan.miner == "xmrig"
    assert plan.mode == "fast"


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
