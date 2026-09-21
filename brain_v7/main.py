import os
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = os.getenv("BRAIN_DB", "brain_v7.db")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
WORKER_ENABLED = os.getenv("WORKER_ENABLED", "false").lower() == "true"
WORKER_INTERVAL = int(os.getenv("WORKER_INTERVAL", "60"))

app = FastAPI(title="Electronic Brain V7", version="7.0")
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

@app.post("/api/cycle")
def cycle():
    with closing(db()) as con:
        goal=con.execute("SELECT * FROM goals WHERE status='PENDING' ORDER BY priority DESC,id LIMIT 1").fetchone()
        if not goal:
            return {"status":"IDLE","message":"لا يوجد هدف معلق."}
        con.execute("UPDATE goals SET status='IN_PROGRESS' WHERE id=?",(goal["id"],))
        import json
        s={"status":"EXECUTING","current_goal":goal["text"],"last_action":"PLAN_AND_OBSERVE"}
        con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps(s,ensure_ascii=False),))
        event(con,"CYCLE",{"goal_id":goal["id"],"action":"PLAN_AND_OBSERVE"})
        con.commit()
        return {"status":"EXECUTING","goal":dict(goal),"action":"PLAN_AND_OBSERVE"}

@app.get("/api/events")
def events():
    with closing(db()) as con:
        rows=con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]

@app.get("/api/llm/status")
def llm_status():
    return {"configured":bool(LLM_API_KEY),"model":LLM_MODEL,"base_url":LLM_BASE_URL}

def worker():
    while WORKER_ENABLED:
        try:
            cycle()
        except Exception:
            pass
        time.sleep(WORKER_INTERVAL)

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT","8000")))
