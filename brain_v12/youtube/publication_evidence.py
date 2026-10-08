"""Evidence model for verified YouTube publication."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json

class PublicationState(str, Enum):
    NOT_STARTED="NOT_STARTED"
    UPLOAD_UNKNOWN="UPLOAD_UNKNOWN"
    VERIFYING="VERIFYING"
    PUBLISHED="PUBLISHED"
    NOT_FOUND="NOT_FOUND"
    SAFE_RETRY="SAFE_RETRY"

@dataclass(frozen=True)
class PublicationEvidence:
    video_id: str
    decision_fingerprint: str
    youtube_video_id: str | None
    state: PublicationState
    observed_at: str
    provider_status: str
    original_video_ref: str

    def valid(self) -> bool:
        return bool(
            self.video_id and self.decision_fingerprint and
            self.observed_at and self.provider_status and
            self.original_video_ref and
            self.state != PublicationState.PUBLISHED or
            (self.state == PublicationState.PUBLISHED and bool(self.youtube_video_id))
        )

    def fingerprint(self) -> str:
        payload={k:v for k,v in self.__dict__.items()}
        payload["state"]=self.state.value
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def classify_provider_result(result: dict, *, video_id: str, decision_fingerprint: str,
                             original_video_ref: str, observed_at: str) -> PublicationEvidence:
    youtube_id = result.get("video_id")
    if youtube_id:
        state=PublicationState.PUBLISHED
    elif result.get("status") in {"timeout","network_error","unknown"}:
        state=PublicationState.UPLOAD_UNKNOWN
    else:
        state=PublicationState.NOT_FOUND
    return PublicationEvidence(
        video_id=video_id,
        decision_fingerprint=decision_fingerprint,
        youtube_video_id=str(youtube_id) if youtube_id else None,
        state=state,
        observed_at=observed_at,
        provider_status=str(result.get("status","UNKNOWN")),
        original_video_ref=original_video_ref,
    )

def verify_provider_presence(*, provider_result: dict, expected_video_id: str,
                             expected_decision_fingerprint: str) -> PublicationState:
    if provider_result.get("video_id") and provider_result.get("video_id") == expected_video_id:
        return PublicationState.PUBLISHED
    if provider_result.get("lookup_status") == "found":
        if provider_result.get("decision_fingerprint") == expected_decision_fingerprint:
            return PublicationState.PUBLISHED
        return PublicationState.VERIFYING
    if provider_result.get("lookup_status") == "not_found":
        return PublicationState.SAFE_RETRY
    return PublicationState.UPLOAD_UNKNOWN
