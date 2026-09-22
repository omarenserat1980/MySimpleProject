"""Arabic intent and conversation layer for the Electronic Brain V8.3.

This layer remains deterministic and local. It normalizes common Arabic variants,
uses intent patterns instead of exact sentences, preserves short-term context,
and routes only known safe actions to the cognitive orchestrator.
"""
from collections import deque
from typing import Any


class BrainChat:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.history = deque(maxlen=60)
        self.turns = 0

    @staticmethod
    def _normalize(text: str) -> str:
        t = text.strip().lower()
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ى": "ي", "ة": "ه",
            "ؤ": "و", "ئ": "ي",
            "ـ": "",
            "؟": " ", "?": " ", "!": " ", "،": " ", ",": " ",
            "؛": " ", ";": " ", ":": " ",
        }
        for old, new in replacements.items():
            t = t.replace(old, new)
        return " ".join(t.split())

    @staticmethod
    def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
        return any(p in text for p in phrases)

    @classmethod
    def _intent(cls, text: str):
        t = cls._normalize(text)

        if cls._has_any(t, (
            "مرحبا", "السلام عليكم", "هلا", "اهلا", "صباح الخير", "مساء الخير"
        )):
            return "greeting", None

        if cls._has_any(t, (
            "من انت", "مين انت", "ما انت", "شو انت",
            "ما هو العقل الالكتروني", "احكيلي عن نفسك"
        )):
            return "identity", None

        if cls._has_any(t, (
            "حاله النظام", "وضع النظام", "حالتك", "كيف حالك",
            "شو وضعك", "كيف وضعك", "status"
        )):
            return "status", None

        if cls._has_any(t, (
            "ماذا تستطيع", "شو بتقدر", "شو تستطيع", "قدراتك",
            "ماذا يمكنك", "شو ممكن تعمل", "ايش بتقدر تعمل"
        )):
            return "capabilities", None

        if cls._has_any(t, (
            "هل تستطيع تطوير نفسك", "تطور نفسك", "تطوير نفسك",
            "تطور حالك", "تحسن نفسك", "تقدر تطور نفسك",
            "كيف تطور نفسك"
        )):
            return "self_improvement", None

        if cls._has_any(t, (
            "ماذا ينقصك", "شو ناقصك", "ما الذي ينقصك",
            "نقاط ضعفك", "شو ناقص", "ما هي نواقصك"
        )):
            return "gaps", None

        if cls._has_any(t, (
            "ذاكرتك", "ماذا تتذكر", "شو بتتذكر",
            "ماذا حفظت", "شو محفوظ بذاكرتك", "شو بتعرف عني"
        )):
            return "memory", None

        # Flexible detection for requests about using ChatGPT to develop the brain.
        has_ai = cls._has_any(t, (
            "شات جي بي تي", "شات جيتي بي", "chatgpt",
            "تشات جي بي تي", "شات جي تي بي"
        ))
        has_dev = cls._has_any(t, (
            "اطلب", "اسال", "احكي", "اكتب", "اعطي",
            "طور", "تطوير", "برومبت", "تعليمات"
        ))
        if (
            cls._has_any(t, ("خطة التطوير", "كيف نطورك", "كيف اطورك"))
            or (has_ai and has_dev)
            or cls._has_any(t, ("ماذا اطلب لتطويرك", "شو اطلب لتطويرك",
                                 "ماذا اطلب منك لتطويرك", "شو اطلب من شات"))
        ):
            return "development_plan", None

        # Contextual follow-up: if the previous user message was about development,
        # short follow-ups such as "طيب شو اطلب؟" remain in that topic.
        recent_users = []
        for item in reversed(getattr(cls, "_context_history", [])):
            if item.get("role") == "user":
                recent_users.append(cls._normalize(item.get("content", "")))
            if len(recent_users) >= 3:
                break
        if recent_users and cls._has_any(t, ("شو اطلب", "ماذا اطلب", "طيب شو", "كيف نبدأ")):
            if any(cls._has_any(x, ("تطوير", "طور", "تطور", "شات جي بي تي", "نطور"))
                   for x in recent_users):
                return "development_plan", None

        if cls._has_any(t, ("بايثون", "python")):
            return "action", "python_version"

        if cls._has_any(t, (
            "git status", "حاله git", "حاله المستودع", "المستودع"
        )):
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
            return {
                "status": "EMPTY",
                "reply": "احكيلي شو بدك أعمل.",
                "history": list(self.history),
            }

        self.turns += 1
        self.history.append({"role": "user", "content": text})

        # Give intent classification access to the current short-term context.
        type(self)._context_history = list(self.history)
        intent, action = self._intent(text)

        if intent == "greeting":
            reply = (
                "وعليكم السلام 👋 أنا العقل الإلكتروني. "
                "جاهز للحوار والتعلم والتنفيذ ضمن الصلاحيات المسموحة."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "identity":
            reply = (
                "أنا العقل الإلكتروني الذي نبنيه في مشروعك. أعمل حاليًا محليًا عبر "
                "Python وFastAPI، ولدي طبقات للأهداف والتخطيط والتنفيذ والتعلم والتحسين. "
                "لكنني لست نموذجًا لغويًا عامًا بعد."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "capabilities":
            reply = (
                "أستطيع حاليًا إدارة أهداف وخطط محدودة، وتنفيذ أفعال مسموحة عبر الـAgent، "
                "وتسجيل التجارب والتعلم من النتائج، وفحص حالتي. "
                "أما الفهم الحر الواسع للحوار فيحتاج إلى نموذج لغوي حقيقي."
            )
            result = {"status": "CHAT", "intent": intent}

        elif intent == "self_improvement":
            reply = (
                "نعم، أستطيع المشاركة في تطوير نفسي بشكل مضبوط: أكتشف نقصًا، "
                "أقترح تحسينًا، نختبره، نقيس النتيجة، ثم نحفظ الدرس. "
                "حاليًا لا أعدل كودي عشوائيًا من تلقاء نفسي."
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
                "ذاكرتي الحالية قصيرة ومحدودة داخل جلسة التشغيل. أتذكر آخر الرسائل "
                f"في هذه الجلسة، ومنها: {topics}. الذاكرة الدائمة لم تُبنَ بعد."
            )
            result = {"status": "CHAT", "intent": intent, "recent_user_messages": recent}

        elif intent == "development_plan":
            reply = (
                "اطلب من ChatGPT تطويري على مراحل، وليس تعديل الكود عشوائيًا. "
                "ابدأ بهذا الطلب: «طوّر العقل الإلكتروني V8.3 ليصبح محرك حوار عربي "
                "يفهم النية والسياق، ثم اربطه لاحقًا بنموذج لغوي حقيقي، مع ذاكرة طويلة "
                "المدى، تخطيط متعدد الخطوات، أدوات تنفيذ آمنة، اختبارات تلقائية، "
                "سجل للتغييرات، وتراجع عند الفشل». "
                "بعد كل تعديل نختبره على الجهاز قبل الانتقال للمرحلة التالية."
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
                "أفهم أنك تتحدث معي بشكل طبيعي. أستطيع حاليًا فهم عدة نوايا عربية "
                "والاحتفاظ بسياق قصير، لكنني ما زلت بلا نموذج لغوي عام. "
                "إذا كان طلبك مهمة تنفيذية، اذكر الهدف بوضوح وسأحوله إلى فعل معروف "
                "إذا كان ضمن الصلاحيات."
            )
            result = {"status": "CHAT", "intent": intent, "action": None}

        self.history.append({"role": "assistant", "content": reply})
        result["reply"] = reply
        result["history"] = list(self.history)
        result["turn"] = self.turns
        return result
