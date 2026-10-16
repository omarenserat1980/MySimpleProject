from brain_v12.brain.mining_controller import (
    HardwareProfile,
    MiningPolicy,
    can_start,
    choose_plan,
    evidence_record,
    bitcoin_sha256d_preflight,
    profitability_gate,
)


def test_randomx_plan_is_brain_owned_plan_only():
    hw = HardwareProfile("linux", "aarch64", 8, 7.5, ("xmrig",))
    plan = choose_plan(hw, "randomx")
    assert plan.miner == "brain-native-backend-pending"
    assert plan.backend == "brain-owned-software-runtime"
    assert plan.mode == "plan-only"
    assert "physical devices are connectivity/observation" in plan.reason


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

def test_bitcoin_sha256d_preflight_fails_closed_by_default():
    result = bitcoin_sha256d_preflight(MiningPolicy())
    assert result["status"] == "BLOCKED"
    assert "MINING_DISABLED_BY_DEFAULT" in result["missing_requirements"]
    assert "VERIFIED_STRATUM_SESSION_REQUIRED" in result["missing_requirements"]
    assert not result["execution_started"]
    assert not result["revenue_verified"]


def test_bitcoin_sha256d_preflight_never_claims_mining_or_revenue():
    policy = MiningPolicy(enabled=True, allow_github_actions=False)
    result = bitcoin_sha256d_preflight(
        policy,
        worker_id="registered-worker",
        worker_identity_verified=True,
        stratum_session_id="session-ref",
        stratum_session_verified=True,
        accepted_share_proof_ref="pool-share-proof-ref",
        accepted_share_proof_verified=True,
        profitability_evidence_ref="economics-proof-ref",
        profitability_verified=True,
        explicit_approval=True,
        worker_is_user_owned=True,
        running_on_github_actions=False,
        current_temperature_c=50.0,
    )
    assert result["status"] == "BLOCKED"
    assert not result["ready_for_review"]
    assert "BRAIN_OWNED_BACKEND_NOT_IMPLEMENTED" in result["missing_requirements"]
    assert "EXTERNAL_WORKER_EXECUTION_FORBIDDEN" in result["missing_requirements"]
    assert not result["execution_started"]
    assert not result["accepted_shares_independently_verified"]
    assert not result["revenue_verified"]


def test_bitcoin_sha256d_preflight_blocks_github_actions_and_thermal_limit():
    policy = MiningPolicy(enabled=True, allow_github_actions=False, max_temperature_c=75.0)
    result = bitcoin_sha256d_preflight(
        policy,
        worker_id="registered-worker",
        worker_identity_verified=True,
        stratum_session_id="session-ref",
        stratum_session_verified=True,
        accepted_share_proof_ref="pool-share-proof-ref",
        accepted_share_proof_verified=True,
        profitability_evidence_ref="economics-proof-ref",
        profitability_verified=True,
        explicit_approval=True,
        worker_is_user_owned=True,
        running_on_github_actions=True,
        current_temperature_c=80.0,
    )
    assert result["status"] == "BLOCKED"
    assert "GITHUB_ACTIONS_MINING_FORBIDDEN" in result["missing_requirements"]
    assert "THERMAL_LIMIT_REACHED" in result["missing_requirements"]

def test_bitcoin_sha256d_plan_is_brain_owned_and_does_not_claim_live_mining():
    from brain_v12.brain.mining_controller import HardwareProfile, choose_plan
    hardware = HardwareProfile("linux", "aarch64", 8, 4.0, ())
    plan = choose_plan(hardware, "sha256d")
    assert plan.algorithm == "sha256d"
    assert plan.backend == "brain-owned-software-runtime"
    assert plan.mode == "plan-only"
    assert "native compute backend is not implemented" in plan.reason
    import pytest
    with pytest.raises(RuntimeError, match="external miner execution is forbidden"):
        choose_plan(hardware, "sha256d", require_installed_miner=True)


def test_enabled_policy_still_blocks_until_brain_backend_exists():
    policy = MiningPolicy(enabled=True)
    ok, reason = can_start(
        policy,
        worker_is_user_owned=True,
        running_on_github_actions=False,
    )
    assert not ok
    assert reason == "brain_owned_mining_backend_not_implemented"

