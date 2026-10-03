from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BrainAITool:
    name: str
    description: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    risk: str = "low"
    permission: Optional[str] = None


@dataclass
class BrainAIResponse:
    ok: bool
    reply: str
    mode: str
    model: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class BrainAI:
    """Gemini-like Brain facade: conversation + memory + tools + verification."""

    def __init__(self, provider, memory_store=None, cognitive=None):
        self.provider = provider
        self.memory_store = memory_store
        self.cognitive = cognitive
        self.tools: Dict[str, BrainAITool] = {}

    def register_tool(self, name, description, handler, risk="low", permission=None):
        self.tools[name] = BrainAITool(name, description, handler, risk, permission)

    def status(self):
        provider_status = self.provider.status() if hasattr(self.provider, "status") else {}
        return {
            "name": "Brain AI",
            "version": "1.0",
            "provider": provider_status,
            "tools": [{"name": t.name, "description": t.description,
                       "risk": t.risk, "permission": t.permission}
                      for t in self.tools.values()],
            "memory_enabled": self.memory_store is not None,
            "cognitive_loop_enabled": self.cognitive is not None,
        }

    def _context(self) -> str:
        parts = []
        if self.memory_store is not None:
            try:
                parts.append("[BRAIN_MEMORY]\n" + str(self.memory_store.memories()[-12:]))
            except Exception:
                parts.append("[BRAIN_MEMORY]\nUNAVAILABLE")
        if self.cognitive is not None:
            try:
                parts.append("[BRAIN_STATE]\n" + str(self.cognitive.store.state()))
            except Exception:
                parts.append("[BRAIN_STATE]\nUNAVAILABLE")
        if self.tools:
            catalog = [{"name": t.name, "description": t.description, "risk": t.risk}
                       for t in self.tools.values()]
            parts.append("[BRAIN_TOOLS]\n" + str(catalog))
        return "\n\n".join(parts)

    def chat(self, user_text: str, instructions: str = "") -> BrainAIResponse:
        user_text = (user_text or "").strip()
        if not user_text:
            return BrainAIResponse(False, "", "error", error="EMPTY_MESSAGE")
        result = self.provider.respond(
            user_text, context=self._context(),
            instructions=instructions or self._system_instructions(),
        )
        if not result.get("ok"):
            return BrainAIResponse(False, "", "error",
                                   model=result.get("model"),
                                   error=result.get("error"))
        return BrainAIResponse(
            True, result.get("reply", ""), "model",
            model=result.get("model"),
            evidence=[{"type": "provider", "provider": result.get("provider"),
                       "response_id": result.get("response_id")}],
        )

    def execute_tool(self, name: str, params: Optional[Dict[str, Any]] = None,
                     approved: bool = False) -> Dict[str, Any]:
        tool = self.tools.get(name)
        if not tool:
            return {"ok": False, "status": "UNKNOWN_TOOL", "tool": name}
        if tool.risk == "high" and not approved:
            return {"ok": False, "status": "WAITING_APPROVAL", "tool": name}
        if tool.permission and self.cognitive is not None:
            grants = getattr(getattr(self.cognitive, "permissions", None), "grants", set())
            if tool.permission not in grants:
                return {"ok": False, "status": "WAITING_PERMISSION",
                        "tool": name, "permission": tool.permission}
        try:
            result = tool.handler(params or {})
        except Exception as exc:
            return {"ok": False, "status": "FAILED", "tool": name,
                    "error": str(exc)[:1000]}
        if not isinstance(result, dict):
            return {"ok": False, "status": "INVALID_TOOL_RESULT", "tool": name}
        return {"tool": name, **result}

    @staticmethod
    def _system_instructions() -> str:
        return """أنت Brain AI داخل Electronic Brain.
أنت واجهة عقلية موحدة فوق الذاكرة والأدوات والنماذج، ولست مجرد chatbot.
افهم الطلب، استخدم السياق المتاح، وكن واضحاً بشأن ما تم تنفيذه وما لم يتم.
لا تختلق ذاكرة أو صلاحية أو نتيجة أداة.
لا تدّعي تنفيذ تغيير أو تشغيل اختبار دون دليل من الأداة.
عند الحاجة إلى تنفيذ فعل، اقترح الأداة المناسبة وحدود الصلاحية، ثم تحقّق من النتيجة.
لا تكشف سلسلة التفكير الداخلية؛ قدم ملخصاً عملياً للخطوات والنتائج.
"""
