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
    """Unified Brain AI facade: conversation + memory + cognition + governed tools."""
    def __init__(self, provider, memory_store=None, cognitive=None, github=None):
        self.provider = provider
        self.memory_store = memory_store
        self.cognitive = cognitive
        self.github = github
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
        return {"name":"Brain AI","version":"1.1","provider":provider_status,
                "tools":[{"name":t.name,"description":t.description,"risk":t.risk,"permission":t.permission} for t in self.tools.values()],
                "memory_enabled":self.memory_store is not None,"cognitive_loop_enabled":self.cognitive is not None,
                "github_gateway": self.github is not None}

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

    def chat(self, user_text: str, instructions: str = "") -> BrainAIResponse:
        user_text=(user_text or "").strip()
        if not user_text: return BrainAIResponse(False,"","error",error="EMPTY_MESSAGE")
        result=self.provider.respond(user_text,context=self._context(),instructions=instructions or self._system_instructions())
        if not result.get("ok"):
            return BrainAIResponse(False,"","error",model=result.get("model"),error=result.get("error"))
        return BrainAIResponse(True,result.get("reply",""),"model",model=result.get("model"),
            evidence=[{"type":"provider","provider":result.get("provider"),"response_id":result.get("response_id")}])

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
أنت واجهة عقلية موحدة فوق الذاكرة والأدوات والنماذج، ولست مجرد chatbot.
افهم الطلب، استخدم السياق المتاح، واختر الأداة المناسبة عندما يلزم تنفيذ فعل.
لا تختلق ذاكرة أو صلاحية أو نتيجة أداة.
لا تدّعي تنفيذ تغيير أو تشغيل اختبار دون دليل.
العمليات الحساسة تحتاج موافقة وصلاحية صريحة.
بعد التنفيذ يجب فحص النتيجة وإرجاع Evidence واضح.
لا تكشف سلسلة التفكير الداخلية؛ قدم ملخصاً عملياً للخطوات والنتائج."""
