from brain_v12.customer_cases import CustomerCaseStore


def test_case_and_approval_require_explicit_decision(tmp_path):
    store = CustomerCaseStore(tmp_path / "cases.db")
    case_id = store.create_case(42)
    assert store.get_case(case_id)["status"] == "OPEN"
    approval_id = store.request_approval(case_id)
    assert store.get_case(case_id)["status"] == "APPROVAL_REQUIRED"
    approval = store.decide(approval_id, "operator", True, "approved after review")
    assert approval["status"] == "APPROVED"
    assert store.get_case(case_id)["status"] == "APPROVED"
