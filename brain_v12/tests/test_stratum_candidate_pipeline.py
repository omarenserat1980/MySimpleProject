import pytest

from brain_v12.brain.bitcoin_header import sha256d
from brain_v12.brain.stratum_candidate_pipeline import (
    prepare_and_search_job,
    validate_job_network_target,
)
from brain_v12.brain.stratum_v1_jobs import StratumJob


def sample_job():
    return StratumJob.from_notify([
        "offline-job-1", "00" * 32, "01020304", "aabbccdd", [],
        "01000000", "ffff001d", "29ab5f49", True,
    ])


def test_offline_pipeline_builds_and_revalidates_candidate():
    result = prepare_and_search_job(
        sample_job(), extranonce1_hex="a1b2", extranonce2_hex="c3d4",
        extranonce2_size=2, prevhash_wire_hex="00" * 32,
        share_target=(1 << 256) - 1, start_nonce=0, max_hashes=1,
    )
    assert result.status == "NONCE_FOUND_UNSUBMITTED"
    assert result.header_bytes is not None and len(result.header_bytes) == 80
    assert result.nonce == 0
    assert result.hash_display_hex == sha256d(result.header_bytes)[::-1].hex()
    assert result.meets_share_target is True
    assert result.pool_contacted is False
    assert result.share_submitted is False
    assert result.pool_acceptance_verified is False
    assert result.revenue_verified is False


def test_offline_pipeline_keeps_share_target_separate_from_nbits():
    job = sample_job()
    diag = validate_job_network_target(job)
    assert diag["share_target_supplied_separately"] is True
    assert diag["pool_acceptance_verified"] is False
    # An intentionally impossible target stops after the configured bounded work.
    result = prepare_and_search_job(
        job, extranonce1_hex="a1b2", extranonce2_hex="c3d4", extranonce2_size=2,
        prevhash_wire_hex="00" * 32, share_target=1, start_nonce=0, max_hashes=2,
    )
    assert result.status == "NONCE_NOT_FOUND_WITHIN_BOUND"
    assert result.hashes_checked == 2
    assert result.header_bytes is None


def test_pipeline_rejects_implicit_or_malformed_prevhash_order():
    with pytest.raises(ValueError, match="INVALID_PREVHASH_WIRE_WIDTH"):
        prepare_and_search_job(
            sample_job(), extranonce1_hex="a1b2", extranonce2_hex="c3d4",
            extranonce2_size=2, prevhash_wire_hex="00", share_target=(1 << 256) - 1,
            max_hashes=1,
        )


def test_pipeline_requires_validated_job_type():
    with pytest.raises(ValueError, match="VALIDATED_STRATUM_JOB_REQUIRED"):
        prepare_and_search_job(
            {}, extranonce1_hex="a1b2", extranonce2_hex="c3d4", extranonce2_size=2,
            prevhash_wire_hex="00" * 32, share_target=(1 << 256) - 1, max_hashes=1,
        )
