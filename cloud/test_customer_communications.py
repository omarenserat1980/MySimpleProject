from pathlib import Path

import pytest

from cloud.customer_communications import (
    Channel,
    CommunicationHub,
    MessageState,
)


def test_message_is_durable_and_idempotent(tmp_path: Path):
    hub = CommunicationHub(tmp_path / "state")
    first = hub.create(
        customer_id="C-1",
        channel=Channel.CUSTOMER_PORTAL,
        direction="INBOUND",
        body="Please send a quote.",
        idempotency_key="customer:C-1:request:1",
    )
    second = hub.create(
        customer_id="C-1",
        channel=Channel.CUSTOMER_PORTAL,
        direction="INBOUND",
        body="Please send a quote.",
        idempotency_key="customer:C-1:request:1",
    )
    assert first.message_id == second.message_id
    assert hub.get(first.message_id).content_hash == first.content_hash


def test_transport_states_require_evidence(tmp_path: Path):
    hub = CommunicationHub(tmp_path / "state")
    msg = hub.create(
        customer_id="C-2",
        channel=Channel.EMAIL,
        direction="OUTBOUND",
        body="Your quote is ready.",
    )
    hub.transition(msg.message_id, MessageState.QUEUED)
    with pytest.raises(ValueError):
        hub.transition(msg.message_id, MessageState.SENT)
    sent = hub.transition(msg.message_id, MessageState.SENT, "smtp:accepted:123")
    assert sent.transport_evidence_ref == "smtp:accepted:123"


def test_customer_thread_is_queryable(tmp_path: Path):
    hub = CommunicationHub(tmp_path / "state")
    msg = hub.create(
        customer_id="C-3",
        channel=Channel.WEB_CHAT,
        direction="INBOUND",
        body="Hello",
        thread_id="THREAD-1",
    )
    assert [m.message_id for m in hub.list_customer("C-3")] == [msg.message_id]
