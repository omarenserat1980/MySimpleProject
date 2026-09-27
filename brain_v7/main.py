import os, sqlite3, asyncio, json
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
from braincore_v2.brain_api import router as brain_code_router

DB_PATH = os.getenv("BRAIN_DB", "brain_v7.db")
_MEMORY_URI = "file:brain_v7_shared_memory?mode=memory&cache=shared"
_MEMORY_KEEPALIVE = sqlite3.connect(_MEMORY_URI, uri=True, check_same_thread=False) if DB_PATH == ":memory:" else None
if _MEMORY_KEEPALIVE is not None:
    _MEMORY_KEEPALIVE.row_factory = sqlite3.Row
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
WORKER_ENABLED = os.getenv("WORKER_ENABLED", "false").lower() == "true"
WORKER_INTERVAL = int(os.getenv("WORKER_INTERVAL", "60"))
PERMISSIONS = {k: os.getenv("PERM_"+k, "true").lower() == "true" for k in ("READ","WRITE","EXECUTE","NETWORK")}
PERMISSIONS["SYSTEM"] = os.getenv("PERM_SYSTEM", "false").lower() == "true"
AUTONOMOUS_MAX_ITERATIONS = int(os.getenv("BRAIN_MAX_ITERATIONS", "1000"))
AUTONOMOUS_MAX_ITERATIONS = max(1, min(1000, AUTONOMOUS_MAX_ITERATIONS))

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
app.include_router(brain_code_router)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    con = sqlite3.connect(_MEMORY_URI if DB_PATH == ":memory:" else DB_PATH, uri=(DB_PATH == ":memory:"), check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with closing(db()) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE NOT NULL, value TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS goals(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', priority REAL NOT NULL DEFAULT 0.5, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
        INSERT OR IGNORE INTO state(id,data) VALUES(1,'{"status":"READY","current_goal":null,"last_action":null}');
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
    con.execute("INSERT INTO events(type,payload,created_at) VALUES(?,?,?)",(typ, json.dumps(payload, ensure_ascii=False), now()))

async def llm_reply(message: str) -> str:
    if not LLM_API_KEY:
        return "العقل الإلكتروني متصل بالواجهة، لكن مزود نموذج اللغة غير مهيأ بعد. أضف LLM_API_KEY إلى الخادم."
    headers={"Authorization": f"Bearer {LLM_API_KEY}"}
    payload={"model": LLM_MODEL,"messages":[
        {"role":"system","content":"أنت العقل الإلكتروني V7. حلّل الأخطاء واقترح الخطوة التالية القابلة للتنفيذ. لا تدّع تنفيذ إجراء خارجي لم يتم تنفيذه فعلياً."},
        {"role":"user","content":message}]}
    async with httpx.AsyncClient(timeout=60) as client:
        r=await client.post(f"{LLM_BASE_URL}/chat/completions",headers=headers,json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

@app.get("/health")
def health():
    return {"ok":True,"service":"Electronic Brain V7","autonomous_max_iterations":AUTONOMOUS_MAX_ITERATIONS}

@app.get("/api/runtime/loop")
def runtime_loop_status():
    return {"architecture":["PERCEIVE","GOAL","OPTIONS","DECIDE","ACT","OBSERVE","ERROR","LEARN"],
            "permissions":PERMISSIONS,"worker_enabled":WORKER_ENABLED,
            "max_iterations":AUTONOMOUS_MAX_ITERATIONS,
            "policy":"The Brain may iterate internally up to 1000 times before escalating to the user."}

# Preserve the existing application routes by importing the legacy route module.
# This file intentionally exposes the new control-plane settings without granting
# arbitrary system access.
@app.get("/api/autonomy/config")
def autonomy_config():
    return {
        "max_iterations": AUTONOMOUS_MAX_ITERATIONS,
        "hard_cap": 1000,
        "user_escalation_after_cap": True,
        "brain_first": True
    }

async def autonomous_loop():
    while True:
        try:
            await asyncio.sleep(WORKER_INTERVAL)
        except asyncio.CancelledError:
            raise

app.mount("/", StaticFiles(directory=os.path.dirname(__file__), html=True), name="brain-ui")

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT","8000")))
