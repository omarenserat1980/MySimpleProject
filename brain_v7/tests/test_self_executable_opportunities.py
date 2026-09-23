from brain_v7.braincore_v2.self_executable_opportunities import (
    catalog,
    classify,
    select_autonomous_work,
)


def test_catalog_has_local_work():
    assert len(catalog()) >= 5
    assert select_autonomous_work()


def test_local_execution_does_not_claim_payment():
    result = classify(can_create_artifact=True, has_required_input=True)
    assert result["status"] == "SELF_EXECUTABLE"
    assert result["payment_verified"] is False
    assert result["income_claim_allowed"] is False


def test_missing_input_blocks():
    result = classify(can_create_artifact=True, has_required_input=False)
    assert result["status"] == "NOT_READY"
