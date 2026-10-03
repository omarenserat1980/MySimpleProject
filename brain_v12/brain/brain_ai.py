from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Callable, Dict, List, Optional

from .tool_protocol import ToolCallRequest, ToolCallResult, parse_tool_call


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
    """Brain facade: model routing + strict tool calling + evidence."""

    def __init__(self, provider, memory_store=None, cognitive=None, model_router=None):
        self.provider = provider
        self.model_router = model_router
        self.memory_store = memory_store
        self.cognitive = cognitive
        self.tools: Dict[str, BrainAITool] = {}

    def register_tool(self, name, description, handler, risk="low", permission=None):
        self.tools[name] = BrainAITool(name, description, handler, risk, permission)

    def status(self):
        provider_status = self.provider.status() if hasattr(self.provider, "status") else {}
        return {
            "name": "Brain AI",
            "version": "1.1",
            "provider": provider_status,
            "model_router": self.model_router.status() if self.model_router is not None else None,
            "tools": [{"name": t.name, "description": t.description,
                       "risk": t.risk, "permission": t.permission}
                      for t in self.tools.values()],
            "memory_enabled": self.memory_store is not None,
            "cognitive_loop_enabled": self.cognitive is not None,
            "tool_calling": {"protocol": "strict-json-v1", "enabled": True},
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

    def _respond(self, user_text: str, instructions: str):
        return (self.model_router.respond(
            user_text, context=self._context(), instructions=instructions
        ) if self.model_router is not None else self.provider.respond(
            user_text, context=self._context(), instructions=instructions
        ))

    @staticmethod
    def _candidate_tool_call(result: Dict[str, Any]) -> Optional[ToolCallRequest]:
        for key in ("tool_call", "tool_request"):
            if key in result:
                call = parse_tool_call(result[key])
                if call:
                    return call
        for key in ("tool_calls",):
            calls = result.get(key)
            if isinstance(calls, list) and calls:
                call = parse_tool_call(calls[0])
                if call:
                    return call
        return parse_tool_call(result.get("reply", ""))

    def _tool_result(self, call: ToolCallRequest, approved: bool) -> ToolCallResult:
        raw = self.execute_tool(call.name, call.arguments, approved)
        ok = bool(raw.get("ok", raw.get("status") == "SUCCESS"))
        status = str(raw.get("status", "SUCCESS" if ok else "FAILED"))
        return ToolCallResult(call.call_id, call.name, status, ok, raw)

    def chat(self, user_text: str, instructions: str = "", approved: bool = False) -> BrainAIResponse:
        user_text = (user_text or "").strip()
        if not user_text:
            return BrainAIResponse(False, "", "error", error="EMPTY_MESSAGE")

        base_instructions = instructions or self._system_instructions()
        result = self._respond(user_text, base_instructions)
        provider_evidence = {
            "type": "provider",
            "provider": result.get("provider"),
            "response_id": result.get("response_id"),
        }
        if not result.get("ok"):
            return BrainAIResponse(False, "", "error",
                                   model=result.get("model"),
                                   evidence=[provider_evidence],
                                   error=result.get("error"))

        call = self._candidate_tool_call(result)
        if call is None:
            return BrainAIResponse(
                True, result.get("reply", ""), "model",
                model=result.get("model"), evidence=[provider_evidence],
            )

        tool_result = self._tool_result(call, approved)
        evidence = [provider_evidence, tool_result.evidence()]
        call_record = {
            "call_id": call.call_id,
            "name": call.name,
            "arguments": call.arguments,
            "status": tool_result.status,
        }

        if tool_result.status in {"WAITING_APPROVAL", "WAITING_PERMISSION", "UNKNOWN_TOOL"}:
            return BrainAIResponse(
                False,
                "",
                "waiting_approval" if tool_result.status == "WAITING_APPROVAL" else "waiting_permission",
                model=result.get("model"),
                tool_calls=[call_record],
                evidence=evidence,
                error=tool_result.status,
            )

        if not tool_result.ok:
            return BrainAIResponse(
                False, "",
                "tool_failed",
                model=result.get("model"),
                tool_calls=[call_record],
                evidence=evidence,
                error=tool_result.status,
            )

        final_context = (
            self._context()
            + "\n\n[BRAIN_TOOL_RESULT]\n"
            + json.dumps(tool_result.result, ensure_ascii=False, default=str)
        )
        final_instructions = (
            base_instructions
            + "\nThe requested tool has now executed. "
              "Use only the supplied tool result as evidence. "
              "Return a concise final answer, not another tool call."
        )
        final_result = (self.model_router.respond(
            user_text, context=final_context, instructions=final_instructions
        ) if self.model_router is not None else self.provider.respond(
            user_text, context=final_context, instructions=final_instructions
        ))
        evidence.append({
            "type": "provider_final",
            "provider": final_result.get("provider"),
            "response_id": final_result.get("response_id"),
        })
        if not final_result.get("ok"):
            return BrainAIResponse(
                True,
                "تم تنفيذ الأداة بنجاح، لكن تعذّر توليد الرد النهائي من النموذج.",
                "tool_executed",
                model=result.get("model"),
                tool_calls=[call_record],
                evidence=evidence,
                error=final_result.get("error"),
            )
        return BrainAIResponse(
            True,
            final_result.get("reply", ""),
            "tool_executed",
            model=final_result.get("model") or result.get("model"),
            tool_calls=[call_record],
            evidence=evidence,
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
        return {"ok": True, "status": "SUCCESS", "tool": name, **result}

    @staticmethod
    def _system_instructions() -> str:
        return """أنت Brain AI داخل Electronic Brain.
أنت واجهة عقلية موحدة فوق الذاكرة والأدوات والنماذج.
إذا احتجت أداة، أخرج JSON صارماً فقط بالشكل:
{"type":"tool_call","call_id":"unique-id","name":"registered_tool","arguments":{}}
لا تطلب أداة غير موجودة في [BRAIN_TOOLS].
لا تدّعي تنفيذ تغيير أو تشغيل اختبار دون دليل من نتيجة الأداة.
الأدوات عالية الخطورة تحتاج موافقة صريحة.
بعد نتيجة الأداة، قدّم جواباً نهائياً موجزاً يعتمد على النتيجة فقط.
لا تكشف سلسلة التفكير الداخلية.
"""
