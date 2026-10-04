"""Evidence-first outbound email gateway for Brain.

AgentMail is an adapter, not a source of truth. Secrets are supplied only
through the environment; recipient addresses are never hard-coded.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


DEFAULT_BASE_URL = "https://api.agentmail.to/v0"


class EmailGatewayError(RuntimeError):
    """Raised when an email operation cannot be verified."""


@dataclass(frozen=True)
class EmailResult:
    message_id: str
    thread_id: str
    provider: str = "agentmail"


class AgentMailGateway:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        inbox_id: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("AGENTMAIL_API_KEY")
        self.inbox_id = inbox_id or os.getenv("BRAIN_EMAIL_INBOX_ID")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def configured(self) -> bool:
        return bool(self.api_key and self.inbox_id)

    def send(
        self,
        *,
        to: list[str],
        subject: str,
        text: str,
        html: str | None = None,
    ) -> EmailResult:
        if not self.api_key:
            raise EmailGatewayError("AGENTMAIL_API_KEY is not configured")
        if not self.inbox_id:
            raise EmailGatewayError("BRAIN_EMAIL_INBOX_ID is not configured")
        if not to:
            raise EmailGatewayError("at least one recipient is required")
        if not subject.strip() or not text.strip():
            raise EmailGatewayError("subject and text are required")

        payload = {"to": to, "subject": subject, "text": text}
        if html is not None:
            payload["html"] = html

        request = urllib.request.Request(
            f"{self.base_url}/inboxes/{self.inbox_id}/messages/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise EmailGatewayError(
                f"AgentMail rejected the message: HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise EmailGatewayError(f"AgentMail transport failure: {exc}") from exc

        message_id = data.get("message_id")
        thread_id = data.get("thread_id")
        if not message_id or not thread_id:
            raise EmailGatewayError("AgentMail response lacks message_id/thread_id")

        return EmailResult(message_id=message_id, thread_id=thread_id)
