"""FastAPI bridge for the cognitive orchestrator and chat layer."""
from typing import Any
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .cognitive_orchestrator import CognitiveOrchestrator
from .agent_executor import execute_action
from .chat_engine import BrainChat

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])
orchestrator = CognitiveOrchestrator(action_executor=execute_action)
chat = BrainChat(orchestrator)


class CycleRequest(BaseModel):
    objective: str = "inspect and improve current state"
    gaps: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=lambda: ["inspect"])
    expected: Any = None
    horizon: int = 5


class LoopRequest(BaseModel):
    objective: str = "run bounded autonomous loop"
    gaps: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=lambda: ["inspect"])
    expected: Any = None
    action_expectations: dict[str, Any] = Field(default_factory=dict)
    horizon: int = 5


class ImprovementRequest(BaseModel):
    id: str
    description: str


class ChatRequest(BaseModel):
    message: str


@router.get("/status")
def autonomous_status():
    return orchestrator.status()


@router.post("/cycle")
def autonomous_cycle(req: CycleRequest):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    return orchestrator.step(payload)


@router.post("/loop")
def autonomous_loop(req: LoopRequest):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    return orchestrator.run_loop(payload)


@router.post("/improvement")
def propose_improvement(req: ImprovementRequest):
    p = orchestrator.propose_improvement(req.id, req.description)
    return {"id": p.id, "description": p.description, "status": p.status}


@router.get("/chat", response_class=HTMLResponse)
def chat_page():
    return HTMLResponse("""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>العقل الإلكتروني</title>
<style>
body{font-family:Arial,sans-serif;max-width:760px;margin:30px auto;padding:15px;background:#f5f5f5}
h1{text-align:center}.box{background:white;border-radius:12px;padding:15px;min-height:360px}
#log{white-space:pre-wrap}.row{margin:10px 0}.user{font-weight:bold}.brain{font-weight:bold}
form{display:flex;gap:8px;margin-top:12px}input{flex:1;padding:12px;border:1px solid #ccc;border-radius:8px}
button{padding:12px 18px;border:0;border-radius:8px;cursor:pointer}
</style>
</head>
<body>
<h1>🧠 العقل الإلكتروني</h1>
<div class="box"><div id="log"></div></div>
<form id="f">
<input id="m" placeholder="احكي معي..." autocomplete="off">
<button type="submit">إرسال</button>
</form>
<script>
const log=document.getElementById("log");
const form=document.getElementById("f");
const input=document.getElementById("m");
function add(who,text){
  const d=document.createElement("div");
  d.className="row";
  d.innerHTML="<span class='"+(who==="أنت"?"user":"brain")+"'>"+who+":</span> "+text;
  log.appendChild(d);
}
form.addEventListener("submit",async e=>{
  e.preventDefault();
  const message=input.value.trim();
  if(!message)return;
  add("أنت",message); input.value="";
  try{
    const r=await fetch("/api/autonomous/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message})});
    const data=await r.json();
    add("العقل",data.reply||JSON.stringify(data));
  }catch(err){add("العقل","حدث خطأ في الاتصال: "+err);}
});
</script>
</body>
</html>
""")


@router.post("/chat")
def chat_message(req: ChatRequest):
    return chat.respond(req.message)
