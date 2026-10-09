from brain_v12.azure_emulator.handoff import certify_default_handoff

def test_handoff_is_short_lived_and_single_use():
    c=certify_default_handoff()
    assert c["schema"]=="BRAIN-REAL-AZURE-HANDOFF-3"
    assert c["provider"]=="brain-emulated-azure"
    assert c["free_only"] is True
    assert c["single_use"] is True
    assert c["expires_at"]>c["issued_at"]
