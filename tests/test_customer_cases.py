from brain_v12.customer_cases import CustomerCaseStore


def test_case_has_auditable_events(tmp_path):
    store = CustomerCaseStore(tmp_path / "cases.db")
    case_id = store.create_case(42)
    approval_id = store.request_approval(case_id)
    store.decide(approval_id, "operator", True, "reviewed")
    events = store.events(case_id)
    assert [e["event_type"] for e in events] == ["CASE_CREATED", "APPROVAL_REQUESTED", "APPROVAL_DECIDED"]
    assert all(len(e["payload_hash"]) == 64 for e in events)
