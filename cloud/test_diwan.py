import pytest
from cloud.diwan import (
    Correspondence, CorrespondenceState, RecordState, CaseFile,
    DocumentVersion, RoutingAssignment, archive_eligible, content_hash,
    register_number,
)


def test_inbound_lifecycle_and_audit_events():
    c = Correspondence(direction="INBOUND", subject="Request", channel="EMAIL")
    c.transition(CorrespondenceState.REGISTERED, "diwan")
    c.transition(CorrespondenceState.CLASSIFIED, "diwan")
    c.transition(CorrespondenceState.ROUTED, "secretariat")
    assert c.state is CorrespondenceState.ROUTED
    assert len(c.events) == 3


def test_invalid_transition_is_rejected():
    c = Correspondence(direction="INBOUND", subject="Request", channel="PORTAL")
    with pytest.raises(ValueError):
        c.transition(CorrespondenceState.ARCHIVED, "attacker")


def test_case_file_links_operational_records():
    case = CaseFile(title="Customer process", owner_type="CUSTOMER", owner_id="cust-1")
    case.correspondence_ids.append("corr-1")
    case.document_ids.append("doc-1")
    case.approval_ids.append("approval-1")
    assert case.correspondence_ids == ["corr-1"]
    assert case.document_ids == ["doc-1"]
    assert case.approval_ids == ["approval-1"]


def test_document_versions_are_explicit():
    v1 = DocumentVersion("doc-1", 1, "contract.pdf", "blob:1", content_hash(b"one"))
    v2 = DocumentVersion("doc-1", 2, "contract.pdf", "blob:2", content_hash(b"two"), supersedes=1)
    assert v2.version == 2
    assert v2.supersedes == v1.version
    assert v1.content_sha256 != v2.content_sha256


def test_routing_and_archive_rules():
    r = RoutingAssignment("corr-1", "commercial-agent", "secretariat")
    assert r.status == "ASSIGNED"
    assert archive_eligible(RecordState.CLOSED)
    assert not archive_eligible(RecordState.ACTIVE)
    assert not archive_eligible(RecordState.CLOSED, legal_hold=True)


def test_stable_numbering():
    assert register_number("IN", 7, 2026) == "IN-2026-000007"
