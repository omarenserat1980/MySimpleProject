from pathlib import Path

from brain_v12.business.customer_activity_supervisor import CustomerActivitySupervisor


def _write(root: Path, name: str, payload: dict):
    p = root / name
    p.write_text(__import__("json").dumps(payload), encoding="utf-8")


def test_report_lists_customer_activities(tmp_path):
    customers = tmp_path / "customer_requests"
    accounts = tmp_path / "client_accounts"
    customers.mkdir()
    accounts.mkdir()
    _write(customers, "c1.json", {
        "request_id": "C-1",
        "display_name": "Customer One",
        "customer_type": "COMPANY",
        "service": "windows",
        "need": "server",
        "status": "RUNNING",
        "external_actions": [{"action": "SEND_MESSAGE", "message_id": "M-1", "status": "QUEUED_FOR_CONNECTOR"}],
    })
    _write(accounts, "a1.json", {
        "client_id": "CLIENT-1",
        "display_name": "Client One",
        "orders": [{"order_id": "O-1", "service": "cloud", "need": "vm", "state": "NEW"}],
    })
    report = CustomerActivitySupervisor(tmp_path).report()
    assert report["customer_count"] == 2
    assert report["unfinished_activity_count"] == 3


def test_continuation_never_claims_completion_without_structured_verification(tmp_path):
    customers = tmp_path / "customer_requests"
    customers.mkdir()
    _write(customers, "c1.json", {
        "request_id": "C-1",
        "display_name": "Customer One",
        "status": "RUNNING",
        "external_actions": [],
    })

    def executor(payload):
        return {
            "completed": True,
            "verification": {"passed": False, "criterion": "activity complete"},
            "evidence": {"attempt": 1},
        }

    result = CustomerActivitySupervisor(tmp_path, repair_resume=executor).continue_unfinished()
    assert result["status"] == "CONTINUATION_INCOMPLETE"
    assert result["results"][0]["status"] == "NOT_COMPLETED"


def test_continuation_accepts_only_verified_completion(tmp_path):
    customers = tmp_path / "customer_requests"
    customers.mkdir()
    _write(customers, "c1.json", {
        "request_id": "C-1",
        "display_name": "Customer One",
        "status": "RUNNING",
        "external_actions": [],
    })

    def executor(payload):
        return {
            "completed": True,
            "verification": {"passed": True, "criterion": "activity completed"},
            "evidence": {"checkpoint": "verified"},
        }

    result = CustomerActivitySupervisor(tmp_path, repair_resume=executor).continue_unfinished()
    assert result["status"] == "COMPLETED"
    assert result["results"][0]["evidence_ref"].startswith("evidence://customer-activity/")
