from cloud.windows_guest_attestation import validate_attestation

def test_attestation_requires_windows_server_2025():
    ok, reason = validate_attestation({
        "verified_os": False,
        "architecture": "x86_64",
        "guest_identity": "abc",
    })
    assert not ok
    assert reason == "WINDOWS_SERVER_2025_NOT_VERIFIED"

def test_attestation_requires_identity():
    ok, reason = validate_attestation({
        "verified_os": True,
        "architecture": "x86_64",
        "guest_identity": "",
    })
    assert not ok
    assert reason == "GUEST_IDENTITY_MISSING"

def test_valid_attestation():
    ok, reason = validate_attestation({
        "verified_os": True,
        "architecture": "x86_64",
        "guest_identity": "abc",
    })
    assert ok
    assert reason == "OK"
