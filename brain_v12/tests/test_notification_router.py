from brain_v12.brain.notification_router import NotificationRouter

class FakeGateway:
    def __init__(self):
        self.calls = []
    def send(self, *, to, subject, text):
        self.calls.append((to, subject, text))
        class Result:
            message_id = "msg-test"
            thread_id = "thread-test"
        return Result()

def test_error_event_is_sent_and_deduplicated(tmp_path):
    gateway = FakeGateway()
    router = NotificationRouter(gateway=gateway, evidence_path=tmp_path / "notifications.jsonl", recipient="test@example.invalid")
    first = router.notify(event_type="CI_FAILURE", source="brain-release-gate", severity="ERROR", subject="Brain CI failure", text="A release gate failed.", fingerprint="gate-x")
    second = router.notify(event_type="CI_FAILURE", source="brain-release-gate", severity="ERROR", subject="Brain CI failure", text="A release gate failed.", fingerprint="gate-x")
    assert first.status == "SENT_VERIFIED"
    assert first.message_id == "msg-test"
    assert second.status == "NOT_SENT"
    assert second.error == "duplicate_event"
    assert len(gateway.calls) == 1

def test_info_event_is_not_sent(tmp_path):
    gateway = FakeGateway()
    router = NotificationRouter(gateway=gateway, evidence_path=tmp_path / "notifications.jsonl", recipient="test@example.invalid")
    result = router.notify(event_type="CI_SUCCESS", source="brain-cloud", severity="INFO", subject="Brain CI passed", text="Success.")
    assert result.status == "NOT_SENT"
    assert result.error == "severity_not_notifiable"
    assert gateway.calls == []

def test_missing_recipient_fails_closed(tmp_path):
    gateway = FakeGateway()
    router = NotificationRouter(gateway=gateway, evidence_path=tmp_path / "notifications.jsonl")
    result = router.notify(event_type="CI_FAILURE", source="brain-cloud", severity="CRITICAL", subject="Failure", text="Failure.")
    assert result.status == "NOT_SENT"
    assert result.error == "recipient_not_configured"
    assert gateway.calls == []
