"""Arabic intent, conversation, smart memory, and bounded terminal control."""
from collections import deque
from typing import Any
import os
from .llm_provider import LLMProvider
from .cloud_memory import CloudMemory


class BrainChat:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.history = deque(maxlen=60)
        self.turns = 0
        self.llm = LLMProvider()
        self.memory = CloudMemory()
        self.user_id = os.getenv("BRAIN_USER_ID", "default")

    @staticmethod
    def _normalize(text: str) -> str:
        t = text.strip().lower()
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه",
            "ؤ": "و", "ئ": "ي", "ـ": "",
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

        if cls._has_any(t, ("مرحبا", "السلام عليكم", "هلا", "اهلا", "صباح الخير", "مساء الخير")):
            return "greeting", None
        if cls._has_any(t, ("من انت", "مين انت", "ما انت", "شو انت", "ما هو العقل الالكتروني", "احكيلي عن نفسك")):
            return "identity", None
        if cls._has_any(t, ("حاله النظام", "وضع النظام", "حالتك", "كيف حالك", "شو وضعك", "كيف وضعك", "status")):
            return "status", None
        if cls._has_any(t, ("ماذا تستطيع", "شو بتقدر", "شو تستطيع", "قدراتك", "ماذا يمكنك", "شو ممكن تعمل", "ايش بتقدر تعمل")):
            return "capabilities", None
        if cls._has_any(t, ("هل تستطيع تطوير نفسك", "تطور نفسك", "تطوير نفسك", "تطور حالك", "تحسن نفسك", "تقدر تطور نفسك", "كيف تطور نفسك")):
            return "self_improvement", None
        if cls._has_any(t, ("ماذا ينقصك", "شو ناقصك", "ما الذي ينقصك", "نقاط ضعفك", "شو ناقص", "ما هي نواقصك")):
            return "gaps", None
        if cls._has_any(t, ("ذاكرتك", "ماذا تتذكر", "شو بتتذكر", "ماذا حفظت", "شو محفوظ بذاكرتك", "شو بتعرف عني")):
            return "memory", None

        # Safe terminal controls: only map natural language to registered actions.
        if cls._has_any(t, ("اعرض ملفات التيرمنال", "اعرض الملفات", "شو موجود بالمجلد", "اعرض محتويات المجلد")):
            return "action", "termux_list"
        if cls._has_any(t, ("وين انا", "اين انا", "وين المجلد", "اعرف موقعي الحالي", "مسار المجلد")):
            return "action", "termux_pwd"
        if cls._has_any(t, ("افحص التيرمنال", "اختبر التيرمنال", "هل التيرمنال شغال")):
            return "action", "inspect"

        has_ai = cls._has_any(t, ("شات جي بي تي", "شات جيتي بي", "chatgpt", "تشات جي بي تي", "شات جي تي بي"))
        has_dev = cls._has_any(t, ("اطلب", "اسال", "احكي", "اكتب", "اعطي", "طور", "تطوير", "برومبت", "تعليمات"))
        if (cls._has_any(t, ("خطة التطوير", "كيف نطورك", "كيف اطورك")) or
                (has_ai and has_dev) or
                cls._has_any(t, ("ماذا اطلب لتطويرك", "شو اطلب لتطويرك", "ماذا اطلب منك لتطويرك", "شو اطلب من شات"))):
            return "development_plan", None

        recent_users = []
        for item in reversed(getattr(cls, "_context_history", [])):
            if item.get("role") == "user":
                recent_users.append(cls._normalize(item.get("content", "")))
            if len(recent_users) >= 3:
                break
        if recent_users and cls._has_any(t, ("شو اطلب", "ماذا اطلب", "طيب شو", "كيف نبدأ")):
            if any(cls._has_any(x, ("تطوير", "طور", "تطور", "شات جي بي تي", "نطور")) for x in recent_users):
                return "development_plan", None

        if cls._has_any(t, ("بايثون", "python")):
            return "action", "python_version"
        if cls._has_any(t, ("git status", "حاله git", "حاله المستودع", "المستودع")):
            return "action", "git_status"
        if cls._has_any(t, ("افحص", "فحص", "تحقق", "inspect")):
            return "action", "inspect"
        return "conversation", None

    @staticmethod
    def _extract_memories(text: str) -> list[tuple[str, str, float]]:
        raw = text.strip()
        n = BrainChat._normalize(raw)
        memories: list[tuple[str, str, float]] = []
        prefixes = (
            ("identity", "اسمي "), ("identity", "انا اسمي "), ("identity", "أنا اسمي "),
            ("preference", "احب "), ("preference", "أحب "),
            ("preference", "افضل "), ("preference", "أفضل "),
            ("goal", "هدفي "), ("goal", "هدفي هو "),
            ("project", "مشروعي "),
        )
        for kind, prefix in prefixes:
            if n.startswith(BrainChat._normalize(prefix)):
                memories.append((kind, raw, 0.85 if kind in ("identity", "goal") else 0.75))
                break
        if any(x in n for x in ("احفظ ان", "تذكر ان", "خلي بذاكرتك", "اريد حفظ")):
            memories.append(("explicit", raw, 0.9))
        unique = []
        seen = set()
        for item in memories:
            if item[1] not in seen:
                unique.append(item)
                seen.add(item[1])
        return unique

    def _status_reply(self) -> tuple[str, dict[str, Any]]:
        status = self.orchestrator.status()
        reply = (
            f"أنا شغال. الدورة الحالية {status['cycle']}. "
            f"لدي {status['learning']['experiences']} تجربة تعلم "
            f"و{status['learning']['learned_actions']} أفعال متعلمة. "
            "إذا طلبت مني مهمة معروفة أستطيع تحويلها إلى تنفيذ ضمن الصلاحيات المسموحة."
        )
        return reply, {"brain_status": status}

    def respond(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            return {"status": "EMPTY", "reply": "احكيلي شو بدك أعمل.", "history": list(self.history)}

        self.turns += 1
        self.history.append({"role": "user", "content": text})
        recalled = self.memory.recall(self.user_id, limit=8)
        type(self)._context_history = list(self.history)
        intent, action = self._intent(text)

        if intent == "greeting":
            reply = "وعليكم السلام 👋 أنا العقل الإلكتروني. جاهز للحوار والتعلم والتنفيذ ضمن الصلاحيات المسموحة."
            result = {"status": "CHAT", "intent": intent}
        elif intent == "identity":
            reply = "أنا العقل الإلكتروني الذي نبنيه في مشروعك. أعمل حاليًا محليًا عبر Python وFastAPI، ولدي طبقات للأهداف والتخطيط والتنفيذ والتعلم والتحسين."
            result = {"status": "CHAT", "intent": intent}
        elif intent == "capabilities":
            reply = "أستطيع حاليًا إدارة أهداف وخطط محدودة، وتنفيذ أفعال مسموحة عبر الـAgent، وتسجيل التجارب والتعلم من النتائج، وفحص حالتي. كما أصبحت أملك جسرًا محدودًا للتعامل مع Terminal عبر أوامر مسجلة مسبقًا."
            result = {"status": "CHAT", "intent": intent}
        elif intent == "self_improvement":
            reply = "نعم، أستطيع المشاركة في تطوير نفسي بشكل مضبوط: أكتشف نقصًا، أقترح تحسينًا، نختبره، نقيس النتيجة، ثم نحفظ الدرس. حاليًا لا أعدل كودي عشوائيًا من تلقاء نفسي."
            result = {"status": "CHAT", "intent": intent}
        elif intent == "gaps":
            reply = "أهم ما ينقصني حاليًا: نموذج لغوي للحوار العام، فهم أفضل للسياق، نظام تقييم واختبار للتعديلات، وأدوات أكثر مع صلاحيات واضحة."
            result = {"status": "CHAT", "intent": intent}
        elif intent == "memory":
            recent = [x for x in self.history if x["role"] == "user"][-5:]
            durable = recalled[:8]
            if durable:
                lines = " | ".join(f"{x.get('kind')}: {x.get('content')}" for x in durable)
                reply = f"هذه ذكرياتي السحابية الحالية عنك: {lines}"
            else:
                reply = "لا توجد لدي ذكريات طويلة المدى محفوظة لهذا المستخدم بعد."
            result = {"status": "CHAT", "intent": intent, "recent_user_messages": recent}
        elif intent == "development_plan":
            reply = "اطلب من ChatGPT تطويري على مراحل: فهم النية والسياق، ذاكرة طويلة المدى، نموذج لغوي، تخطيط متعدد الخطوات، أدوات تنفيذ آمنة، اختبارات تلقائية، سجل تغييرات وتراجع عند الفشل. بعد كل تعديل نختبره على الجهاز قبل المرحلة التالية."
            result = {"status": "CHAT", "intent": intent}
        elif intent == "status":
            reply, extra = self._status_reply()
            result = {"status": "CHAT", "intent": intent, **extra}
        elif intent == "action":
            outcome = self.orchestrator.step({"objective": text, "actions": [action], "horizon": 1})
            if outcome.get("status") == "EXECUTED":
                reply = f"تم تنفيذ المهمة: {action} بنجاح."
            elif outcome.get("status") == "PROPOSED":
                reply = f"فهمت المهمة ({action})، لكن هذا التنفيذ غير مفعّل حاليًا."
            else:
                reply = f"حاولت تنفيذ ({action}) لكن التنفيذ فشل. النتيجة محفوظة للتعلم."
            result = {"status": outcome.get("status", "UNKNOWN"), "intent": intent, "action": action, "execution": outcome}
        else:
            context = [{
                "role": "system",
                "content": "أنت طبقة الحوار في العقل الإلكتروني. أجب بالعربية بوضوح وباختصار. لا تدّع تنفيذ أفعال لم ينفذها النظام فعليًا. لا تمنح نفسك صلاحيات جديدة ولا تغيّر النظام من خلال الحوار."
            }]
            if recalled:
                context.append({
                    "role": "system",
                    "content": "ذكريات سحابية مرتبطة بالمستخدم:\n" + "\n".join(
                        f"- {item.get('content', '')}" for item in recalled
                    ),
                })
            for item in list(self.history)[-12:]:
                context.append({"role": item["role"], "content": item["content"]})
            llm_reply = self.llm.reply(context)
            if llm_reply:
                reply = llm_reply
                result = {"status": "LLM_CHAT", "intent": intent, "action": None, "llm": self.llm.status()}
            else:
                reply = "أفهم أنك تتحدث معي بشكل طبيعي. أفهم عدة نوايا عربية وأستخدم ذاكرة سحابية انتقائية، لكن محرك اللغة العام غير مهيأ أو غير متاح الآن."
                result = {"status": "CHAT", "intent": intent, "action": None, "llm": self.llm.status()}

        saved_memories = []
        if self.memory.configured:
            for kind, content, importance in self._extract_memories(text):
                if self.memory.save(self.user_id, kind, content, importance):
                    saved_memories.append({"kind": kind, "content": content, "importance": importance})

        self.history.append({"role": "assistant", "content": reply})
        result["reply"] = reply
        result["memory"] = self.memory.status()
        result["recalled_memories"] = recalled
        result["saved_memories"] = saved_memories
        result["history"] = list(self.history)
        result["turn"] = self.turns
        return result
