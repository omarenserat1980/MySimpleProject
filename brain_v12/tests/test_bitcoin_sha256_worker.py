from brain_v12.brain.bitcoin_sha256_worker import double_sha256, scan_nonce_range


def test_double_sha256_is_real_and_deterministic():
    header = bytes(80)
    first = double_sha256(header)
    second = double_sha256(header)
    assert len(first) == 32
    assert first == second


def test_nonce_scan_executes_real_hashes():
    result = scan_nonce_range(bytes(76), start_nonce=0, end_nonce=3, target=0)
    assert result.nonces_tested == 4
    assert result.matching_nonce is None
    assert result.hashes_per_second > 0


def test_nonce_scan_can_open_on_easy_target():
    result = scan_nonce_range(bytes(76), start_nonce=0, end_nonce=0, target=(1 << 256) - 1)
    assert result.nonces_tested == 1
    assert result.matching_nonce == 0
    assert result.matching_hash_hex is not None
