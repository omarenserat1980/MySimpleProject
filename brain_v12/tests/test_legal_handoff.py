from brain_v12.brain.legal_handoff import HandoffState, LegalHandoff
import pytest


def test_handoff_requires_opaque_identity_reference():
    h = LegalHandoff("FOUNDER_IDENTITY_REF")
    assert h.state == HandoffState.VERIFIED_FUNDS


def test_handoff_progression_is_bounded():
    h = LegalHandoff("FOUNDER_IDENTITY_REF")
    for state in [
        HandoffState.LEGAL_HANDOFF_PENDING,
        HandoffState.LAWYER_CANDIDATE_REVIEW,
        HandoffState.LAWYER_AUTHORITY_VERIFIED,
        HandoffState.BENEFICIARY_AUTHORITY_VERIFIED,
        HandoffState.HUMAN_HANDOFF,
        HandoffState.HANDOFF_EVIDENCE_RECORDED,
        HandoffState.CLOSED,
    ]:
        result = h.transition(state, {"authority_ref": "EVIDENCE-REF"})
        assert result["state"] == state.value


def test_raw_identity_or_payment_data_is_rejected():
    h = LegalHandoff("FOUNDER_IDENTITY_REF")
    with pytest.raises(ValueError):
        h.transition(HandoffState.LEGAL_HANDOFF_PENDING, {"national_id": "REDACTED"})


def test_cannot_jump_directly_to_human_handoff():
    h = LegalHandoff("FOUNDER_IDENTITY_REF")
    with pytest.raises(ValueError):
        h.transition(HandoffState.HUMAN_HANDOFF, {"authority_ref": "EVIDENCE-REF"})
