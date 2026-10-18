import pytest

from brain_v12.brain.bitcoin_nonce_scanner import scan_nonce


def test_scanner_returns_valid_80_byte_candidate_for_easy_target():
    result = scan_nonce(bytes(76), 2**256 - 1, start_nonce=7, max_attempts=3)
    assert result["found"] is True
    assert result["nonce"] == 7
    assert len(bytes.fromhex(result["header_hex"])) == 80
    assert result["attempts"] == 1
    assert result["meets_supplied_target"] is True
    assert result["pool_share_acceptance_verified"] is False
    assert result["mode"] == "OFFLINE_CPU_TEST"


def test_scanner_stops_at_attempt_limit():
    result = scan_nonce(bytes(76), 1, start_nonce=0, max_attempts=2)
    assert result["found"] is False
    assert result["attempts"] == 2
    assert result["pool_share_acceptance_verified"] is False


@pytest.mark.parametrize(
    ("prefix", "target", "start", "attempts", "error"),
    [
        (b"short", 1, 0, 1, "HEADER_PREFIX_MUST_BE_76_BYTES"),
        (bytes(76), 0, 0, 1, "SHARE_TARGET_OUT_OF_RANGE"),
        (bytes(76), 1, -1, 1, "START_NONCE_OUT_OF_RANGE"),
        (bytes(76), 1, 0, 0, "MAX_ATTEMPTS_OUT_OF_RANGE"),
        (bytes(76), 1, 0, 1_000_001, "MAX_ATTEMPTS_OUT_OF_RANGE"),
    ],
)
def test_scanner_rejects_invalid_inputs(prefix, target, start, attempts, error):
    with pytest.raises(ValueError, match=error):
        scan_nonce(prefix, target, start_nonce=start, max_attempts=attempts)


def test_scanner_does_not_wrap_past_nonce_space():
    result = scan_nonce(bytes(76), 1, start_nonce=0xFFFFFFFF, max_attempts=10)
    assert result["attempts"] == 1
    assert result["found"] is False
