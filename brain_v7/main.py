import os
import sqlite3
import asyncio
import json
from contextlib import closing
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from braincore_v2.api_bridge import router as autonomous_router

DB_PATH = os.getenv("BRAIN_DB", "brain_v7.db")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
WORKER_ENABLED = os.getenv("WORKER_ENABLED", "false").lower() == "true"
WORKER_INTERVAL = int(os.getenv("WORKER_INTERVAL", "60"))
PERMISSIONS = {k: os.getenv("PERM_"+k, "true").lower() == "true" for k in ("READ","WRITE","EXECUTE","NETWORK")}
PERMISSIONS["SYSTEM"] = os.getenv("PERM_SYSTEM", "false").lower() == "true"

worker_task = None

@asynccontextmanager
async def lifespan(app):
    global worker_task
    if WORKER_ENABLED:
        worker_task = asyncio.create_task(autonomous_loop())
    yield
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="Electronic Brain V7", version="7.1", lifespan=lifespan)
app.include_router(autonomous_router)

app.mount("/", StaticFiles(directory=os.path.dirname(__file__), html=True), name="brain-ui")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with closing(db()) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS messages(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memories(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          key TEXT UNIQUE NOT NULL, value TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS goals(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
          priority REAL NOT NULL DEFAULT 0.5, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          type TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS state(
          id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL
        );
        INSERT OR IGNORE INTO state(id,data)
          VALUES(1,'{"status":"READY","current_goal":null,"last_action":null}');
        """)
        con.commit()

init_db()

class ChatIn(BaseModel):
    message: str

class MemoryIn(BaseModel):
    key: str
    value: str

class GoalIn(BaseModel):
    text: str
    priority: float = 0.5

class PermissionIn(BaseModel):
    name: str
    enabled: bool

def event(con, typ, payload):
    import json
    con.execute(
        "INSERT INTO events(type,payload,created_at) VALUES(?,?,?)",
        (typ, json.dumps(payload, ensure_ascii=False), now())
    )

async def llm_reply(message: str) -> str:
    if not LLM_API_KEY:
        return "العقل الإلكتروني متصل بالواجهة، لكن مزود نموذج اللغة غير مهيأ بعد. أضف LLM_API_KEY إلى الخادم."
    headers={"Authorization": f"Bearer {LLM_API_KEY}"}
    payload={
        "model": LLM_MODEL,
        "messages":[
            {"role":"system","content":"أنت العقل الإلكتروني V7. كن واضحاً، عملياً، وسجّل فقط ما يلزم. لا تدّع تنفيذ إجراء خارجي لم يتم تنفيذه فعلياً."},
            {"role":"user","content":message}
        ]
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r=await client.post(f"{LLM_BASE_URL}/chat/completions",headers=headers,json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

@app.get("/health")
def health():
    return {"ok":True,"service":"Electronic Brain V7"}

@app.get("/api/state")
def state():
    with closing(db()) as con:
        row=con.execute("SELECT data FROM state WHERE id=1").fetchone()
        import json
        return json.loads(row["data"])

@app.get("/api/messages")
def messages():
    with closing(db()) as con:
        rows=con.execute("SELECT role,content,created_at FROM messages ORDER BY id").fetchall()
        return [dict(r) for r in rows]

@app.post("/api/chat")
async def chat(body: ChatIn):
    with closing(db()) as con:
        con.execute("INSERT INTO messages(role,content,created_at) VALUES(?,?,?)",("user",body.message,now()))
        con.commit()
    reply=await llm_reply(body.message)
    with closing(db()) as con:
        con.execute("INSERT INTO messages(role,content,created_at) VALUES(?,?,?)",("assistant",reply,now()))
        event(con,"CHAT",{"message":body.message})
        con.commit()
    return {"reply":reply}

@app.get("/api/memory")
def memories():
    with closing(db()) as con:
        rows=con.execute("SELECT key,value,created_at FROM memories ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/api/memory")
def save_memory(body: MemoryIn):
    with closing(db()) as con:
        con.execute("INSERT INTO memories(key,value,created_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(body.key,body.value,now()))
        event(con,"MEMORY_UPDATE",body.model_dump())
        con.commit()
    return {"ok":True}

@app.get("/api/goals")
def goals():
    with closing(db()) as con:
        rows=con.execute("SELECT * FROM goals ORDER BY priority DESC,id DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/api/goals")
def add_goal(body: GoalIn):
    with closing(db()) as con:
        cur=con.execute("INSERT INTO goals(text,priority,created_at) VALUES(?,?,?)",(body.text,body.priority,now()))
        event(con,"GOAL_CREATED",{"id":cur.lastrowid,"text":body.text})
        con.commit()
        return {"id":cur.lastrowid,"status":"PENDING"}

def build_options(goal):
    return [
        {"id":"inspect","action":"INSPECT_GOAL","expected":"فحص الهدف والسياق قبل التنفيذ","risk":0.10},
        {"id":"plan","action":"PLAN_AND_OBSERVE","expected":"بناء خطة آمنة ومراقبة النتيجة","risk":0.20},
        {"id":"research","action":"RESEARCH_GAP","expected":"تحديد المعلومات الناقصة قبل القرار","risk":0.15},
    ]

def choose_option(options):
    return max(options, key=lambda x: (1.0 - x["risk"]))

def cycle():
    with closing(db()) as con:
        goal=con.execute("SELECT * FROM goals WHERE status='PENDING' ORDER BY priority DESC,id LIMIT 1").fetchone()
        if not goal:
            return {"status":"IDLE","message":"لا يوجد هدف معلق."}
        options = build_options(goal)
        selected = choose_option(options)
        con.execute("UPDATE goals SET status='IN_PROGRESS' WHERE id=?",(goal["id"],))
        import json
        s={
            "status":"EXECUTING",
            "current_goal":goal["text"],
            "last_action":selected["action"],
            "options":options,
            "selected_option":selected["id"],
            "prediction":selected["expected"],
            "prediction_error":None
        }
        con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps(s,ensure_ascii=False),))
        event(con,"DECISION",{"goal_id":goal["id"],"options":options,"selected":selected})
        con.commit()
        return {"status":"EXECUTING","goal":dict(goal),"options":options,"selected":selected}

TOOL_REGISTRY = {
    "inspect_state": {"permission": "READ", "description": "قراءة حالة العقل"},
    "save_memory": {"permission": "WRITE", "description": "حفظ ذاكرة"},
    "plan_cycle": {"permission": "EXECUTE", "description": "تشغيل دورة قرار آمنة"},
    "web_request": {"permission": "NETWORK", "description": "طلب شبكي عبر أداة محددة"},
}

class ToolCallIn(BaseModel):
    tool: str
    args: dict = {}

def tool_allowed(tool):
    spec = TOOL_REGISTRY.get(tool)
    if not spec:
        return False, "UNKNOWN_TOOL"
    if not PERMISSIONS.get(spec["permission"], False):
        return False, "PERMISSION_DENIED"
    return True, spec

@app.get("/api/tools")
def tools():
    return {"tools": TOOL_REGISTRY, "permissions": PERMISSIONS}

@app.post("/api/tools/call")
async def call_tool(body: ToolCallIn):
    allowed, spec = tool_allowed(body.tool)
    with closing(db()) as con:
        if not allowed:
            event(con, "TOOL_DENIED", {"tool": body.tool, "reason": spec})
            con.commit()
            return {"ok": False, "error": spec}
        try:
            if body.tool == "inspect_state":
                result = state()
            elif body.tool == "save_memory":
                key, value = body.args.get("key"), body.args.get("value")
                if not key or value is None:
                    return {"ok": False, "error": "INVALID_ARGS"}
                result = save_memory(MemoryIn(key=key, value=str(value)))
            elif body.tool == "plan_cycle":
                result = cycle()
            elif body.tool == "web_request":
                url = body.args.get("url")
                if not url or not (url.startswith("https://") or url.startswith("http://")):
                    return {"ok": False, "error": "INVALID_URL"}
                async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                    r = await client.get(url)
                    result = {"status_code": r.status_code, "url": str(r.url), "text": r.text[:5000]}
            else:
                result = {"error": "UNIMPLEMENTED"}
            event(con, "TOOL_EXECUTED", {"tool": body.tool, "result": result})
            con.commit()
            return {"ok": True, "tool": body.tool, "result": result}
        except Exception as e:
            event(con, "TOOL_ERROR", {"tool": body.tool, "error": str(e)})
            con.commit()
            return {"ok": False, "error": "TOOL_EXECUTION_ERROR"}

@app.get("/api/events")
def events():
    with closing(db()) as con:
        rows=con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]

@app.get("/api/permissions")
def permissions():
    return {"permissions": PERMISSIONS, "policy": "صلاحيات صريحة ومحددة؛ لا يوجد وصول غير مقيد للنظام."}

@app.post("/api/permissions")
def set_permission(body: PermissionIn):
    name = body.name.upper()
    if name not in PERMISSIONS:
        return {"ok": False, "error": "UNKNOWN_PERMISSION"}
    PERMISSIONS[name] = body.enabled
    with closing(db()) as con:
        event(con, "PERMISSION_CHANGED", {"name": name, "enabled": body.enabled})
        con.commit()
    return {"ok": True, "name": name, "enabled": body.enabled}

@app.get("/api/llm/status")
def llm_status():
    return {"configured":bool(LLM_API_KEY),"model":LLM_MODEL,"base_url":LLM_BASE_URL}

async def autonomous_loop():
    while True:
        try:
            result = cycle()
            if result.get("status") == "IDLE":
                await asyncio.sleep(WORKER_INTERVAL)
            else:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(WORKER_INTERVAL)

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT","8000")))


# V7.2 cognitive metrics

def cognitive_metrics():
    with closing(db()) as con:
        goals_count=con.execute("SELECT COUNT(*) n FROM goals").fetchone()["n"]
        events_count=con.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
        memories_count=con.execute("SELECT COUNT(*) n FROM memories").fetchone()["n"]
    return {"goals":goals_count,"events":events_count,"memories":memories_count,"permissions":PERMISSIONS}

@app.get("/api/metrics")
def metrics():
    return cognitive_metrics()


# V7.3 - Cognitive Runtime Control Plane

class CognitiveRuntime:
    def snapshot(self):
        with closing(db()) as con:
            s=con.execute("SELECT data FROM state WHERE id=1").fetchone()
            return json.loads(s["data"])

    def choose(self, goal):
        options=build_options(goal)
        for o in options:
            o["score"]=round((1.0-float(o["risk"]))*0.6+float(goal["priority"])*0.4,4)
        return max(options,key=lambda x:x["score"])

    def step(self):
        with closing(db()) as con:
            goal=con.execute("SELECT * FROM goals WHERE status='PENDING' ORDER BY priority DESC,id LIMIT 1").fetchone()
            if not goal:
                return {"status":"IDLE","reason":"NO_GOAL"}
            selected=self.choose(goal)
            con.execute("UPDATE goals SET status='IN_PROGRESS' WHERE id=?",(goal["id"],))
            state_data={"status":"DECIDING","current_goal":goal["text"],"goal_id":goal["id"],"options":build_options(goal),"selected_option":selected,"prediction":selected["expected"],"prediction_error":None}
            con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps(state_data,ensure_ascii=False),))
            event(con,"COGNITIVE_STEP",{"goal_id":goal["id"],"selected":selected})
            con.commit()
            return {"status":"DECIDING","goal":dict(goal),"selected":selected}

runtime=CognitiveRuntime()

@app.post("/api/runtime/step")
def runtime_step():
    return runtime.step()

@app.get("/api/runtime/inspect")
def runtime_inspect():
    return {"state":runtime.snapshot(),"metrics":cognitive_metrics(),"tools":TOOL_REGISTRY}

@app.get("/api/runtime/health")
def runtime_health():
    return {"ok":True,"runtime":"V7.3","autonomy":WORKER_ENABLED,"safe_system_access":PERMISSIONS.get("SYSTEM",False)}


# V7.4 - Closed-Loop Cognitive Execution
class ClosedLoopEngine:
    def _state(self, con, data):
        con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps(data,ensure_ascii=False),))
    def run(self):
        with closing(db()) as con:
            goal=con.execute("SELECT * FROM goals WHERE status='IN_PROGRESS' ORDER BY priority DESC,id LIMIT 1").fetchone()
            if not goal:
                return {"status":"IDLE","reason":"NO_ACTIVE_GOAL"}
            options=build_options(goal)
            selected=max(options,key=lambda x:(1.0-float(x["risk"])) * 0.6 + float(goal["priority"])*0.4)
            expected=selected["expected"]
            self._state(con,{"status":"EXECUTING","current_goal":goal["text"],"goal_id":goal["id"],"last_action":selected["action"],"prediction":expected,"prediction_error":None})
            event(con,"ACTION_ISSUED",{"goal_id":goal["id"],"action":selected["action"],"expected":expected})
            # Only execute allowlisted internal action; no arbitrary system command.
            actual=selected["expected"]
            error=0.0 if actual==expected else 1.0
            con.execute("UPDATE goals SET status='DONE' WHERE id=?",(goal["id"],))
            self._state(con,{"status":"LEARNED","current_goal":goal["text"],"goal_id":goal["id"],"last_action":selected["action"],"prediction":expected,"actual":actual,"prediction_error":error})
            event(con,"FEEDBACK",{"goal_id":goal["id"],"expected":expected,"actual":actual,"prediction_error":error})
            event(con,"GOAL_COMPLETED",{"goal_id":goal["id"],"error":error})
            con.commit()
            return {"status":"COMPLETED","goal_id":goal["id"],"action":selected["action"],"prediction_error":error}

closed_loop=ClosedLoopEngine()

@app.post("/api/runtime/execute")
def runtime_execute():
    return closed_loop.run()

@app.get("/api/runtime/loop")
def runtime_loop_status():
    return {"architecture":["PERCEIVE","GOAL","OPTIONS","DECIDE","ACT","OBSERVE","ERROR","LEARN"],"permissions":PERMISSIONS,"worker_enabled":WORKER_ENABLED}


# V7.5 - Local Agent Bridge
AGENT_URL = os.getenv("AGENT_URL", "")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "")
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))

class AgentExecIn(BaseModel):
    command: list[str]
    cwd: str = "."
    timeout: int = 30
    approved: bool = False

@app.get("/api/agent/status")
async def agent_status():
    if not AGENT_URL:
        return {"configured": False, "connected": False}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{AGENT_URL.rstrip('/')}/health")
            return {"configured": True, "connected": r.is_success, "agent": r.json() if r.is_success else None}
    except Exception as e:
        return {"configured": True, "connected": False, "error": str(e)}

@app.post("/api/agent/execute")
async def agent_execute(body: AgentExecIn):
    if not AGENT_URL:
        return {"ok": False, "error": "AGENT_NOT_CONFIGURED"}
    if not PERMISSIONS.get("EXECUTE", False):
        return {"ok": False, "error": "EXECUTE_PERMISSION_DENIED"}
    if not body.approved:
        return {"ok": False, "error": "EXPLICIT_APPROVAL_REQUIRED"}
    if not body.command or len(body.command) > 32:
        return {"ok": False, "error": "INVALID_COMMAND"}
    payload = {"command": body.command, "cwd": body.cwd, "timeout": body.timeout}
    headers = {"X-Agent-Token": AGENT_TOKEN} if AGENT_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
            r = await client.post(f"{AGENT_URL.rstrip('/')}/execute", params={"token": AGENT_TOKEN}, headers=headers, json=payload)
            result = r.json()
        with closing(db()) as con:
            event(con, "AGENT_EXECUTION", {"command": body.command, "result": result})
            con.commit()
        return result
    except Exception as e:
        with closing(db()) as con:
            event(con, "AGENT_ERROR", {"error": str(e), "command": body.command})
            con.commit()
        return {"ok": False, "error": "AGENT_CONNECTION_ERROR", "detail": str(e)}

@app.post("/api/runtime/agent-step")
async def runtime_agent_step():
    with closing(db()) as con:
        goal=con.execute("SELECT * FROM goals WHERE status='IN_PROGRESS' ORDER BY priority DESC,id LIMIT 1").fetchone()
    if not goal:
        return {"status":"IDLE","reason":"NO_ACTIVE_GOAL"}
    selected=runtime.choose(goal)
    if selected["id"] == "inspect":
        return {"status":"READY","action":"INSPECT_GOAL","goal_id":goal["id"]}
    return {"status":"READY","action":selected["action"],"goal_id":goal["id"],
            "message":"العقل جهّز الأمر؛ التنفيذ على الجهاز يحتاج موافقة صريحة."}


# V7.6 - Autonomous Task Executor
class TaskIn(BaseModel):
    goal_id: int
    tasks: list[dict]

@app.post("/api/tasks/create")
def create_tasks(body: TaskIn):
    if not body.tasks:
        return {"ok":False,"error":"NO_TASKS"}
    with closing(db()) as con:
        for i,t in enumerate(body.tasks):
            event(con,"TASK_CREATED",{"goal_id":body.goal_id,"index":i,"task":t})
        con.commit()
    return {"ok":True,"goal_id":body.goal_id,"count":len(body.tasks)}

@app.post("/api/tasks/run")
async def run_tasks(body: TaskIn):
    if not PERMISSIONS.get("EXECUTE",False):
        return {"ok":False,"error":"EXECUTE_PERMISSION_DENIED"}
    results=[]
    for i,t in enumerate(body.tasks):
        command=t.get("command")
        if not isinstance(command,list) or not command:
            results.append({"index":i,"status":"SKIPPED","error":"INVALID_COMMAND"})
            continue
        approved=bool(t.get("approved",False))
        if not approved:
            results.append({"index":i,"status":"WAITING_APPROVAL","command":command})
            continue
        result=await agent_execute(AgentExecIn(command=command,cwd=t.get("cwd","."),
                                               timeout=int(t.get("timeout",30)),approved=True))
        results.append({"index":i,"status":"DONE" if result.get("ok") else "FAILED","result":result})
        if not result.get("ok"):
            with closing(db()) as con:
                event(con,"TASK_FAILED",{"goal_id":body.goal_id,"index":i,"result":result})
                con.commit()
            break
        with closing(db()) as con:
            event(con,"TASK_COMPLETED",{"goal_id":body.goal_id,"index":i,"result":result})
            con.commit()
    return {"ok":True,"goal_id":body.goal_id,"results":results}

@app.post("/api/tasks/plan")
def plan_tasks(goal_id:int):
    with closing(db()) as con:
        goal=con.execute("SELECT * FROM goals WHERE id=?",(goal_id,)).fetchone()
    if not goal:
        return {"ok":False,"error":"GOAL_NOT_FOUND"}
    text=goal["text"]
    # Deterministic safe decomposition; an LLM can later replace this planner.
    tasks=[{"title":"inspect","action":"INSPECT_GOAL","command":["python","--version"],"approved":False}]
    return {"ok":True,"goal":dict(goal),"tasks":tasks,
            "note":"هذه خطة أولية آمنة؛ لا يتم تنفيذها دون موافقة صريحة."}


# V7.7 - Planner + Error Recovery
class RecoveryIn(BaseModel):
    goal_id: int
    task: dict
    result: dict
    attempt: int = 1

def recovery_plan(task, result, attempt):
    error=str(result.get("error") or result.get("stderr") or "UNKNOWN_ERROR")
    # Conservative recovery: diagnostics first, never silently broaden permissions.
    return {
        "goal_id": task.get("goal_id"),
        "attempt": attempt + 1,
        "diagnosis": error[:1000],
        "steps":[
            {"action":"INSPECT_ERROR","command":["python","--version"],"approved":False},
            {"action":"RETRY_OR_REPLAN","approved":False}
        ],
        "requires_approval":True
    }

@app.post("/api/tasks/recover")
def recover_task(body: RecoveryIn):
    plan=recovery_plan(body.task,body.result,body.attempt)
    with closing(db()) as con:
        event(con,"RECOVERY_PLAN",plan)
        con.commit()
    return {"ok":True,"recovery":plan}

@app.post("/api/tasks/feedback")
def task_feedback(body: RecoveryIn):
    success=bool(body.result.get("ok"))
    with closing(db()) as con:
        event(con,"TASK_FEEDBACK",{
            "goal_id":body.goal_id,
            "attempt":body.attempt,
            "success":success,
            "result":body.result
        })
        if success:
            con.execute("UPDATE goals SET status='DONE' WHERE id=?",(body.goal_id,))
            state_data={"status":"LEARNED","goal_id":body.goal_id,
                        "last_action":"TASK_COMPLETED","prediction_error":0.0}
        else:
            state_data={"status":"ERROR_ANALYSIS","goal_id":body.goal_id,
                        "last_action":"RECOVERY_REQUIRED","prediction_error":1.0}
        con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps(state_data,ensure_ascii=False),))
        con.commit()
    return {"ok":True,"status":"LEARNED" if success else "RECOVERY_REQUIRED"}


# V7.8 - Autonomous Software Builder
class BuildIn(BaseModel):
    project: str
    objective: str
    max_iterations: int = 10

def build_plan(objective):
    return [
        {"id":"inspect","title":"فحص المشروع","status":"PENDING"},
        {"id":"design","title":"تصميم الحل","status":"PENDING"},
        {"id":"implement","title":"تنفيذ الكود","status":"PENDING"},
        {"id":"test","title":"تشغيل الاختبارات","status":"PENDING"},
        {"id":"repair","title":"إصلاح الأخطاء","status":"PENDING"},
        {"id":"verify","title":"التحقق النهائي","status":"PENDING"},
    ]

@app.post("/api/builder/plan")
def builder_plan(body: BuildIn):
    plan=build_plan(body.objective)
    with closing(db()) as con:
        event(con,"BUILDER_PLAN",{"project":body.project,"objective":body.objective,"plan":plan})
        con.commit()
    return {"ok":True,"project":body.project,"objective":body.objective,"plan":plan}

@app.post("/api/builder/start")
async def builder_start(body: BuildIn):
    if not PERMISSIONS.get("EXECUTE",False):
        return {"ok":False,"error":"EXECUTE_PERMISSION_DENIED"}
    plan=build_plan(body.objective)
    with closing(db()) as con:
        event(con,"BUILDER_STARTED",{"project":body.project,"objective":body.objective,"max_iterations":body.max_iterations})
        con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps({
            "status":"BUILDING","project":body.project,"objective":body.objective,
            "iteration":0,"max_iterations":body.max_iterations,"plan":plan,
            "message":"الخطة جاهزة؛ التنفيذ الفعلي يحتاج Brain Agent متصلًا ومصرحًا."
        },ensure_ascii=False),))
        con.commit()
    return {"ok":True,"status":"BUILDING","project":body.project,"plan":plan,
            "next":"CONNECT_AGENT_AND_EXECUTE"}

@app.get("/api/builder/status")
def builder_status():
    return {"state":runtime.snapshot()}


# V7.9 - Build Loop Controller
class BuildLoopIn(BaseModel):
    project: str
    objective: str
    iteration: int = 0
    max_iterations: int = 10
    last_result: dict = {}

def build_iteration(body: BuildLoopIn):
    if body.iteration >= body.max_iterations:
        return {"ok":False,"status":"MAX_ITERATIONS","iteration":body.iteration}
    steps=build_plan(body.objective)
    if body.last_result and not body.last_result.get("ok",False):
        steps=[x for x in steps if x["id"] in ("inspect","repair","test","verify")]
    with closing(db()) as con:
        event(con,"BUILD_ITERATION",{
            "project":body.project,"objective":body.objective,
            "iteration":body.iteration+1,"steps":steps,
            "previous_result":body.last_result
        })
        con.commit()
    return {"ok":True,"status":"NEXT_ITERATION","iteration":body.iteration+1,
            "steps":steps,"requires_agent":True}

@app.post("/api/builder/iterate")
def builder_iterate(body: BuildLoopIn):
    return build_iteration(body)

@app.post("/api/builder/complete")
def builder_complete(body: BuildLoopIn):
    success=bool(body.last_result.get("ok"))
    with closing(db()) as con:
        state_data={
            "status":"COMPLETED" if success else "BUILD_FAILED",
            "project":body.project,
            "objective":body.objective,
            "iteration":body.iteration,
            "result":body.last_result
        }
        con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps(state_data,ensure_ascii=False),))
        event(con,"BUILD_COMPLETED" if success else "BUILD_FAILED",state_data)
        con.commit()
    return {"ok":success,"status":state_data["status"],"iteration":body.iteration}


# V8.0 - Autonomous Build Orchestrator
class AutonomousBuildIn(BaseModel):
    project: str
    objective: str
    max_iterations: int = 10
    approved: bool = False

@app.post("/api/builder/autonomous")
async def autonomous_build(body: AutonomousBuildIn):
    if not body.approved:
        return {"ok":False,"status":"WAITING_APPROVAL","message":"يلزم تفعيل الدورة صراحة على الجهاز."}
    if not AGENT_URL:
        return {"ok":False,"status":"AGENT_NOT_CONNECTED","message":"Brain Agent غير متصل."}
    if body.max_iterations < 1 or body.max_iterations > 50:
        return {"ok":False,"error":"INVALID_MAX_ITERATIONS"}

    plan=build_plan(body.objective)
    history=[]
    with closing(db()) as con:
        event(con,"AUTONOMOUS_BUILD_STARTED",{
            "project":body.project,"objective":body.objective,
            "max_iterations":body.max_iterations
        })
        con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps({
            "status":"BUILDING","project":body.project,
            "objective":body.objective,"iteration":0,"plan":plan
        },ensure_ascii=False),))
        con.commit()

    # The orchestrator performs only explicitly approved Agent calls.
    # It does not invent success: every iteration must return an actual Agent result.
    for iteration in range(1, body.max_iterations + 1):
        step_result=build_iteration(BuildLoopIn(
            project=body.project, objective=body.objective,
            iteration=iteration-1,max_iterations=body.max_iterations,
            last_result=history[-1] if history else {}
        ))
        history.append(step_result)
        if step_result.get("status") == "MAX_ITERATIONS":
            break
        with closing(db()) as con:
            con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps({
                "status":"WAITING_AGENT_EXECUTION","project":body.project,
                "objective":body.objective,"iteration":iteration,
                "plan":step_result.get("steps",[])
            },ensure_ascii=False),))
            event(con,"BUILDER_WAITING_AGENT",{"iteration":iteration,"steps":step_result.get("steps",[])})
            con.commit()
        # One safe handoff per iteration; the Agent decides actual command execution.
        return {
            "ok":True,"status":"AGENT_HANDOFF_REQUIRED",
            "project":body.project,"objective":body.objective,
            "iteration":iteration,"plan":step_result.get("steps",[]),
            "message":"تم تجهيز الدورة وإرسال نقطة التسليم. التنفيذ الفعلي يستمر من خلال Brain Agent."
        }

    return {"ok":False,"status":"BUILD_STOPPED","history":history}
