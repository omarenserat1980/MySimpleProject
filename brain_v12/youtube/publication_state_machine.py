"""Execution state machine for safe YouTube publication."""
from __future__ import annotations
from enum import Enum

from .publication_evidence import PublicationState


class PublicationAction(str, Enum):
    WAIT_AUTHORIZATION="WAIT_AUTHORIZATION"
    PUBLISH="PUBLISH"
    VERIFY="VERIFY"
    MEASURE="MEASURE"
    SAFE_RETRY="SAFE_RETRY"
    STOP="STOP"


def next_publication_action(
    *,
    requires_authorization: bool,
    authorized: bool,
    evidence_state: PublicationState,
) -> PublicationAction:
    if not requires_authorization:
        return PublicationAction.STOP
    if not authorized:
        return PublicationAction.WAIT_AUTHORIZATION
    if evidence_state is PublicationState.UPLOAD_UNKNOWN:
        return PublicationAction.VERIFY
    if evidence_state is PublicationState.VERIFYING:
        return PublicationAction.VERIFY
    if evidence_state is PublicationState.NOT_FOUND:
        return PublicationAction.SAFE_RETRY
    if evidence_state is PublicationState.SAFE_RETRY:
        return PublicationAction.SAFE_RETRY
    if evidence_state is PublicationState.PUBLISHED:
        return PublicationAction.MEASURE
    return PublicationAction.PUBLISH
