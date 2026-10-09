from cloud.windows_node_attestation import bind_or_verify

def test_first_attestation_binds_identity():
    ok, reason = bind_or_verify({}, {"verified_os": True, "guest_identity": "abc"})
    assert ok
    assert reason == "IDENTITY_BOUND"

def test_matching_identity_is_accepted():
    ok, reason = bind_or_verify({"guest_identity": "abc"}, {"verified_os": True, "guest_identity": "abc"})
    assert ok
    assert reason == "IDENTITY_MATCH"

def test_identity_drift_is_rejected():
    ok, reason = bind_or_verify({"guest_identity": "abc"}, {"verified_os": True, "guest_identity": "xyz"})
    assert not ok
    assert reason == "GUEST_IDENTITY_DRIFT"
