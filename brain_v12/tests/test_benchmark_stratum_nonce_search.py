"""Tests for the offline Stratum nonce benchmark tool."""
import pytest

from brain_v12.tools.benchmark_stratum_nonce_search import benchmark
from brain_v12.brain.stratum_bounded_nonce_search import MAX_NONCE_ATTEMPTS


def test_benchmark_reports_measured_local_evidence_without_pool_claims():
    result = benchmark(1)
    assert result["evidence_class"] == "LOCAL_SYNTHETIC_SOFTWARE_BENCHMARK"
    assert result["requested_attempts"] == 1
    assert 1 <= result["attempts_checked"] <= 1
    assert result["elapsed_seconds"] >= 0
    assert result["hashes_per_second"] is None or result["hashes_per_second"] > 0
    assert result["synthetic_job"] is True
    assert result["network_used"] is False
    assert result["pool_submission_sent"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["asic_hashrate_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


@pytest.mark.parametrize("attempts", [0, -1, MAX_NONCE_ATTEMPTS + 1, True, "4"])
def test_benchmark_rejects_invalid_attempt_counts(attempts):
    with pytest.raises(ValueError):
        benchmark(attempts)
