from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cloud.customer_communications import (
    Channel,
    CommunicationHub,
    MessageState,
    Priority,
)


def test_message_is_durable_and_idempotent(tmp_path: Path):
    hub = CommunicationHub(tmp_path / "state")
    first = hub.create(
        customer_id="C-1", channel=Channel.CUSTOMER_PORTAL, direction="INBOUND",
        body="Please send a quote.", idempotency_key="customer:C-1:request:1",
    )
    second = hub.create(
        customer_id="C-1", channel=Channel.CUSTOMER_PORTAL, direction="INBOUND",
        body="Please send a quote.", idempotency_key="customer:C-1:request:1",
    )
    assert first.message_id == second.message_id
    loaded = hub.get(first.message_id)
    assert loaded.content_hash == first.content_hash
    assert len(loaded.events) == 1
    assert loaded.events[0]["event"] == "CREATED"


def test_transport_states_require_evidence(tmp_path: Path):
    hub = CommunicationHub(tmp_path / "state")
    msg = hub.create(customer_id="C-2", channel=Channel.EMAIL, direction="OUTBOUND",
                     body="Your quote is ready.")
    hub.transition(msg.message_id, MessageState.QUEUED)
    with pytest.raises(ValueError):
        hub.transition(msg.message_id, MessageState.SENT)
    sent = hub.transition(msg.message_id, MessageState.SENT, "smtp:accepted:123")
    assert sent.transport_evidence_ref == "smtp:accepted:123"
    assert sent.attempt == 1


def test_thread_assignment_and_escalation_are_durable(tmp_path: Path):
    hub = CommunicationHub(tmp_path / "state")
    msg = hub.create(customer_id="C-3", channel=Channel.WEB_CHAT, direction="INBOUND",
                     body="Urgent help", thread_id="THREAD-1", priority=Priority.URGENT,
                     sla_minutes=60)
    hub.assign(msg.message_id, "CUSTOMER_SUCCESS")
    hub.escalate(msg.message_id, "customer-impact")
    loaded = hub.get(msg.message_id)
    assert loaded.assigned_to == "CUSTOMER_SUCCESS"
    assert loaded.escalation_state == "ESCALATED"
    assert loaded.priority == Priority.URGENT
    assert loaded.thread_id == "THREAD-1"


def test_sla_overdue_is_detected(tmp_path: Path):
    hub = CommunicationHub(tmp_path / "state")
    msg = hub.create(customer_id="C-4", channel=Channel.CUSTOMER_PORTAL,
                     direction="INBOUND", body="Old request", sla_minutes=1)
    loaded = hub.get(msg.message_id)
    old = datetime.now(timezone.utc) + timedelta(minutes=2)
    assert loaded.sla_overdue(old)
    assert msg.message_id in [m.message_id for m in hub.list_overdue()]
