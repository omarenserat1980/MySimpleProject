import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .brain.memory import MemoryStore
from .brain.core import BrainCore
from .brain.agent import Agent
from .brain.builder import SoftwareBuilder

ROOT=os.path.dirname(__file__)
store=MemoryStore(os.getenv("BRAIN_DB",os.path.join(ROOT,"brain_v12.db")))
store.init()
brain=BrainCore(store)
agent=Agent()
builder=SoftwareBuilder()
app=FastAPI(title="Electronic Brain V12",version="12.0")

class Chat(BaseModel):
    message:str
class Goal(BaseModel):
    text:str
    priority:float=0.5
class Memory(BaseModel):
    key:str
    value:str
class Observe(BaseModel):
    actual:str
class Learn(BaseModel):
    lesson:str
class Exec(BaseModel):
    command:list[str]
    cwd:str="."
    timeout:int=30
    approved:bool=False

@app.get("/health")
def health():
    return {"ok":True,"brain":"V12"}

@app.get("/api/state")
def state():
    return brain.snapshot()

@app.get("/api/messages")
def messages():
    return store.messages()

@app.post("/api/chat")
def chat(body:Chat):
    message=body.message.strip()
    if not message:
        return {"ok":False,"error":"EMPTY_MESSAGE"}

    store.add_message("user",message)
    store.event("PERCEPTION",{"message":message})

    goal=store.active_goal()
    created_goal=False
    if not goal:
        goal_id=store.add_goal(message,0.8)
        created_goal=True
        goal=store.active_goal()

    decision=brain.think()
    selected=decision.get("selected")
    if decision.get("status")=="DECIDING" and selected:
        reply=(
            f"فهمت الطلب وربطته بهدف نشط.\n"
            f"الهدف: {decision.get('current_goal')}\n"
            f"القرار الحالي: {selected.get('action')}\n"
            f"الخطوة المتوقعة: {selected.get('expected')}\n"
            f"الحالة: DECIDING"
        )
    else:
        reply=f"تم تسجيل الطلب، لكن لا يوجد قرار قابل للتنفيذ الآن: {decision.get('reason','UNKNOWN')}"
    store.add_message("assistant",reply)
    return {
        "ok":True,
        "reply":reply,
        "created_goal":created_goal,
        "goal_id":goal["id"] if goal else None,
        "decision":decision
    }

@app.get("/api/memory")
def memory():
    return store.memories()

@app.post("/api/memory")
def save_memory(body:Memory):
    store.save_memory(body.key,body.value)
    return {"ok":True}

@app.get("/api/goals")
def goals():
    return store.goals()

@app.post("/api/goals")
def add_goal(body:Goal):
    return {"id":store.add_goal(body.text,body.priority)}

@app.post("/api/cycle")
def cycle():
    return brain.think()

@app.post("/api/observe")
def observe(body:Observe):
    return brain.observe(body.actual)

@app.post("/api/learn")
def learn(body:Learn):
    return brain.learn(body.lesson)

@app.get("/api/events")
def events():
    return store.events()

@app.get("/api/agent/status")
def agent_status():
    return agent.status()

@app.post("/api/agent/execute")
def agent_execute(body:Exec):
    if not body.approved:
        return {"ok":False,"error":"EXPLICIT_APPROVAL_REQUIRED"}
    result=agent.execute(body.command,body.cwd,body.timeout)
    store.event("AGENT_EXECUTION",{"command":body.command,"result":result})
    return result

@app.post("/api/builder/plan")
def builder_plan(project:str,objective:str):
    plan=builder.plan(project,objective)
    store.event("BUILDER_PLAN",plan)
    return plan

app.mount("/",StaticFiles(directory=os.path.join(ROOT,"web"),html=True),name="ui")

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT","8012")))
