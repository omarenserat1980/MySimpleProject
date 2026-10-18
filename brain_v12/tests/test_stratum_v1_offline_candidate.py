import pytest

from brain_v12.brain.stratum_v1_offline_candidate import (
    LEGACY_PREVHASH_DIALECT,
    build_offline_stratum_candidate,
)


def notify():
    return [
        "offline-job-1",
        "00" * 32,
        "01020304",
        "aabbccdd",
        ["11" * 32],
        "01000000",
        "1d00ffff",
        "495fab29",
        True,
    ]


def build(**overrides):
    args = {
        "extranonce1_hex": "a1b2",
        "extranonce2_hex": "c3d4",
        "extranonce2_size": 2,
        "version_header_hex": "01000000",
        "ntime_header_hex": "29ab5f49",
        "nbits_header_hex": "ffff001d",
        "nonce": 0x12345678,
        "share_target": (1 << 256) - 1,
        "prevhash_dialect": LEGACY_PREVHASH_DIALECT,
    }
    args.update(overrides)
    return build_offline_stratum_candidate(notify(), **args)


def test_offline_pipeline_builds_header_from_notify_coinbase_and_merkle():
    result = build()
    assert result["job_id"] == "offline-job-1"
    assert result["clean_jobs"] is True
    assert result["coinbase_bytes"] == len(bytes.fromhex("01020304a1b2c3d4aabbccdd"))
    assert len(bytes.fromhex(result["merkle_root_raw_hex"])) == 32
    assert result["header_bytes"] == 80
    assert bytes.fromhex(result["header_hex"])[-4:] == bytes.fromhex("78563412")
    assert result["status"] == "LOCAL_SHARE_TARGET_MET"
    assert result["share_target_met"] is True
    assert result["network_target_met"] is None


def test_offline_pipeline_keeps_live_and_revenue_evidence_false():
    result = build(network_target=1)
    assert result["network_target_met"] is False
    assert result["execution_mode"] == "OFFLINE_CANDIDATE_ONLY"
    assert result["transport_connected"] is False
    assert result["nonce_search_executed"] is False
    assert result["live_execution_allowed"] is False
    assert result["pool_connection_opened"] is False
    assert result["credentials_loaded"] is False
    assert result["share_submitted"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["revenue_verified"] is False
    assert result["evidence_class"] == "OFFLINE_STRATUM_JOB_CANDIDATE_ONLY"


def test_unknown_prevhash_dialect_fails_closed():
    with pytest.raises(ValueError, match="UNCONFIRMED_STRATUM_PREVHASH_DIALECT"):
        build(prevhash_dialect="unknown-or-guessed")


def test_malformed_notify_fails_before_candidate_is_created():
    malformed = notify()
    malformed[1] = "00"
    with pytest.raises(ValueError, match="INVALID_LENGTH_PREVHASH"):
        build_offline_stratum_candidate(
            malformed,
            extranonce1_hex="a1b2",
            extranonce2_hex="c3d4",
            extranonce2_size=2,
            version_header_hex="01000000",
            ntime_header_hex="29ab5f49",
            nbits_header_hex="ffff001d",
            nonce=0,
            share_target=(1 << 256) - 1,
            prevhash_dialect=LEGACY_PREVHASH_DIALECT,
        )


def test_network_target_validation_fails_closed():
    with pytest.raises(ValueError, match="NETWORK_TARGET_OUT_OF_RANGE"):
        build(network_target=True)



def test_share_target_failure_is_not_reported_as_a_met_share():
    result = build(share_target=1, network_target=(1 << 256) - 1)
    assert result["share_target_met"] is False
    assert result["status"] == "SHARE_TARGET_NOT_MET"
    assert result["network_target_met"] is True
    assert result["pool_acceptance_verified"] is False
    assert result["revenue_verified"] is False


def test_share_target_and_network_target_are_independent_checks():
    # The maximal share target accepts this local hash, while a stricter
    # network target can remain unmet. Neither result means pool acceptance.
    result = build(share_target=(1 << 256) - 1, network_target=1)
    assert result["share_target_met"] is True
    assert result["status"] == "LOCAL_SHARE_TARGET_MET"
    assert result["network_target_met"] is False
    assert result["pool_acceptance_verified"] is False
