from economics.economic_decision import Decision, decide
from economics.economic_memory import EconomicEstimate
from economics.opportunity_engine import Opportunity
from economics.opportunity_verifier import VerificationResult


def opportunity():
    return Opportunity("x", 100, .8, .8, 2, .1, .1)


def verified():
    return VerificationResult("x", True, (), 1.0, "a" * 64)


def test_unverified_opportunity_is_rejected():
    result = decide(
        opportunity(), 10,
        VerificationResult("x", False, ("stale_source",), 0.8, "a" * 64),
        EconomicEstimate("x", .5, .5, 2),
    )
    assert result.decision is Decision.REJECT
    assert "stale_source" in result.reasons


def test_low_confidence_is_held():
    result = decide(
        opportunity(), 10,
        VerificationResult("x", True, (), 0.5, "a" * 64),
        EconomicEstimate("x", .5, .5, 2),
    )
    assert result.decision is Decision.HOLD


def test_no_history_is_held():
    result = decide(
        opportunity(), 10, verified(),
        EconomicEstimate("x", .5, .5, 0),
    )
    assert result.decision is Decision.HOLD
    assert "no_historical_evidence" in result.reasons


def test_good_verified_opportunity_can_proceed():
    result = decide(
        opportunity(), 10, verified(),
        EconomicEstimate("x", .7, .2, 10),
    )
    assert result.decision is Decision.PROCEED
    assert result.reasons == ()
