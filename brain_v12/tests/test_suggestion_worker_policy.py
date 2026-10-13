from brain_v12.brain.suggestion_worker_policy import (
    REAL_BOOT_CAPABILITY,
    evaluate_suggestion_handoff,
)


def approved_suggestion():
    return {
        "suggestion_id": "sug-123",
        "incident_id": "inc-456",
        "status": "APPROVED",
        "payload": {
            "incident_id": "inc-456",
            "problem_summary": "Worker heartbeat expired",
            "supporting_evidence": ["error-event-1", "trace-2"],
            "implementation_plan": ["reproduce", "patch", "test"],
            "test_plan": ["focused regression tests"],
            "rollback_plan": ["revert patch and rerun baseline"],
            "risk_assessment": "Low if isolated",
        },
    }


def test_approved_suggestion_creates_candidate_not_execution():
    result = evaluate_suggestion_handoff(approved_suggestion(), requested_capability="diagnostics")
    assert result["ok"] is True
    assert result["decision"] == "CANDIDATE_ONLY_NOT_EXECUTABLE"
    assert result["candidate"]["execution_authorized"] is False
    assert result["candidate"]["execution_claim"] == "NONE"
    assert result["windows_boot_verified"] is False


def test_unapproved_chatgpt_advice_cannot_be_handed_off():
    suggestion = approved_suggestion()
    suggestion["status"] = "READY_FOR_REVIEW"
    result = evaluate_suggestion_handoff(suggestion, requested_capability="diagnostics")
    assert result["ok"] is False
    assert "BRAIN_REVIEW_APPROVAL_REQUIRED" in result["reasons"]
    assert result["candidate"] is None


def test_missing_evidence_test_or_rollback_denies_handoff():
    suggestion = approved_suggestion()
    suggestion["payload"]["supporting_evidence"] = []
    suggestion["payload"]["rollback_plan"] = []
    result = evaluate_suggestion_handoff(suggestion, requested_capability="diagnostics")
    assert result["ok"] is False
    assert "SUPPORTING_EVIDENCE_REQUIRED" in result["reasons"]
    assert "ROLLBACK_PLAN_REQUIRED" in result["reasons"]


def test_chatgpt_suggestion_never_bypasses_real_boot_worker_gates():
    result = evaluate_suggestion_handoff(
        approved_suggestion(), requested_capability=REAL_BOOT_CAPABILITY
    )
    assert result["ok"] is False
    assert "REAL_BOOT_REQUIRES_SEPARATE_TRUSTED_WORKER_ADMISSION" in result["reasons"]
    assert result["execution_authorized"] is False
    assert result["windows_boot_verified"] is False


def test_invalid_suggestion_is_denied():
    result = evaluate_suggestion_handoff({}, requested_capability="")
    assert result["ok"] is False
    assert "SUGGESTION_ID_REQUIRED" in result["reasons"]
    assert "TARGET_CAPABILITY_REQUIRED" in result["reasons"]
