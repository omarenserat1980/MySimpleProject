"""UI automation contract for the Brain human mediator.

This module is deliberately adapter-based: it defines the evidence contract for
type -> click Send -> wait -> read, without pretending that an API call is a UI click.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, asdict
from typing import Any, Protocol


class ChatGPTUIAdapter(Protocol):
    def type_message(self, message: str) -> dict[str, Any]: ...
    def click_send(self) -> dict[str, Any]: ...
    def wait_for_response(self, timeout: float = 120.0) -> dict[str, Any]: ...
    def read_response(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class UIEvidence:
    typed: bool = False
    clicked: bool = False
    response_ready: bool = False
    response_read: bool = False
    response_text: str = ""
    error: str = ""


class HumanChatGPTUI:
    """Execute the four UI stages through a supplied, real UI adapter."""

    def __init__(self, adapter: ChatGPTUIAdapter | None = None):
        self.adapter = adapter

    def send(self, message: str, timeout: float = 120.0) -> dict[str, Any]:
        if self.adapter is None:
            return {
                "ok": False,
                "status": "UI_ADAPTER_NOT_CONFIGURED",
                "evidence": asdict(UIEvidence(error="No real UI adapter configured")),
            }
        text = str(message).strip()
        if not text:
            return {
                "ok": False,
                "status": "EMPTY_MESSAGE",
                "evidence": asdict(UIEvidence(error="Message is empty")),
            }
        evidence = UIEvidence()
        started = time.time()
        try:
            typed = self.adapter.type_message(text)
            if not typed.get("ok"):
                return self._fail("TYPE_FAILED", evidence, typed)
            evidence = UIEvidence(typed=True)

            clicked = self.adapter.click_send()
            if not clicked.get("ok") or not clicked.get("clicked", False):
                return self._fail("SEND_CLICK_NOT_VERIFIED", evidence, clicked)
            evidence = UIEvidence(typed=True, clicked=True)

            ready = self.adapter.wait_for_response(timeout=timeout)
            if not ready.get("ok") or not ready.get("ready", False):
                return self._fail("RESPONSE_NOT_READY", evidence, ready)
            evidence = UIEvidence(typed=True, clicked=True, response_ready=True)

            response = self.adapter.read_response()
            response_text = str(response.get("text", "")).strip()
            if not response.get("ok") or not response_text:
                return self._fail("RESPONSE_READ_FAILED", evidence, response)
            evidence = UIEvidence(
                typed=True, clicked=True, response_ready=True,
                response_read=True, response_text=response_text,
            )
            return {
                "ok": True,
                "status": "UI_CONVERSATION_VERIFIED",
                "ui_clicked": True,
                "elapsed_seconds": round(time.time() - started, 3),
                "evidence": asdict(evidence),
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": "UI_ADAPTER_EXCEPTION",
                "ui_clicked": False,
                "elapsed_seconds": round(time.time() - started, 3),
                "evidence": asdict(evidence),
                "error": str(exc)[:1000],
            }

    @staticmethod
    def _fail(status: str, evidence: UIEvidence, detail: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "ui_clicked": evidence.clicked,
            "evidence": asdict(evidence),
            "detail": detail,
        }
