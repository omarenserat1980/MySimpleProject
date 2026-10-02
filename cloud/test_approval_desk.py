from cloud.approval_desk import create_approval, decide_approval, get_approval, list_approvals, notification_status

def test_approval_is_durable_and_email_is_outbox(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_STATE_DIR", str(tmp_path))
    import cloud.approval_desk as desk
    desk.STATE, desk.APPROVAL_DIR, desk.OUTBOX_DIR = tmp_path, tmp_path / "approvals", tmp_path / "notification_outbox"
    monkeypatch.delenv("BRAIN_SMTP_HOST", raising=False)
    approval = create_approval(subject="Price below floor", reason="Requested quote is below floor.",
                               risk="HIGH", recipient_email="owner@example.com",
                               evidence=[{"type": "pricing", "ref": "price-1"}])
    assert approval["status"] == "PENDING"
    assert get_approval(approval["approval_id"])["status"] == "PENDING"
    assert list_approvals()[0]["approval_id"] == approval["approval_id"]
    assert notification_status()[0]["status"] == "QUEUED"

def test_decision_is_recorded_once(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_STATE_DIR", str(tmp_path))
    import cloud.approval_desk as desk
    desk.STATE, desk.APPROVAL_DIR, desk.OUTBOX_DIR = tmp_path, tmp_path / "approvals", tmp_path / "notification_outbox"
    approval = create_approval(subject="Deploy", reason="Production change")
    decided = decide_approval(approval["approval_id"], decision="APPROVED", actor="authorized-human", note="Reviewed evidence")
    assert decided["status"] == "APPROVED"
    assert decided["decision"]["actor"] == "authorized-human"
    try:
        decide_approval(approval["approval_id"], decision="APPROVED", actor="authorized-human")
        assert False
    except ValueError as exc:
        assert "no longer pending" in str(exc)
