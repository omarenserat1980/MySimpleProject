from economics.audit_ledger import (
    create_audit_event,
    is_duplicate,
    payload_fingerprint,
)


def test_payload_fingerprint_is_deterministic():
    assert payload_fingerprint({"b": 2, "a": 1}) == payload_fingerprint(
        {"a": 1, "b": 2}
    )


def test_audit_event_is_deterministic():
    kwargs = {
        "event_type": "DECISION",
        "opportunity_id": "x",
        "payload": {"decision": "HOLD"},
        "occurred_at": "2026-10-08T00:00:00+00:00",
    }
    first = create_audit_event(**kwargs)
    second = create_audit_event(**kwargs)
    assert first.event_id == second.event_id
    assert first.payload_hash == second.payload_hash


def test_duplicate_event_is_detected():
    event = create_audit_event(
        event_type="DECISION",
        opportunity_id="x",
        payload={"decision": "HOLD"},
        occurred_at="2026-10-08T00:00:00+00:00",
    )
    assert is_duplicate(event, {event.event_id})


def test_invalid_event_fails_closed():
    try:
        create_audit_event(
            event_type="",
            opportunity_id="x",
            payload={},
            occurred_at="2026-10-08T00:00:00+00:00",
        )
        assert False
    except ValueError:
        assert True
