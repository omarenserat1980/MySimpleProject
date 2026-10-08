from economics.opportunity_engine import (
    Opportunity, OpportunityState, can_record_confirmed_revenue,
    score, transition_allowed,
)


def test_score_is_positive_for_valid_opportunity():
    o = Opportunity("x", 100, .5, .8, 2, .1, .1)
    assert score(o) > 0


def test_revenue_requires_payment_verification():
    assert not can_record_confirmed_revenue(OpportunityState.DELIVERED, True)
    assert not can_record_confirmed_revenue(OpportunityState.PAYMENT_VERIFIED, False)
    assert can_record_confirmed_revenue(OpportunityState.PAYMENT_VERIFIED, True)


def test_state_transitions_are_linear():
    assert transition_allowed(OpportunityState.DELIVERED, OpportunityState.PAYMENT_PENDING)
    assert not transition_allowed(OpportunityState.DELIVERED, OpportunityState.PAYMENT_VERIFIED)
