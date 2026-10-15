"""Tests for the bounded, local SHA-256d benchmark."""
import hashlib

import pytest

from brain_v12.brain.bitcoin_hash_benchmark import (
    HEADER_BYTES, benchmark_header_hashing, sha256d,
)


def test_sha256d_matches_independent_standard_library_composition():
    payload = b"Electronic Brain Bitcoin Lab"
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()
    assert sha256d(payload) == expected


def test_benchmark_returns_measured_rate_and_never_claims_mining():
    result = benchmark_header_hashing(duration_seconds=0.05, max_hashes=200)
    assert result["ok"] is True
    assert result["mode"] == "LOCAL_BENCHMARK_ONLY"
    assert result["header_bytes"] == HEADER_BYTES
    assert 1 <= result["hashes_completed"] <= 200
    assert result["hashrate_hs"] > 0
    assert len(result["last_digest_hex"]) == 64
    assert result["pool_connected"] is False
    assert result["real_bitcoin_mining"] is False
    assert result["revenue_verified"] is False


@pytest.mark.parametrize("header", [b"", b"x" * 79, b"x" * 81])
def test_rejects_invalid_header_length(header):
    with pytest.raises(ValueError, match="HEADER_MUST_BE_EXACTLY_80_BYTES"):
        benchmark_header_hashing(header=header, duration_seconds=0.05)


@pytest.mark.parametrize("duration", [0, -1, 3.1, True])
def test_rejects_unsafe_duration(duration):
    with pytest.raises(ValueError):
        benchmark_header_hashing(duration_seconds=duration)


@pytest.mark.parametrize("max_hashes", [0, -1, 100001, True])
def test_rejects_unbounded_hash_count(max_hashes):
    with pytest.raises(ValueError):
        benchmark_header_hashing(max_hashes=max_hashes)
