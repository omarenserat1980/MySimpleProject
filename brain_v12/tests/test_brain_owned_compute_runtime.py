from brain_v12.brain.brain_owned_compute_runtime import (
    double_sha256,
    execution_host_gate,
    is_android_or_termux_runtime,
    search_nonce,
    validate_header,
)


def test_sha256d_is_real_double_hash():
    assert double_sha256(b"abc").hex() == (
        "4f8b42c22dd3729b519ba6f68d2da7cc"
        "5b2d606d05daed5ad5128cc03e6c6358"
    )


def test_search_nonce_finds_valid_nonce_for_easy_target():
    header = bytes(80)
    result = search_nonce(header, (1 << 256) - 1, max_hashes=1)
    assert result.found is True
    assert result.nonce == 0
    assert result.hashes_checked == 1
    assert result.status == "NONCE_FOUND_UNSUBMITTED"


def test_search_nonce_is_bounded_and_does_not_claim_pool_acceptance():
    result = search_nonce(bytes(80), 1, max_hashes=2)
    assert result.found is False
    assert result.hashes_checked == 2
    assert result.status == "NONCE_NOT_FOUND_WITHIN_BOUND"


def test_invalid_header_is_rejected():
    try:
        validate_header(b"short")
    except ValueError as exc:
        assert str(exc) == "BITCOIN_HEADER_MUST_BE_80_BYTES"
    else:
        raise AssertionError("invalid header was accepted")


def test_execution_gate_fails_closed_without_real_host_and_pool_adapter():
    result = execution_host_gate(
        attested_brain_compute_host=False,
        explicit_approval=False,
        pool_adapter_ready=False,
        resource_budget_verified=False,
        physical_gateway_only=True,
    )
    assert result["status"] == "BLOCKED"
    assert result["execution_allowed"] is False
    assert result["execution_started"] is False
    assert result["real_mining_verified"] is False
    assert "BRAIN_COMPUTE_HOST_NOT_ATTESTED" in result["blockers"]
    assert "STRATUM_POOL_ADAPTER_NOT_IMPLEMENTED" in result["blockers"]
    assert "ZERO_COST_COMPUTE_RESOURCE_NOT_VERIFIED" in result["blockers"]


def test_android_termux_is_not_accepted_as_compute_host(monkeypatch):
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.delenv("ANDROID_ROOT", raising=False)
    monkeypatch.delenv("ANDROID_DATA", raising=False)
    monkeypatch.delenv("TERMUX_VERSION", raising=False)
    assert is_android_or_termux_runtime() is True
    result = execution_host_gate(
        attested_brain_compute_host=True,
        explicit_approval=True,
        pool_adapter_ready=True,
        resource_budget_verified=True,
        physical_gateway_only=True,
    )
    assert result["execution_allowed"] is False
    assert "PHYSICAL_ANDROID_GATEWAY_COMPUTATION_FORBIDDEN" in result["blockers"]
