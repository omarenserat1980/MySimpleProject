from brain_v12.youtube.publication_evidence import PublicationState
from brain_v12.youtube.publication_state_machine import (
    PublicationAction, next_publication_action
)

def test_requires_auth_waits():
    assert next_publication_action(
        requires_authorization=True, authorized=False,
        evidence_state=PublicationState.NOT_STARTED,
    ) is PublicationAction.WAIT_AUTHORIZATION

def test_unknown_upload_verifies_before_retry():
    assert next_publication_action(
        requires_authorization=True, authorized=True,
        evidence_state=PublicationState.UPLOAD_UNKNOWN,
    ) is PublicationAction.VERIFY

def test_verified_not_found_allows_safe_retry():
    assert next_publication_action(
        requires_authorization=True, authorized=True,
        evidence_state=PublicationState.NOT_FOUND,
    ) is PublicationAction.SAFE_RETRY

def test_published_moves_to_measurement():
    assert next_publication_action(
        requires_authorization=True, authorized=True,
        evidence_state=PublicationState.PUBLISHED,
    ) is PublicationAction.MEASURE
