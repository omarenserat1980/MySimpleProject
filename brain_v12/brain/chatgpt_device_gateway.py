"""Brain-authorized gateway to the installed ChatGPT Android UI.

This module never decides policy. Brain supplies the decision envelope; the
Android Executor performs the bounded UI action and reports evidence.
"""
from __future__ import annotations

from typing import Any


class ChatGPTDeviceGateway:
    def __init__(self, device_bridge: Any) -> None:
        self.device_bridge = device_bridge

    def send(
        self,
        message: str,
        *,
        decision_id: str = "",
        required_evidence: list[str] | None = None,
        timeout_ms: int = 120_000,
    ) -> dict[str, Any]:
        return self.device_bridge.enqueue_chatgpt_ui(
            message,
            decision_id=decision_id,
            required_evidence=required_evidence,
            timeout_ms=timeout_ms,
        )

    def verify(self, task_id: str) -> dict[str, Any]:
        return self.device_bridge.verify_result(task_id)

    def contract(self) -> dict[str, Any]:
        return {
            "authority": "BRAIN",
            "partner": "CHATGPT",
            "executor": "ANDROID_EXECUTOR",
            "transport": "DEVICE_TASK_QUEUE",
            "task": "chatgpt_ui_send",
            "target_package": "com.openai.chatgpt",
            "approval_source": "BRAIN_DECISION",
            "required_evidence": ["response_text", "ui_clicked", "status"],
            "verification_status": "BRAIN_MUST_VERIFY",
            "security_boundary": "USER_ENABLED_ACCESSIBILITY_SERVICE_ONLY",
        }
