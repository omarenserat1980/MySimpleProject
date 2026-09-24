import os
import threading
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .brain.memory import MemoryStore
from .brain.core import BrainCore
from .brain.agent import Agent
from .brain.builder import SoftwareBuilder
from .brain.orchestrator import CognitiveOrchestrator
from .brain.capabilities import CAPABILITIES, PLUGINS, TOOLS
from .brain.self_improvement import SelfImprovementEngine
from .brain.cognitive_loop import CognitiveLoop
from .brain.ai_gateway import AIGateway
from .brain.openai_provider import OpenAIProvider
from .brain.plugin_manager import PluginManager
from brain_v7.braincore_v2.code_workspace_tool import CodeWorkspaceTool, CodeChange
from brain_v7.braincore_v2.code_tool_engineering_team import CodeToolEngineeringTeam
from brain_v7.braincore_v2.code_tool_api import CodeTool
from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy
from .brain.code_agent import BrainCodeAgent

ROOT=os.path.dirname(__file__)
store=MemoryStore(os.getenv("BRAIN_DB",os.path.join(ROOT,"brain_v12.db"))); store.init()
brain=BrainCore(store); agent=Agent(); builder=SoftwareBuilder()
orchestrator=CognitiveOrchestrator(store,brain,builder); self_improver=SelfImprovementEngine()
cognitive=CognitiveLoop(store); ai=AIGateway(); openai_provider=OpenAIProvider(); plugins=PluginManager()
code_root=os.getenv("BRAIN_CODE_ROOT", os.path.abspath(os.path.join(ROOT, "..")))
code_workspace=CodeWorkspaceTool(root=code_root, allowed_prefixes=("brain_v7/","brain_v12/"))
code_team=CodeToolEngineeringTeam(EmployeeHierarchy(), code_workspace)
code_tool=CodeTool(code_workspace, code_team)
brain_code_agent=BrainCodeAgent(openai_provider, code_tool, code_workspace)
cognitive.code_tool=code_tool
for p in PLUGINS:
    plugin_id=p.get("id") if isinstance(p,dict) else str(p)
    plugin_name=p.get("name",plugin_id) if isinstance(p,dict) else str(p)
    plugin_permission=p.get("permission") if isinstance(p,dict) else None
    registered=plugins.register(plugin_id,plugin_name,"1.0",[],[plugin_permission] if plugin_permission else [])
    if isinstance(p,dict) and p.get("enabled"):
        plugins.enable(plugin_id)

APP_VERSION=os.getenv("BRAIN_V12_VERSION","12.4")
app=FastAPI(title="Electronic Brain V12",version=APP_VERSION)

@app.middleware("http")
async def no_cache(request, call_next):
    response=await call_next(request)
    response.headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"]="no-cache"
    return response

class BrainCodePlanIn(BaseModel):
    objective:str
    files:list[str]=[]

class BrainCodeApplyIn(BaseModel):
    objective:str
    files:list[str]=[]
    approved:bool=False
    commit_message:str="brain: validated self-improvement"
    persist_to_github:bool=True

class Chat(BaseModel): message:str
class Goal(BaseModel): text:str; priority:float=0.5
class Memory(BaseModel): key:str; value:str
class Observe(BaseModel): actual:str
class Learn(BaseModel): lesson:str
class Exec(BaseModel): command:list[str]; cwd:str="."; timeout:int=30; approved:bool=False
class Improve(BaseModel): objective:str; files:list[str]=[]
class Permission(BaseModel): capability:str
class CodeChangeIn(BaseModel): path:str; content:str; reason:str=""
class CodeChanges(BaseModel):
    changes:list[CodeChangeIn]
    reason:str=""
    commit_message:str="brain: controlled code change"
    approved:bool=False
    persist_to_github:bool=True
class CodePaths(BaseModel): paths:list[str]=[]

@app.post("/api/media/upload")
async def media_upload(file:UploadFile=File(...)):
    media_dir=os.path.join(ROOT,"web","media"); os.makedirs(media_dir,exist_ok=True)
    safe=os.path.basename(file.filename or "upload.bin"); target=os.path.join(media_dir,safe); data=await file.read()
    with open(target,"wb") as f: f.write(data)
    store.event("MEDIA_RECEIVED",{"filename":safe,"content_type":file.content_type,"size":len(data)})
    return {"ok":True,"filename":safe,"url":f"/media/{safe}","content_type":file.content_type,"size":len(data)}

@app.get("/api/capabilities")
def capabilities(): return {"capabilities":CAPABILITIES,"plugins":PLUGINS,"tools":TOOLS}
@app.get("/health")
def health(): return {"ok":True,"brain":"V12","version":APP_VERSION,"systems":["cognition","memory","decision","tasks","permissions","plugins","ai_gateway","chatgpt","brain_code_agent","code_tool"]}
@app.get("/api/system/status")
def system_status():
    return {"ok":True,"status":"ONLINE","brain":"V12","version":APP_VERSION}

@app.get("/api/state")
def state(): return brain.snapshot()
@app.get("/api/messages")
def messages(): return store.messages()

def chatgpt_reply(message,cognitive_context=None):
    recent=store.messages()[-12:]
    context="\n".join(f"{m.get('role','')}: {m.get('content','')}" for m in recent)
    if cognitive_context:
        context += "\n\n[HIGH_LEVEL_COGNITIVE_STATE]\n" + str(cognitive_context)
    return openai_provider.respond(message,context)

@app.post("/api/chat")
def chat(body:Chat):
    message=body.message.strip()
    if not message: return {"ok":False,"error":"EMPTY_MESSAGE"}
    store.add_message("user",message); store.event("PERCEPTION",{"message":message})
    goal=store.active_goal()
    if not goal: store.add_goal(message,.8); goal=store.active_goal()
    loop=cognitive.run(goal["text"])
    selected=loop["decision"].get("selected",{})

    ai_result=chatgpt_reply(message,{"run_id":loop.get("run_id"),"decision":selected.get("action"),"execution":loop.get("execution"),"verification":loop.get("verification"),"learning":loop.get("learning")})
    if ai_result.get("ok"):
        reply=ai_result["reply"]
        source="chatgpt"
    else:
        reply=("تم تشغيل الحلقة المعرفية.\n"
               f"الهدف: {goal['text']}\n"
               f"الحالة: {loop['decision']['status']}\n"
               f"القرار: {selected.get('action','انتظار/موافقة')}\n"
               f"السبب: {loop['decision'].get('reason','—')}")
        source="cognitive_fallback"
    store.add_message("assistant",reply)
    store.event("AI_RESPONSE",{"provider":source})
    decision = loop.get("decision", {}) if isinstance(loop, dict) else {}
    selected = decision.get("selected", {}) if isinstance(decision, dict) else {}
    cognitive_summary = {
        "understood": message,
        "goal": goal.get("text") if isinstance(goal, dict) else message,
        "analysis_status": decision.get("status", "ANALYZING"),
        "decision": selected.get("action", "تحديد الخطوة التالية"),
        "decision_reason": decision.get("reason", "تمت مراجعة الهدف والسياق المتاح."),
        "execution": "لم يُنفذ إجراء خارجي" if source == "chatgpt" else "تم تشغيل الحلقة المعرفية",
        "verification": "الرد الذكي لا يعني أن إجراءً خارجياً تم تنفيذه؛ التنفيذ يحتاج نتيجة موثقة."
    }
    cognitive_summary["run_id"]=loop.get("run_id")
    cognitive_summary["execution_result"]=loop.get("execution",{})\n    cognitive_summary["verification_result"]=loop.get("verification",{})\n    return {"ok":True,"reply":reply,"provider":source,"cognitive":loop,"cognitive_summary":cognitive_summary,"run_id":loop.get("run_id"),"ai":ai_result if not ai_result.get("ok") else {"ok":True,"provider":"openai","model":openai_provider.model}}

@app.get("/api/memory")
def memory(): return store.memories()
@app.post("/api/memory")
def save_memory(body:Memory): store.save_memory(body.key,body.value); return {"ok":True}
@app.get("/api/goals")
def goals(): return store.goals()
@app.post("/api/goals")
def add_goal(body:Goal): return {"id":store.add_goal(body.text,body.priority)}
@app.post("/api/cycle")
def cycle(): return brain.think()
@app.post("/api/cognitive/run")
def cognitive_run(goal:str): return cognitive.run(goal)
@app.get("/api/decision/history")
def decision_history(): return cognitive.decisions.history[-100:]
@app.get("/api/world")
def world(): return cognitive.world.snapshot()
@app.post("/api/world/fact")
def world_fact(key:str,value:str,source:str="user",confidence:float=.8): return cognitive.world.set_fact(key,value,source,confidence)
@app.post("/api/run")
def run_cycle(goal:str="brain_v12"): return cognitive.run(goal)

@app.post("/api/cognitive/start")
def cognitive_start(goal:str="brain_v12"):
    run_id=str(uuid4())
    def worker():
        try:
            cognitive.run(goal,run_id=run_id)
        except Exception as exc:
            state=store.state(); state.update({"status":"ERROR","cognitive_stage":"ERROR","cognitive_trace":{"run_id":run_id,"error":str(exc)}}); store.set_state(state)
            store.event("COGNITIVE_RUN_FAILED",{"run_id":run_id,"error":str(exc)})
    threading.Thread(target=worker,daemon=True).start()
    return {"ok":True,"run_id":run_id,"status":"STARTED"}
@app.post("/api/observe")
def observe(body:Observe): return orchestrator.observe_and_learn(body.actual)
@app.post("/api/learn")
def learn(body:Learn): return brain.learn(body.lesson)
@app.get("/api/events")
def events(): return store.events()

@app.post("/api/code/brain-plan")
def code_brain_plan(body:BrainCodePlanIn):
    try:
        plan=brain_code_agent.plan(body.objective,body.files)
        return brain_code_agent.public_plan(plan)
    except Exception as exc:
        return {"status":"PLAN_FAILED","error":str(exc)}

@app.post("/api/code/brain-apply")
def code_brain_apply(body:BrainCodeApplyIn):
    try:
        plan=brain_code_agent.plan(body.objective,body.files)
        public=brain_code_agent.public_plan(plan)
        if plan.get("status") != "PLAN_READY":
            return public
        result=brain_code_agent.execute_plan(
            plan,
            approved=body.approved,
            commit_message=body.commit_message,
            persist_to_github=body.persist_to_github,
        )
        store.event("BRAIN_CODE_EVOLUTION", {
            "status":result.get("status"),
            "objective":body.objective,
            "files":body.files,
        })
        return {"plan":public,"execution":result}
    except Exception as exc:
        return {"status":"EXECUTION_FAILED","error":str(exc)}

@app.get("/api/code/status")
def code_status(): return code_team.snapshot()

@app.post("/api/code/inspect")
def code_inspect(path:str): return code_tool.inspect(path)

@app.post("/api/code/preview")
def code_preview(body:CodeChanges):
    changes=[CodeChange(x.path,x.content,x.reason) for x in body.changes]
    return code_tool.preview(changes)

@app.post("/api/code/checkpoint")
def code_checkpoint(body:CodePaths): return code_tool.save_checkpoint(body.paths)

@app.post("/api/code/verify")
def code_verify(body:CodePaths): return code_tool.verify(body.paths)

@app.post("/api/code/apply")
def code_apply(body:CodeChanges):
    if not body.approved:
        return {"ok":False,"status":"EXPLICIT_APPROVAL_REQUIRED","message":"الموافقة الصريحة مطلوبة قبل الكتابة أو الحفظ البعيد."}
    changes=[CodeChange(x.path,x.content,x.reason) for x in body.changes]
    result=code_tool.save_and_execute(
        changes,
        reason=body.reason or "controlled code change from Brain interface",
        commit_message=body.commit_message,
        persist_to_github=body.persist_to_github,
    )
    store.event("CODE_TOOL_EXECUTION", {"status":result.get("status"),"remote_status":result.get("remote_status"),"paths":[x.path for x in changes]})
    return result

@app.get("/api/code/audit")
def code_audit(): return code_workspace.snapshot()

@app.get("/api/tools")
def tools_catalog(): return {"ok":True,"tools":cognitive.tool_catalog()}

@app.post("/api/tools/execute")
def tools_execute(tool_id:str,params:dict|None=None,approved:bool=False): return cognitive.execute_tool(tool_id,params or {},approved)

@app.get("/api/cognitive/live")
def cognitive_live():
    s=store.state(); ev=store.events(40); trace=s.get("cognitive_trace",{}) if isinstance(s,dict) else {}
    return {"ok":True,"state":s,"run_id":trace.get("run_id"),"result":s.get("cognitive_result"),"stage":s.get("cognitive_stage","READY"),"stage_index":s.get("cognitive_stage_index",-1),"total":s.get("cognitive_total",len(cognitive.STAGES)),"trace":trace,"events":ev,"tasks":cognitive.tasks.snapshot()}

@app.get("/api/tasks")
def tasks(): return cognitive.tasks.snapshot()
@app.post("/api/tasks")
def task(title:str,parent_id:str|None=None,depends_on:list[str]=[]): return cognitive.tasks.create(title,parent_id,depends_on)

@app.get("/api/permissions")
def permissions(): return {"grants":sorted(cognitive.permissions.grants)}
@app.post("/api/permissions/grant")
def grant(body:Permission): return {"grants":cognitive.permissions.grant(body.capability)}
@app.post("/api/permissions/revoke")
def revoke(body:Permission): return {"grants":cognitive.permissions.revoke(body.capability)}
@app.post("/api/permissions/check")
def permission_check(capabilities:list[str],approved:bool=False): return cognitive.permissions.check(capabilities,approved)

@app.get("/api/ai/status")
def ai_status(): return {"providers":ai.status(),"openai":openai_provider.status()}
@app.post("/api/ai/invoke")
def ai_invoke(provider:str,modality:str,payload:dict): return ai.invoke(provider,modality,payload)
@app.post("/api/ai/chat")
def ai_chat(body:Chat):
    result=chatgpt_reply(body.message.strip())
    if result.get("ok"): store.add_message("assistant",result["reply"])
    return result

@app.get("/api/plugins")
def plugin_status(): return plugins.status()
@app.post("/api/plugins/{plugin_id}/enable")
def plugin_enable(plugin_id:str): return plugins.enable(plugin_id)
@app.post("/api/plugins/{plugin_id}/disable")
def plugin_disable(plugin_id:str): return plugins.disable(plugin_id)

@app.get("/api/agent/status")
def agent_status(): return agent.status()
@app.get("/api/self-improvement/status")
def self_improvement_status(): return self_improver.status()
@app.post("/api/self-improvement/propose")
def self_improvement_propose(body:Improve):
    result=self_improver.propose(body.objective,body.files); store.event("SELF_IMPROVEMENT_PROPOSAL",result); return result
@app.post("/api/self-improvement/record-approval")
def self_improvement_record_approval(body:Improve):
    store.event("SELF_IMPROVEMENT_APPROVAL",{"objective":body.objective,"files":body.files})
    return {"ok":True,"approved":True,"note":"Approval recorded; repository writes remain explicitly gated."}

@app.post("/api/agent/execute")
def agent_execute(body:Exec):
    if not body.approved: return {"ok":False,"error":"EXPLICIT_APPROVAL_REQUIRED"}
    current=brain.snapshot(); current["status"]="ACTING"; store.set_state(current)
    store.event("ACTION_STARTED",{"command":body.command})
    result=agent.execute(body.command,body.cwd,body.timeout)
    current=brain.snapshot(); current.update({"status":"OBSERVING","last_action":body.command,"last_result":result}); store.set_state(current)
    store.event("AGENT_EXECUTION",{"command":body.command,"result":result}); return result

@app.post("/api/builder/plan")
def builder_plan(project:str,objective:str):
    plan=builder.plan(project,objective); store.event("BUILDER_PLAN",plan); return plan

app.mount("/media",StaticFiles(directory=os.path.join(ROOT,"web","media"),check_dir=False),name="media")
app.mount("/",StaticFiles(directory=os.path.join(ROOT,"web"),html=True),name="ui")
if __name__=="__main__":
    import uvicorn; uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT","8012")))
