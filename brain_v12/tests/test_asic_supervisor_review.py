from brain_v12.brain.asic_supervisor_review import review_candidate_with_supervisor


class FakeSupervisor:
    def __init__(self):
        self.events = []

    def _event(self, job_id, event, data=None):
        self.events.append({"job_id": job_id, "event": event, "data": data or {}})


def passed_checks():
    return {"unit": "passed", "rtl": "passed", "synthesis": "passed", "security": "passed"}


def test_review_is_audited_and_never_authorizes_execution():
    supervisor = FakeSupervisor()
    result = review_candidate_with_supervisor(
        supervisor,
        job_id="job-asic-001",
        candidate_branch="brain/asic-change",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
        check_results=passed_checks(),
    )
    assert result["decision"] == "READY_FOR_REVIEW"
    assert result["autonomous_execution_enabled"] is False
    assert result["merge_enabled"] is False
    assert result["device_write_enabled"] is False
    assert len(supervisor.events) == 1
    assert supervisor.events[0]["event"] == "asic_self_modification_review"
    assert supervisor.events[0]["data"]["real_mining_verified"] is False


def test_rejected_review_is_audited():
    supervisor = FakeSupervisor()
    result = review_candidate_with_supervisor(
        supervisor,
        job_id="job-asic-002",
        candidate_branch="main",
        changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
        check_results=passed_checks(),
    )
    assert result["decision"] == "REJECT"
    assert "DIRECT_MAIN_MODIFICATION_FORBIDDEN" in result["reasons"]
    assert supervisor.events[0]["data"]["decision"] == "REJECT"


def test_empty_job_id_is_rejected_before_review():
    supervisor = FakeSupervisor()
    try:
        review_candidate_with_supervisor(
            supervisor,
            job_id=" ",
            candidate_branch="brain/asic-change",
            changed_paths=["brain_v12/asic/rtl/brain_asic_core.sv"],
            check_results=passed_checks(),
        )
    except ValueError as exc:
        assert str(exc) == "JOB_ID_REQUIRED"
    else:
        raise AssertionError("Expected empty job id to be rejected")
    assert supervisor.events == []
