from __future__ import annotations

import pytest

from brain_v12.brain.email_gateway import AgentMailGateway, EmailGatewayError


def test_gateway_requires_secret_and_inbox(monkeypatch):
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("BRAIN_EMAIL_INBOX_ID", raising=False)
    gateway = AgentMailGateway()
    assert gateway.configured() is False
    with pytest.raises(EmailGatewayError, match="AGENTMAIL_API_KEY"):
        gateway.send(to=["example@example.com"], subject="x", text="y")


def test_gateway_requires_recipient(monkeypatch):
    gateway = AgentMailGateway(api_key="test-key", inbox_id="test-inbox")
    with pytest.raises(EmailGatewayError, match="recipient"):
        gateway.send(to=[], subject="x", text="y")


def test_gateway_configuration_does_not_expose_secret(monkeypatch):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "super-secret")
    monkeypatch.setenv("BRAIN_EMAIL_INBOX_ID", "brain-inbox")
    gateway = AgentMailGateway()
    assert gateway.configured() is True
    assert "super-secret" not in repr(gateway)
