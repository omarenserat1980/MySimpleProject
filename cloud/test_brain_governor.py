from cloud.brain_governor import BrainGovernor

def test_governor_blocks_unverified_consequential_action():
    result = BrainGovernor().preflight(
        "publish",
        {"evidence_verified": False, "consequential": True},
    )
    assert result["decision"] == "REVIEW"
    assert "tathabbut" in result["governance"]["review_required"]

def test_governor_blocks_agent_disagreement_for_review():
    result = BrainGovernor().preflight(
        "execute",
        {"evidence_verified": True, "agent_disagreement": True},
    )
    assert result["decision"] == "REVIEW"
    assert "shura" in result["governance"]["review_required"]

def test_governor_has_no_spiritual_claim():
    result = BrainGovernor().preflight("safe", {"evidence_verified": True})
    assert result["literal_spiritual_claim"] is False
