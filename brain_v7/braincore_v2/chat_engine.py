"""Arabic conversational layer for the Electronic Brain.

V8.2 adds broader deterministic Arabic understanding without pretending to be an
LLM. It classifies common conversational intents, keeps short-term context, and
routes safe known actions through the cognitive orchestrator.
"""
from collections import deque
from typing import Any


class BrainChat:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.history = deque(maxlen=60)
        self.turns = 0

    @staticmethod
    def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
        return any(p in text for p in phrases)

    @classmethod
    def _intent(cls, text: str):
        t = " ".join(text.strip().lower().split())

        if cls._has_any(t, ("مرحبا", "السلام عليكم", "هلا", "اهلا", "أهلا", "صباح الخير", "مساء الخير")):
            return "greeting", None
        if cls._has_any(t, ("من أنت", "مين انت", "مين إنت", "ما أنت", "شو أنت", "ما هو العقل الإلكتروني")):
            return "identity", None
        if cls._has_any(t, ("حالة النظام", "وضع النظام", "حالتك", "كيف حالك", "status")):
            return "status", None
        if cls._has_any(t, ("ماذا تستطيع", "شو بتقدر", "شو تستطيع", "قدراتك", "ماذا يمكنك", "شو ممكن تعمل")):
            return "capabilities", None
        if cls._has_any(t, ("هل تستطيع تطوير نفسك", "تطور نفسك", "تطوير نفسك", "تطور حالك", "تحسن نفسك")):
            return "self_improvement", None
        if cls._has_any(t, ("ماذا ينقصك", "شو ناقصك", "ما الذي ينقصك", "نقاط ضعفك")):
            return "gaps", None
        if cls._has_any(t, ("ذاكرتك", "ماذا تتذكر", "شو بتتذكر", "ماذا حفظت")):
            return "memory", None
        if cls._has_any(t, ("خطة التطوير", "كيف نطورك", "كيف أطورك", "ماذا أطلب من شات جي بي تي",
                             "ماذا اطلب من شات جي تي بي", "شو أطلب من شات جي بي تي")):
            return "development_plan", None
        if cls._has_any(t, ("بايثون", "python")):
            return "action", "python_version"
        if cls._has_any(t, ("git status", "حالة git", "حالة المستودع", "المستودع")):
            return "action", "git_status"
        if cls._has_any(t, ("افحص", "فحص", "تحقق", "inspect")):
            return "action", "inspect"
        return "conversation", None

    def _status_reply(self) -> tuple[str, dict[str, Any]]:
        status = self.orchestrator.status()
        reply = (
            f"أنا شغال. الدورة الحالية {status['cycle']}. "
            f"لدي {status['learning']['experiences']} تجربة تعلم "
            f"و{status['learning']['learned_actions']} أفعال متعلمة. "
            "إذا طلبت مني مهمة معروفة أستطيع تحويلها إلى تنفيذ ضمن الصلاحيات."
        )
        return reply, {"brain_status": status}

    def respond(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            return {"status": "EMPTY", "reply": "احكيلي شو بدك أعمل.", "history": list(self.history)}

        self.turns += 1
        self.history.append({"role": "user", "content": text})
        intent, action = self._intent(text)

        if intent == "greeting":
            reply = "وعليكم السلام 👋 أنا العقل الإلكتروني. جاهز للحوار والتعلم والتنفيذ ضمن الصلاحيات المسموحة."
            result = {"status": "CHAT", "intent": intent}

        elif intent == "identity":
            reply = (
                "أنا العقل الإلكتروني الذي نبنيه في مشروعك. أعمل حاليًا محليًا عبر Python وFastAPI، "
                "ولدي طبقات للأهداف والتخطيط والتنفيذ والتعلم والتحسين. لكنني لست نموذجًا لغويًا عامًا بعد."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "capabilities":
            reply = (
                "أستطيع حاليًا إدارة أهداف وخطط محدودة، تنفيذ أفعال مسموحة عبر الـAgent، "
                "تسجيل التجارب والتعلم من نجاح التنفيذ أو فشله، وفحص حالتي. "
                "أما الحوار الحر والفهم العام، فنحتاج لاحقًا إلى ربط نموذج لغوي حقيقي."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "self_improvement":
            reply = (
                "نعم، أستطيع المشاركة في تطوير نفسي لكن بشكل مضبوط: أكتشف نقصًا، أقترح تحسينًا، "
                "نختبره، نقيس النتيجة، ثم نحفظ الدرس. حاليًا لا أعدل كودي عشوائيًا من تلقاء نفسي."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "gaps":
            reply = (
                "أهم ما ينقصني حاليًا: نموذج لغوي للحوار العام، ذاكرة طويلة المدى، "
                "فهم أفضل للسياق، نظام تقييم واختبار للتعديلات، وأدوات أكثر مع صلاحيات واضحة."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "memory":
            recent = [x for x in self.history if x["role"] == "user"][-5:]
            topics = " | ".join(x["content"] for x in recent)
            reply = (
                f"ذاكرتي الحالية قصيرة ومحدودة داخل جلسة التشغيل. أتذكر آخر الرسائل في هذه الجلسة، "
                f"ومنها: {topics}. الذاكرة الدائمة لم تُبنَ بعد."
            )
            result = {"status": "CHAT", "intent": intent, "recent_user_messages": recent}

        elif intent == "development_plan":
            reply = (
                "اطلب من ChatGPT تطويري على مراحل: "
                "1) محرك حوار عربي حقيقي، 2) ذاكرة طويلة المدى، "
                "3) مخطط مهام متعدد الخطوات، 4) أدوات تنفيذ آمنة، "
                "5) تقييم واختبارات تلقائية، 6) دورة تحسين ذاتي مقيدة مع سجل وتراجع. "
                "وهذا بالضبط المسار الذي نستطيع تنفيذه الآن."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "status":
            reply, extra = self._status_reply()
            result = {"status": "CHAT", "intent": intent, **extra}

        elif intent == "action":
            outcome = self.orchestrator.step({
                "objective": text,
                "actions": [action],
                "horizon": 1,
            })
            if outcome.get("status") == "EXECUTED":
                reply = f"تم تنفيذ المهمة: {action} بنجاح."
            elif outcome.get("status") == "PROPOSED":
                reply = f"فهمت المهمة ({action})، لكن هذا التنفيذ غير مفعّل حاليًا."
            else:
                reply = f"حاولت تنفيذ ({action}) لكن التنفيذ فشل. النتيجة محفوظة للتعلم."
            result = {
                "status": outcome.get("status", "UNKNOWN"),
                "intent": intent,
                "action": action,
                "execution": outcome,
            }

        else:
            reply = (
                "فهمت أنك تتحدث معي بشكل طبيعي. أستطيع الآن فهم مجموعة أوسع من الأسئلة عن هويتي "
                "وقدراتي وتطويري وحالتي، لكنني ما زلت بلا نموذج لغوي عام؛ لذلك لن أخترع إجابة. "
                "إذا أردت فهمًا أوسع للحوار، فالخطوة التالية هي ربط محرك لغوي حقيقي."
            )
            result = {"status": "CHAT", "intent": intent, "action": None}

        self.history.append({"role": "assistant", "content": reply})
        result["reply"] = reply
        result["history"] = list(self.history)
        result["turn"] = self.turns
        return result
