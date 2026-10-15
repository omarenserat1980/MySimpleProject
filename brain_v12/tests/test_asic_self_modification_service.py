from brain_v12.brain.asic_self_modification_service import review_candidate


def test_service_never_enables_merge_or_device_writes():
    result = review_candidate(
        candidate_branch="brain/asic-update",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
        check_results={"unit": "passed", "rtl": "passed", "synthesis": "passed", "security": "passed"},
    )
    assert result["decision"] == "READY_FOR_REVIEW"
    assert result["autonomous_execution_enabled"] is False
    assert result["merge_enabled"] is False
    assert result["device_write_enabled"] is False


def test_service_blocks_missing_ci_results():
    result = review_candidate(
        candidate_branch="brain/asic-update",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
        check_results={"unit": "passed"},
    )
    assert result["decision"] == "REJECT"
