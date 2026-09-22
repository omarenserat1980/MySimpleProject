"""Local Arabic chat layer for the Electronic Brain.

This is intentionally lightweight and deterministic: it keeps short conversation
memory, recognizes a small set of useful commands, and routes executable requests
through the existing CognitiveOrchestrator. A future LLM can be plugged in without
changing the HTTP API.
"""
from collections import deque
from typing import Any

class BrainChat:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.history = deque(maxlen=30)

    @staticmethod
    def _intent(text: str):
        t = text.strip().lower()
        if any(x in t for x in ("مرحبا", "السلام عليكم", "هلا", "اهلا", "أهلا")):
            return "greeting", None
        if any(x in t for x in ("وضع النظام", "حالة النظام", "حالتك", "كيف حالك", "status")):
            return "status", None
        if any(x in t for x in ("بايثون", "python")):
            return "action", "python_version"
        if any(x in t for x in ("git status", "حالة git", "حالة المستودع", "المستودع")):
            return "action", "git_status"
        if any(x in t for x in ("افحص", "فحص", "تحقق", "inspect")):
            return "action", "inspect"
        return "conversation", None

    def respond(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            return {"status": "EMPTY", "reply": "احكيلي شو بدك أعمل.", "history": list(self.history)}

        intent, action = self._intent(text)
        self.history.append({"role": "user", "content": text})

        if intent == "greeting":
            reply = "وعليكم السلام 👋 أنا العقل الإلكتروني. احكي معي، وإذا طلبت مني مهمة أقدر أحولها إلى هدف وأنفذها ضمن الصلاحيات المسموحة."
            result = {"status": "CHAT", "intent": intent}
        elif intent == "status":
            status = self.orchestrator.status()
            reply = (
                f"أنا شغال. الدورة الحالية: {status['cycle']}. "
                f"عدد التجارب المتعلمة: {status['learning']['experiences']}. "
                f"الأفعال المتعلمة: {status['learning']['learned_actions']}."
            )
            result = {"status": "CHAT", "intent": intent, "brain_status": status}
        elif intent == "action":
            outcome = self.orchestrator.step({
                "objective": text,
                "actions": [action],
                "horizon": 1,
            })
            if outcome.get("status") == "EXECUTED":
                reply = f"تم تنفيذ المهمة: {action}. النتيجة وصلت بنجاح."
            elif outcome.get("status") == "PROPOSED":
                reply = f"فهمت المهمة ({action})، لكن التنفيذ غير مفعّل لهذه العملية حالياً."
            else:
                reply = f"حاولت تنفيذ المهمة ({action}) لكن التنفيذ فشل. أقدر أتعلم من النتيجة ونحاول بخطة أخرى."
            result = {"status": outcome.get("status", "UNKNOWN"), "intent": intent, "action": action, "execution": outcome}
        else:
            reply = (
                "فهمت كلامك. حالياً طبقة الحوار المحلية تدعم المحادثة الأساسية "
                "وتحويل الأوامر المعروفة إلى تنفيذ. هذا الكلام غير مربوط بعد بنموذج لغوي عام، "
                "لذلك لن أخترع جواباً من عندي."
            )
            result = {"status": "CHAT", "intent": intent, "action": None}

        self.history.append({"role": "assistant", "content": reply})
        result["reply"] = reply
        result["history"] = list(self.history)
        return result
