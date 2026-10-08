from economics.opportunity_engine import (
    Opportunity, OpportunityState, can_record_confirmed_revenue,
    create_transition, deduplicate_opportunities, rank_opportunities,
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


def test_transition_emits_audit_event():
    current = Opportunity("x", 100, .5, .8, 2, .1, .1, OpportunityState.DELIVERED)
    updated, event = create_transition(
        current, OpportunityState.PAYMENT_PENDING, "delivery-proof-1"
    )
    assert updated.state is OpportunityState.PAYMENT_PENDING
    assert event.from_state is OpportunityState.DELIVERED
    assert event.to_state is OpportunityState.PAYMENT_PENDING
    assert event.evidence_ref == "delivery-proof-1"


def test_invalid_transition_fails_closed():
    current = Opportunity("x", 100, .5, .8, 2, .1, .1, OpportunityState.DELIVERED)
    try:
        create_transition(current, OpportunityState.PAYMENT_VERIFIED)
        assert False
    except ValueError:
        assert True


def test_ranking_is_deterministic():
    a = Opportunity("a", 100, .8, .8, 2, .1, .1)
    b = Opportunity("b", 50, .8, .8, 2, .1, .1)
    ranked = rank_opportunities([b, a])
    assert ranked[0][0].opportunity_id == "a"
    assert ranked[0][1] > ranked[1][1]


def test_duplicate_opportunities_are_collapsed():
    a = Opportunity("same", 100, .8, .8, 2, .1, .1)
    b = Opportunity("same", 200, .8, .8, 2, .1, .1)
    result = deduplicate_opportunities([a, b])
    assert len(result) == 1
    assert result[0] == a
