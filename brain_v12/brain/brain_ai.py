from __future__ import annotations

import json
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
    """Unified Brain AI facade with governed model-driven tool execution."""
    def __init__(self, provider, memory_store=None, cognitive=None, github=None, max_tool_rounds=4, max_tool_retries=2):
        self.provider = provider
        self.memory_store = memory_store
        self.cognitive = cognitive
        self.github = github
        self.max_tool_rounds = max(1, int(max_tool_rounds))
        self.max_tool_retries = max(0, int(max_tool_retries))
        self.tools: Dict[str, BrainAITool] = {}
        self._register_builtin_tools()

    def register_tool(self, name, description, handler, risk="low", permission=None):
        self.tools[name] = BrainAITool(name, description, handler, risk, permission)

    def _register_builtin_tools(self):
        if self.github is None:
            try:
                from ..github_control_plane import GitHubControlPlane
                self.github = GitHubControlPlane()
            except Exception:
                return
        g = self.github
        self.register_tool("github.capabilities", "List governed GitHub capability domains.", lambda p: g.capability_catalog())
        self.register_tool("github.repository", "Read repository metadata.", lambda p: g.repository(p["owner"], p["repo"]))
        self.register_tool("github.contents", "Read repository file or directory contents.", lambda p: g.contents(p["owner"], p["repo"], p.get("path",""), p.get("ref")))
        self.register_tool("github.issues", "Read repository issues.", lambda p: g.issues(p["owner"], p["repo"], p.get("number")))
        self.register_tool("github.pull_request", "Read a pull request.", lambda p: g.pull_request(p["owner"], p["repo"], int(p["number"])))
        self.register_tool("github.actions_runs", "Read GitHub Actions runs.", lambda p: g.actions_runs(p["owner"], p["repo"], int(p.get("page",1)), int(p.get("per_page",30))))
        self.register_tool("github.releases", "Read repository releases.", lambda p: g.releases(p["owner"], p["repo"]))
        self.register_tool("github.search", "Search GitHub resources.", lambda p: g.search(p["query"], p.get("search_type","repositories")))
        self.register_tool("github.write_contents", "Write repository contents; explicit approval required.", lambda p: g.write_contents(p["owner"], p["repo"], p["path"], p["body"], approved=bool(p.get("approved",False))), risk="high", permission="code.write")

    def status(self):
        provider_status = self.provider.status() if hasattr(self.provider, "status") else {}
        return {"name":"Brain AI","version":"1.2","provider":provider_status,
                "tools":[{"name":t.name,"description":t.description,"risk":t.risk,"permission":t.permission} for t in self.tools.values()],
                "memory_enabled":self.memory_store is not None,"cognitive_loop_enabled":self.cognitive is not None,
                "github_gateway": self.github is not None, "tool_loop_enabled": True, "max_tool_rounds": self.max_tool_rounds, "self_healing_enabled": True, "max_tool_retries": self.max_tool_retries}

    def _context(self) -> str:
        parts=[]
        if self.memory_store is not None:
            try: parts.append("[BRAIN_MEMORY]\n"+str(self.memory_store.memories()[-12:]))
            except Exception: parts.append("[BRAIN_MEMORY]\nUNAVAILABLE")
        if self.cognitive is not None:
            try: parts.append("[BRAIN_STATE]\n"+str(self.cognitive.store.state()))
            except Exception: parts.append("[BRAIN_STATE]\nUNAVAILABLE")
        if self.tools:
            parts.append("[BRAIN_TOOLS]\n"+str([{"name":t.name,"description":t.description,"risk":t.risk,"permission":t.permission} for t in self.tools.values()]))
        return "\n\n".join(parts)

    def _provider_respond(self, user_text, context, instructions, tool_trace):
        prompt = user_text
        if tool_trace:
            prompt += "\n\n[BRAIN_TOOL_TRACE]\n" + json.dumps(tool_trace, ensure_ascii=False, default=str)
        return self.provider.respond(prompt, context=context, instructions=instructions)

    @staticmethod
    def _tool_intents(result):
        intents = result.get("tool_calls") or result.get("tools") or result.get("tool_call")
        if not intents:
            return []
        if isinstance(intents, dict):
            intents = [intents]
        normalized = []
        for item in intents:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("tool")
            params = item.get("params") or item.get("arguments") or {}
            if isinstance(params, str):
                try: params = json.loads(params)
                except json.JSONDecodeError: params = {}
            if name:
                normalized.append({"name": name, "params": params if isinstance(params, dict) else {}})
        return normalized

    def chat(self, user_text: str, instructions: str = "", approved=False) -> BrainAIResponse:
        user_text=(user_text or "").strip()
        if not user_text: return BrainAIResponse(False,"","error",error="EMPTY_MESSAGE")
        evidence=[]
        calls=[]
        trace=[]
        result=None
        for round_no in range(1, self.max_tool_rounds + 1):
            result=self._provider_respond(user_text, self._context(), instructions or self._system_instructions(), trace)
            if not result.get("ok"):
                return BrainAIResponse(False,"","error",model=result.get("model"),tool_calls=calls,evidence=evidence,error=result.get("error"))
            evidence.append({"type":"provider","provider":result.get("provider"),"response_id":result.get("response_id"),"round":round_no})
            intents=self._tool_intents(result)
            if not intents:
                return BrainAIResponse(True,result.get("reply",""),"model",model=result.get("model"),tool_calls=calls,evidence=evidence)
            for intent in intents:
                name=intent["name"]
                params=intent["params"]
                outcome=self.execute_tool(name, params, approved=approved)
                attempts=0
                while not self._verify_tool_outcome(outcome) and self._retryable(outcome) and attempts < self.max_tool_retries:
                    attempts += 1
                    evidence.append({"type":"self_healing","tool":name,"action":"retry","attempt":attempts,"round":round_no,"reason":outcome.get("error") or outcome.get("status")})
                    outcome=self.execute_tool(name, params, approved=approved)
                record={"round":round_no,"tool":name,"params":params,"result":outcome,"retry_count":attempts,"verified":self._verify_tool_outcome(outcome)}
                calls.append(record)
                trace.append(record)
                evidence.append({"type":"tool","tool":name,"status":outcome.get("status","EXECUTED" if outcome.get("ok") else "FAILED"),"round":round_no,"verified":record["verified"],"retry_count":attempts})
                if not outcome.get("ok") and outcome.get("status") in {"WAITING_APPROVAL","WAITING_PERMISSION"}:
                    return BrainAIResponse(False,"Approval or permission is required before this action can continue.","approval",model=result.get("model"),tool_calls=calls,evidence=evidence,error=outcome.get("status"))
        return BrainAIResponse(False,"Tool execution limit reached before a final answer was produced.","limit",model=(result or {}).get("model"),tool_calls=calls,evidence=evidence,error="TOOL_LOOP_LIMIT")

    @staticmethod
    def _verify_tool_outcome(outcome: Dict[str, Any]) -> bool:
        if not isinstance(outcome, dict):
            return False
        if not outcome.get("ok"):
            return False
        return outcome.get("status", "EXECUTED") not in {"FAILED", "INVALID_TOOL_RESULT"}

    @staticmethod
    def _retryable(outcome: Dict[str, Any]) -> bool:
        return isinstance(outcome, dict) and outcome.get("status") == "FAILED"

    def execute_tool(self, name: str, params: Optional[Dict[str, Any]]=None, approved: bool=False) -> Dict[str, Any]:
        tool=self.tools.get(name)
        if not tool: return {"ok":False,"status":"UNKNOWN_TOOL","tool":name}
        if tool.risk=="high" and not approved: return {"ok":False,"status":"WAITING_APPROVAL","tool":name}
        if tool.permission and self.cognitive is not None:
            grants=getattr(getattr(self.cognitive,"permissions",None),"grants",set())
            if tool.permission not in grants: return {"ok":False,"status":"WAITING_PERMISSION","tool":name,"permission":tool.permission}
        try: result=tool.handler(params or {})
        except Exception as exc: return {"ok":False,"status":"FAILED","tool":name,"error":str(exc)[:1000]}
        if not isinstance(result,dict): return {"ok":False,"status":"INVALID_TOOL_RESULT","tool":name}
        return {"tool":name,"ok":True,**result}

    @staticmethod
    def _system_instructions() -> str:
        return """أنت Brain AI داخل Electronic Brain.
أنت واجهة عقلية موحدة فوق الذاكرة والأدوات والنماذج.
إذا احتاج الطلب فعلاً إلى أداة، أرجع tool_calls منظمة بالشكل:
{"tool_calls":[{"name":"github.repository","params":{"owner":"...","repo":"..."}}]}
استخدم فقط أسماء الأدوات الموجودة في BRAIN_TOOLS.
لا تختلق ذاكرة أو صلاحية أو نتيجة أداة.
لا تدّعي تنفيذ تغيير أو تشغيل اختبار دون دليل.
العمليات الحساسة تحتاج موافقة وصلاحية صريحة.
بعد تنفيذ الأداة، استخدم BRAIN_TOOL_TRACE لصياغة الرد النهائي.
لا تكشف سلسلة التفكير الداخلية؛ قدم ملخصاً عملياً للخطوات والنتائج."""
