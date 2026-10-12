from brain_v12.brain.founder_payout_bridge import FounderPayoutBridge

def test_bridge_blocks_unverified_destination():
    b = FounderPayoutBridge()
    r = b.prepare(1000, "JOD", destination_ref=None)
    assert r["status"] == "BLOCKED"

def test_bridge_never_exposes_destination_identity():
    b = FounderPayoutBridge()
    r = b.prepare(1000, "JOD", destination_ref="opaque-ref")
    assert "ooenserat@gmail.com" not in str(r)
