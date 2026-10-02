"""Human mediator bridge for Brain ↔ ChatGPT conversations.

The mediator models the human handoff explicitly: compose -> send -> receive -> verify.
It never claims UI clicks unless a real UI automation adapter reports them.
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
LEDGER = STATE / "chatgpt_human_mediator.jsonl"


class HumanMediator:
    def __init__(self, responder: Callable[..., dict[str, Any]] | None = None):
        self.responder = responder

    def compose(self, message: str, context: str = "") -> dict[str, Any]:
        text = str(message).strip()
        if not text:
            return {"ok": False, "status": "EMPTY_MESSAGE"}
        return {
            "ok": True,
            "status": "COMPOSED",
            "message": text,
            "context": str(context or ""),
            "message_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    def send(self, message: str, context: str = "") -> dict[str, Any]:
        composed = self.compose(message, context)
        if not composed["ok"]:
            return composed
        if self.responder is None:
            result = {
                "ok": False,
                "status": "NO_CHATGPT_ADAPTER",
                "ui_clicked": False,
                "message_hash": composed["message_hash"],
            }
        else:
            started = time.time()
            try:
                response = self.responder(message, context=context)
                result = {
                    "ok": bool(response.get("ok")),
                    "status": "RECEIVED" if response.get("ok") else "CHATGPT_ERROR",
                    "ui_clicked": bool(response.get("ui_clicked", False)),
                    "response": response,
                    "elapsed_seconds": round(time.time() - started, 3),
                    "message_hash": composed["message_hash"],
                }
            except Exception as exc:
                result = {
                    "ok": False,
                    "status": "ADAPTER_EXCEPTION",
                    "ui_clicked": False,
                    "error": str(exc)[:1000],
                    "message_hash": composed["message_hash"],
                }
        STATE.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": time.time(),
                "operation": "human_mediator",
                "composed": composed,
                "result": result,
            }, ensure_ascii=False) + "\n")
        return result
