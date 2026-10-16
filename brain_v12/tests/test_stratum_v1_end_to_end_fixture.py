"""Synthetic end-to-end regression vector for offline Stratum V1 assembly.

This fixture exercises every local transformation, but is deliberately not
presented as a captured Braiins/pool job or live-interoperability evidence.
Expected bytes/hash were independently calculated with hashlib SHA256d.
"""
from brain_v12.brain.stratum_candidate_pipeline import prepare_and_search_job
from brain_v12.brain.stratum_v1_jobs import StratumJob, build_coinbase, merkle_root_from_coinbase


SYNTHETIC_NOTIFY = [
    "synthetic-e2e-001",
    "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
    "01020304",
    "aabbccdd",
    ["11" * 32, "22" * 32],
    "01000000",
    "ffff001d",
    "29ab5f49",
    True,
]
EXTRANONCE1 = "a1b2"
EXTRANONCE2 = "c3d4"
EXTRANONCE2_SIZE = 2
# Explicit synthetic serialized-header prevhash; this is not inferred from
# SYNTHETIC_NOTIFY and is not a claim about any real pool's byte-order dialect.
PREVHASH_WIRE_HEX = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
EXPECTED_COINBASE_HEX = "01020304a1b2c3d4aabbccdd"
EXPECTED_MERKLE_ROOT_RAW_HEX = "0ca64eccf882e40d119cebe191c968272b3d1a990d2be4130227ea0324a56c5c"
EXPECTED_HEADER_HEX = (
    "01000000"
    "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    "0ca64eccf882e40d119cebe191c968272b3d1a990d2be4130227ea0324a56c5c"
    "29ab5f49ffff001d00000000"
)
EXPECTED_SHA256D_DISPLAY_HEX = "9929179435bfaa3e04d127018ec3e0089a0b68dd8c711577c765b3020d030234"


def test_synthetic_notify_to_coinbase_merkle_header_and_hash_vector():
    job = StratumJob.from_notify(SYNTHETIC_NOTIFY)
    coinbase = build_coinbase(job, EXTRANONCE1, EXTRANONCE2, EXTRANONCE2_SIZE)
    assert coinbase.hex() == EXPECTED_COINBASE_HEX

    merkle_root = merkle_root_from_coinbase(coinbase, job.merkle_branch_hex)
    assert merkle_root.hex() == EXPECTED_MERKLE_ROOT_RAW_HEX

    result = prepare_and_search_job(
        job,
        extranonce1_hex=EXTRANONCE1,
        extranonce2_hex=EXTRANONCE2,
        extranonce2_size=EXTRANONCE2_SIZE,
        prevhash_wire_hex=PREVHASH_WIRE_HEX,
        share_target=(1 << 256) - 1,
        start_nonce=0,
        max_hashes=1,
    )
    assert result.status == "NONCE_FOUND_UNSUBMITTED"
    assert result.header_bytes is not None
    assert result.header_bytes.hex() == EXPECTED_HEADER_HEX
    assert len(result.header_bytes) == 80
    assert result.merkle_root_raw_hex == EXPECTED_MERKLE_ROOT_RAW_HEX
    assert result.nonce == 0
    assert result.hash_display_hex == EXPECTED_SHA256D_DISPLAY_HEX
    assert result.hashes_checked == 1
    assert result.meets_share_target is True
    assert result.pool_contacted is False
    assert result.share_submitted is False
    assert result.pool_acceptance_verified is False
    assert result.revenue_verified is False
