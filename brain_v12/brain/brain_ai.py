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
    def __init__(self, provider, memory_store=None, cognitive=None, github=None, chatgpt_bridge=None, model_router=None, max_tool_rounds=4, max_tool_retries=2):
        self.provider = provider
        self.model_router = model_router
        self.memory_store = memory_store
        self.cognitive = cognitive
        self.github = github
        if chatgpt_bridge is None:
            try:
                from .chatgpt_tool_bridge import build_chatgpt_tool_bridge_from_environment
                chatgpt_bridge = build_chatgpt_tool_bridge_from_environment()
            except Exception:
                chatgpt_bridge = None
        self.chatgpt_bridge = chatgpt_bridge
        self.max_tool_rounds = max(1, int(max_tool_rounds))
        self.max_tool_retries = max(0, int(max_tool_retries))
        self.max_repair_attempts = 1
        self.tools: Dict[str, BrainAITool] = {}
        self._register_builtin_tools()

    def register_tool(self, name, description, handler, risk="low", permission=None):
        self.tools[name] = BrainAITool(name, description, handler, risk, permission)

    def connect_supervisor(self, problem_solver):
        """Expose the bounded Supervisor pipeline through Brain Chat."""
        def solve(params):
            goal = str((params or {}).get("goal", "")).strip()
            if not goal:
                # Keep the empty-input contract consistent with ProblemSolver.
                return {"ok": False, "status": "EMPTY_GOAL"}
            result = problem_solver.solve(goal)
            return result

        self.register_tool(
            "supervisor.solve",
            "Run a bounded Brain Supervisor cycle for a user goal. Returns the selected action, action-level verification evidence, and a separate objective verification status. Never claim the objective is complete unless objective_verified is true.",
            solve,
            risk="medium",
        )

    def _register_builtin_tools(self):
        if self.github is None:
            try:
                from ..github_control_plane import GitHubControlPlane
                self.github = GitHubControlPlane()
            except Exception:
                self.github = None
        self.register_tool("chatgpt.capabilities", "List the ChatGPT host-tool capabilities visible to Brain.", lambda p: self._chatgpt_capabilities())
        self.register_tool("chatgpt.discover", "Find the most relevant ChatGPT host tool for a natural-language task.", lambda p: self._chatgpt_discover(p))
        self.register_tool("chatgpt.bridge_status", "Report whether a real ChatGPT host-tool bridge is configured.", lambda p: self._chatgpt_bridge_status())
        self.register_tool("chatgpt.execute", "Delegate a ChatGPT host-tool call only through a configured fail-closed bridge.", lambda p: self._chatgpt_execute(p), risk="medium")
        from .success_bot import SuccessBot
        self.success_bot = SuccessBot()
        self.register_tool("success.create", "Create a bounded goal that cannot become success without verification evidence.", lambda p: self._success_create(p))
        self.register_tool("success.start", "Start execution of a registered Success Bot goal through Brain Supervisor.", lambda p: self._success_start(p))
        self.register_tool("success.update", "Record measured progress and evidence for a Success Bot goal.", lambda p: self._success_update(p))
        self.register_tool("success.verify", "Verify a Success Bot goal and only then allow VERIFIED_COMPLETED.", lambda p: self._success_verify(p))
        self.register_tool("success.status", "Read the current Success Bot goal state and evidence.", lambda p: self._success_status(p))
        g = self.github
        if g is None:
            self._register_github_surface_without_runtime()
            return
        self.register_tool("github.capabilities", "List governed GitHub capability domains.", lambda p: g.capability_catalog())
        self.register_tool("github.repository", "Read repository metadata.", lambda p: g.repository(p["owner"], p["repo"]))
        self.register_tool("github.contents", "Read repository file or directory contents.", lambda p: g.contents(p["owner"], p["repo"], p.get("path",""), p.get("ref")))
        self.register_tool("github.issues", "Read repository issues.", lambda p: g.issues(p["owner"], p["repo"], p.get("number")))
        self.register_tool("github.pull_request", "Read a pull request.", lambda p: g.pull_request(p["owner"], p["repo"], int(p["number"])))
        self.register_tool("github.actions_runs", "Read GitHub Actions runs.", lambda p: g.actions_runs(p["owner"], p["repo"], int(p.get("page",1)), int(p.get("per_page",30))))
        self.register_tool("github.releases", "Read repository releases.", lambda p: g.releases(p["owner"], p["repo"]))
        self.register_tool("github.search", "Search GitHub resources.", lambda p: g.search(p["query"], p.get("search_type","repositories")))
        self.register_tool("github.write_contents", "Write repository contents; explicit approval required.", lambda p: g.write_contents(p["owner"], p["repo"], p["path"], p["body"], approved=bool(p.get("approved",False))), risk="high", permission="code.write")
        self.register_tool("github.rest", "Governed full GitHub REST gateway for operations not covered by a dedicated Brain tool. Mutations require explicit approval.", lambda p: g.rest(p["method"], p["path"], p.get("capability","repo.read"), approved=bool(p.get("approved",False)), params=p.get("params"), body=p.get("body")), risk="high", permission="github.write")
        self.register_tool("github.registry", "Discover GitHub tools grouped by domain and risk.", lambda p: self._github_registry())
        self.register_tool("github.discover", "Find the most relevant GitHub tool for a natural-language task.", lambda p: self._github_discover(p))
        self.register_tool("github.read", "Execute an arbitrary governed GitHub read operation through the REST gateway.", lambda p: g.rest(p["method"], p["path"], p.get("capability","repo.read"), params=p.get("params"), body=p.get("body")))
        self.register_tool("github.write", "Execute an arbitrary governed GitHub mutation through the REST gateway; explicit approval required.", lambda p: g.rest(p["method"], p["path"], p.get("capability","repo.write"), approved=bool(p.get("approved",False)), params=p.get("params"), body=p.get("body")), risk="high", permission="github.write")
        self._register_github_tool_surface()


    def _register_github_surface_without_runtime(self):
        """Register the complete surface even when the runtime transport is unavailable."""
        from ..github_capability_registry import GITHUB_TOOLS, WRITE_OR_MUTATING_TOOLS
        for tool_name in GITHUB_TOOLS:
            mutable = tool_name in WRITE_OR_MUTATING_TOOLS
            def unavailable(params, _tool=tool_name):
                return {"ok": False, "status": "GITHUB_RUNTIME_UNAVAILABLE", "tool": _tool}
            self.register_tool("github.tool." + tool_name, "GitHub capability: " + tool_name.replace("_", " "),
                               unavailable, risk="high" if mutable else "low",
                               permission="github.write" if mutable else None)

    def _register_github_tool_surface(self):
        """Expose every governed GitHub capability as a first-class Brain tool."""
        from ..github_capability_registry import GITHUB_TOOLS, WRITE_OR_MUTATING_TOOLS
        for tool_name in GITHUB_TOOLS:
            brain_name = "github.tool." + tool_name
            mutable = tool_name in WRITE_OR_MUTATING_TOOLS
            capability = "repo.write" if mutable else "repo.read"
            risk = "high" if mutable else "low"
            permission = "github.write" if mutable else None
            def handler(params, _cap=capability):
                method = str(params.get("method", "GET")).upper()
                path = str(params.get("path", ""))
                if not path.startswith("/"):
                    raise ValueError("github tool requires an absolute REST path")
                return self.github.rest(method, path, capability=_cap,
                                        approved=bool(params.get("approved", False)),
                                        params=params.get("query"), body=params.get("body"))
            self.register_tool(brain_name, "GitHub capability: " + tool_name.replace("_", " "), handler, risk=risk, permission=permission)

    def _github_discover(self, params):
        """Rank the registered GitHub tools for a natural-language task."""
        from ..github_capability_registry import GITHUB_TOOLS
        query = str(params.get("query", "")).lower()
        tokens = {t for t in query.replace("/", " ").replace("-", " ").split() if len(t) > 2}
        ranked = []
        for name in GITHUB_TOOLS:
            words = set(name.replace("_", " ").split())
            score = len(tokens & words)
            if score:
                ranked.append((score, name))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        return {"ok": True, "query": query, "candidates": [{"tool": n, "score": score, "brain_tool": "github.tool." + n} for score, n in ranked[:10]]}

    def _success_create(self, params):
        state = self.success_bot.create_goal(params.get("goal", ""), params.get("success_criteria"))
        return {"ok": True, "status": "GOAL_CREATED", "goal": self.success_bot.snapshot(state)}

    def _success_start(self, params):
        state = self.success_bot.get_goal(params.get("goal_id", ""))
        if state is None:
            return {"ok": False, "status": "GOAL_NOT_FOUND"}
        job = self.success_bot.start(state, steps=params.get("steps"))
        return {"ok": True, "status": "RUNNING", "goal": self.success_bot.snapshot(state), "job": job}

    def _success_update(self, params):
        state = self.success_bot.get_goal(params.get("goal_id", ""))
        if state is None:
            return {"ok": False, "status": "GOAL_NOT_FOUND"}
        updated = self.success_bot.update(
            state,
            verified=bool(params.get("verified", False)),
            evidence=params.get("evidence"),
            progress=params.get("progress"),
        )
        return {"ok": True, "status": updated.status, "goal": self.success_bot.snapshot(updated)}

    def _success_verify(self, params):
        state = self.success_bot.get_goal(params.get("goal_id", ""))
        if state is None:
            return {"ok": False, "status": "GOAL_NOT_FOUND"}
        verified = self.success_bot.verify(state, params.get("verification") or {})
        return {"ok": True, "status": verified.status, "goal": self.success_bot.snapshot(verified)}

    def _success_status(self, params):
        state = self.success_bot.get_goal(params.get("goal_id", ""))
        if state is None:
            return {"ok": False, "status": "GOAL_NOT_FOUND"}
        return {"ok": True, "status": state.status, "goal": self.success_bot.snapshot(state)}

    def _chatgpt_capabilities(self):
        from .chatgpt_tool_registry import capability_catalog
        return capability_catalog()

    def _chatgpt_discover(self, params):
        from .chatgpt_tool_registry import discover
        return discover(params.get("query", ""), params.get("limit", 10))

    def _chatgpt_bridge_status(self):
        if self.chatgpt_bridge is None:
            return {"ok": True, "status": "BRIDGE_UNAVAILABLE", "available": False, "evidence_required": True}
        return {"ok": True, **self.chatgpt_bridge.status()}

    def _chatgpt_execute(self, params):
        if self.chatgpt_bridge is None:
            return {"ok": False, "status": "BRIDGE_UNAVAILABLE", "error": "No ChatGPT host-tool bridge configured."}
        from .chatgpt_tool_bridge import ToolBridgeRequest
        request = ToolBridgeRequest(
            tool=str(params.get("tool", "")),
            arguments=params.get("arguments") if isinstance(params.get("arguments"), dict) else {},
            request_id=str(params.get("request_id", "")),
        )
        result = self.chatgpt_bridge.dispatch(request)
        return {"ok": result.ok, "status": result.status, "request_id": result.request_id, "result": result.result, "error": result.error}

    def _github_registry(self):
        domains = {
            "repositories": ["github.repository"],
            "contents": ["github.contents", "github.write_contents"],
            "issues": ["github.issues"],
            "pull_requests": ["github.pull_request"],
            "actions": ["github.actions_runs"],
            "releases": ["github.releases"],
            "search": ["github.search"],
            "gateway": ["github.read", "github.write", "github.rest"],
        }
        return {"ok": True, "version": "1.0", "domains": domains,
                "tool_count": sum(len(v) for v in domains.values()),
                "policy": "reads allowed by capability; mutations require explicit approval"}

    def status(self):
        provider_status = self.provider.status() if hasattr(self.provider, "status") else {}
        router_status = self.model_router.status() if self.model_router is not None else {"enabled": False}
        return {"name":"Brain AI","version":"1.2","provider":provider_status, "model_router": router_status,
                "tools":[{"name":t.name,"description":t.description,"risk":t.risk,"permission":t.permission} for t in self.tools.values()],
                "memory_enabled":self.memory_store is not None,"cognitive_loop_enabled":self.cognitive is not None,
                "github_gateway": self.github is not None, "chatgpt_bridge": self._chatgpt_bridge_status(), "tool_loop_enabled": True, "max_tool_rounds": self.max_tool_rounds, "self_healing_enabled": True, "max_tool_retries": self.max_tool_retries, "diagnose_repair_enabled": True, "max_repair_attempts": self.max_repair_attempts}

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
        if self.model_router is not None:
            return self.model_router.respond(prompt, context=context, instructions=instructions)
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
                return self._with_layer_trace(BrainAIResponse(False,"","error",model=result.get("model"),tool_calls=calls,evidence=evidence,error=result.get("error")), user_text, instructions)
            evidence.append({"type":"provider","provider":result.get("provider"),"model":result.get("model"),"response_id":result.get("response_id"),"round":round_no})
            if result.get("routing") or result.get("evidence", {}).get("type") == "model_routing":
                evidence.append({"type":"model_routing", **(result.get("routing") or result.get("evidence") or {})})
            intents=self._tool_intents(result)
            if not intents:
                return self._with_layer_trace(BrainAIResponse(True,result.get("reply",""),"model",model=result.get("model"),tool_calls=calls,evidence=evidence), user_text, instructions)
            for intent in intents:
                name=intent["name"]
                params=intent["params"]
                outcome=self.execute_tool(name, params, approved=approved)
                attempts=0
                while not self._verify_tool_outcome(outcome) and self._retryable(outcome) and attempts < self.max_tool_retries:
                    attempts += 1
                    evidence.append({"type":"self_healing","tool":name,"action":"retry","attempt":attempts,"round":round_no,"reason":outcome.get("error") or outcome.get("status")})
                    outcome=self.execute_tool(name, params, approved=approved)
                repair_count=0
                if not self._verify_tool_outcome(outcome) and self._repairable(outcome):
                    repaired=self._diagnose_and_repair(user_text, name, params, outcome, approved=approved)
                    if repaired is not None:
                        repair_count=1
                        outcome=repaired["outcome"]
                        evidence.append({"type":"diagnose_repair","tool":name,"action":"corrected_tool_call","replacement":repaired["intent"],"verified":self._verify_tool_outcome(outcome)})
                record={"round":round_no,"tool":name,"params":params,"result":outcome,"retry_count":attempts,"repair_count":repair_count,"verified":self._verify_tool_outcome(outcome)}
                calls.append(record)
                trace.append(record)
                evidence.append({"type":"tool","tool":name,"status":outcome.get("status","EXECUTED" if outcome.get("ok") else "FAILED"),"round":round_no,"verified":record["verified"],"retry_count":attempts})
                if name == "supervisor.solve":
                    verification = outcome.get("verification", {})
                    run = outcome.get("execution", {}).get("solution_run", {})
                    evidence.append({
                        "type": "supervisor_execution",
                        "tool": name,
                        "run_id": outcome.get("run_id"),
                        "supervisor_job_id": (outcome.get("supervisor_job") or {}).get("job_id"),
                        "status": outcome.get("status"),
                        "verified": verification.get("status") == "VERIFIED",
                        "objective_verified": outcome.get("objective_verified") is True,
                        "evidence_ref": verification.get("evidence"),
                    })
                    for item in run.get("attempts", []):
                        evidence.append({
                            "type": "supervisor_attempt",
                            "tool": item.get("alternative_id"),
                            "status": item.get("status"),
                            "verified": item.get("status") == "VERIFIED",
                            "error": item.get("error"),
                        })
                if not outcome.get("ok") and outcome.get("status") in {"WAITING_APPROVAL","WAITING_PERMISSION"}:
                    return self._with_layer_trace(BrainAIResponse(False,"Approval or permission is required before this action can continue.","approval",model=result.get("model"),tool_calls=calls,evidence=evidence,error=outcome.get("status")), user_text, instructions)
        return self._with_layer_trace(BrainAIResponse(False,"Tool execution limit reached before a final answer was produced.","limit",model=(result or {}).get("model"),tool_calls=calls,evidence=evidence,error="TOOL_LOOP_LIMIT"), user_text, instructions)

    @staticmethod
    def _verify_tool_outcome(outcome: Dict[str, Any]) -> bool:
        if not isinstance(outcome, dict):
            return False
        if not outcome.get("ok"):
            return False
        if outcome.get("tool") == "supervisor.solve" and outcome.get("objective_verified") is not True:
            return False
        return outcome.get("status", "EXECUTED") not in {"FAILED", "INVALID_TOOL_RESULT"}

    @staticmethod
    def _retryable(outcome: Dict[str, Any]) -> bool:
        return isinstance(outcome, dict) and outcome.get("status") == "FAILED"

    @staticmethod
    def _repairable(outcome: Dict[str, Any]) -> bool:
        return isinstance(outcome, dict) and outcome.get("status") in {"FAILED", "INVALID_TOOL_RESULT", "UNKNOWN_TOOL"}

    def _diagnose_and_repair(self, user_text, failed_name, failed_params, outcome, approved=False):
        prompt = "Diagnose this failed Brain tool call and return exactly one corrected tool intent under tool_calls as JSON. Use only BRAIN_TOOLS. Failure evidence:\n" + json.dumps({"user_request": user_text, "failed_tool": failed_name, "failed_params": failed_params, "failure": outcome}, ensure_ascii=False, default=str)
        try:
            result = self.provider.respond(prompt, context=self._context(), instructions=self._system_instructions())
        except Exception:
            return None
        intents = self._tool_intents(result if isinstance(result, dict) else {})
        if len(intents) != 1:
            return None
        intent = intents[0]
        if intent["name"] not in self.tools or (intent["name"] == failed_name and intent["params"] == failed_params):
            return None
        return {"intent": intent, "outcome": self.execute_tool(intent["name"], intent["params"], approved=approved)}

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
عند الحاجة إلى قدرة يوفرها ChatGPT، استخدم chatgpt.discover ثم chatgpt.capabilities؛ لا تدّعِ تنفيذ أداة مضيفة ما لم يظهر دليل تنفيذ فعلي من الجسر.
لا تختلق ذاكرة أو صلاحية أو نتيجة أداة.
لا تدّعي تنفيذ تغيير أو تشغيل اختبار دون دليل.
العمليات الحساسة تحتاج موافقة وصلاحية صريحة.
بعد تنفيذ الأداة، استخدم BRAIN_TOOL_TRACE لصياغة الرد النهائي.
أداة supervisor.solve تسجل تنفيذ خطوة آمنة وقد تثبت نجاح تلك الخطوة فقط؛ لا تقل إن هدف المستخدم اكتمل إلا إذا objective_verified=true في الدليل.
لا تكشف سلسلة التفكير الداخلية؛ قدم ملخصاً عملياً للخطوات والنتائج."""
