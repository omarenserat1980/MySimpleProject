from .decision_engine import DecisionEngine
from .event_bus import EventBus
from .permissions import PermissionGate
from .task_engine import TaskEngine
from .world_model import WorldModel
from uuid import uuid4

class CognitiveLoop:
    """Traceable V12 cognitive pipeline. Exposes high-level state, never private chain-of-thought."""
    STAGES=["PERCEIVE","UNDERSTAND","MEMORY","ANALYZE","PLAN","DECIDE","EXECUTE","VERIFY","LEARN"]
    TOOL_CATALOG=[
        {"id":"memory.read","name":"قراءة الذاكرة","risk":"low","permission":None},
        {"id":"state.read","name":"قراءة حالة العقل","risk":"low","permission":None},
        {"id":"tasks.create","name":"إنشاء مهمة","risk":"low","permission":None},
        {"id":"tasks.complete","name":"إكمال مهمة","risk":"low","permission":None},
        {"id":"code.inspect","name":"فحص الكود","risk":"low","permission":"developer"},
        {"id":"code.verify","name":"التحقق من الكود","risk":"low","permission":"developer"},
        {"id":"device.enqueue","name":"إرسال مهمة إلى Termux","risk":"medium","permission":"device_agent"},
        {"id":"code.apply","name":"تعديل الكود","risk":"high","permission":"developer_approval"},
        {"id":"agent.execute","name":"تنفيذ معزول","risk":"high","permission":"agent_approval"},
    ]

    def __init__(self,store):
        self.store=store
        self.events=EventBus(store)
        self.decisions=DecisionEngine()
        self.permissions=PermissionGate()
        self.tasks=TaskEngine()
        self.world=WorldModel()
        self.code_tool=None

    def _state(self,stage,status="RUNNING",**extra):
        current=self.store.state()
        current.update({
            "status":status,
            "cognitive_stage":stage,
            "cognitive_stage_index":self.STAGES.index(stage) if stage in self.STAGES else -1,
            "cognitive_total":len(self.STAGES),
            "cognitive_trace":extra,
        })
        self.store.set_state(current)
        return current

    def tool_catalog(self):
        return self.TOOL_CATALOG

    def execute_tool(self,tool_id,params=None,approved=False,_retry=False):
        params=params or {}
        item=next((x for x in self.TOOL_CATALOG if x["id"]==tool_id),None)
        self.events.publish("TOOL_SELECTED",{"tool":tool_id,"approved":approved})
        if not item:
            result={"ok":False,"status":"UNKNOWN_TOOL","tool":tool_id}
        elif item["permission"] and (item["permission"] not in self.permissions.grants or (item["risk"]=="high" and not approved)):
            result={"ok":False,"status":"WAITING_PERMISSION","tool":tool_id,"permission":item["permission"]}
        elif tool_id=="memory.read":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.store.memories()[:int(params.get("limit",12))]}
        elif tool_id=="state.read":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.store.state()}
        elif tool_id=="tasks.create":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.tasks.create(str(params.get("title","مهمة جديدة")))}
        elif tool_id=="tasks.complete":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.tasks.update(str(params.get("task_id")),"COMPLETED")}
        elif tool_id=="code.inspect":
            if not self.code_tool:
                result={"ok":False,"status":"UNAVAILABLE","tool":tool_id}
            else:
                result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.code_tool.inspect(str(params.get("path","brain_v12/app.py")))}
        elif tool_id=="code.verify":
            if not self.code_tool:
                result={"ok":False,"status":"UNAVAILABLE","tool":tool_id}
            else:
                result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.code_tool.verify(params.get("paths",[]))}
        elif tool_id=="device.enqueue":
            bridge = getattr(self, "device_bridge", None)
            if not bridge:
                result={"ok":False,"status":"UNAVAILABLE","tool":tool_id}
            else:
                result=bridge.enqueue(str(params.get("task","status")), params.get("params",{}))
        else:
            result={"ok":False,"status":"DELEGATED","tool":tool_id,"reason":"الأداة تحتاج المسار المخصص لها."}
        self.events.publish("TOOL_RESULT",result)
        if not result.get("ok") and not _retry and item and item.get("risk")=="low":
            self.events.publish("TOOL_RETRY",{"tool":tool_id,"reason":"safe_tool_failure","attempt":2})
            return self.execute_tool(tool_id,params,approved,True)
        return result

    def run(self,goal):
        goal=(goal or "").strip()
        run_id=str(uuid4())
        self._state("PERCEIVE",goal=goal,run_id=run_id)
        self.events.publish("COGNITIVE_RUN_STARTED",{"run_id":run_id,"goal":goal})
        self.events.publish("PERCEIVE",{"goal":goal,"run_id":run_id})

        self._state("UNDERSTAND",goal=goal,run_id=run_id)
        self.events.publish("UNDERSTAND",{"goal":goal,"summary":"تحديد المطلوب والنتيجة المتوقعة","run_id":run_id})

        self._state("MEMORY",goal=goal,run_id=run_id)
        memories=self.store.memories()[-12:]
        self.events.publish("MEMORY_RECALL",{"count":len(memories),"run_id":run_id})

        self._state("ANALYZE",goal=goal,run_id=run_id)
        options=self.decisions.generate(goal)
        self.events.publish("ANALYZE",{"options_count":len(options),"run_id":run_id})

        self._state("PLAN",goal=goal,run_id=run_id)
        self.events.publish("PLAN_CREATED",{"steps":["فهم الطلب","تقييم الخيارات","اختيار الخطوة الآمنة","التحقق"],"run_id":run_id})

        self._state("DECIDE",goal=goal,run_id=run_id)
        decision=self.decisions.choose(goal,options,self.permissions.grants)
        decision["run_id"]=run_id
        self.events.publish("DECISION_MADE",decision)

        selected=decision.get("selected",{})
        action=selected.get("id","observe") if isinstance(selected,dict) else "observe"

        self._state("EXECUTE",goal=goal,run_id=run_id)
        task_title=selected.get("action","تحليل الهدف") if isinstance(selected,dict) else "تحليل الهدف"
        task=self.tasks.create(task_title)
        self.tasks.update(task["id"],"RUNNING")
        self.events.publish("EXECUTION_STARTED",{"task_id":task["id"],"action":action,"title":task_title,"run_id":run_id})

        tool_id={"observe":"memory.read","plan":"tasks.create","inspect_code":"code.inspect","verify_code":"code.verify"}.get(action)
        tool_result=self.execute_tool(tool_id,{"title":task_title} if tool_id=="tasks.create" else {"path":"brain_v12/app.py"} if tool_id=="code.inspect" else {}) if tool_id else None
        if action in {"observe","plan"} and tool_result and tool_result.get("ok"):
            self.tasks.update(task["id"],"COMPLETED")
            execution={"status":"COMPLETED","action":action,"task_id":task["id"],"tool":tool_id,"tool_result":tool_result,"result":"تم اختيار أداة آمنة وتنفيذها ثم إكمال المهمة.","run_id":run_id}
            self.events.publish("EXECUTION_COMPLETED",execution)
        else:
            self.tasks.update(task["id"],"PENDING")
            execution={"status":"WAITING_PERMISSION","action":action,"task_id":task["id"],"result":"الخطوة تحتاج صلاحية أو أداة تنفيذ خارجية.","run_id":run_id}
            self.events.publish("EXECUTION_WAITING_PERMISSION",execution)

        self._state("VERIFY",goal=goal,run_id=run_id,task_id=task["id"])
        verified_task=next((x for x in self.tasks.snapshot()["tasks"] if x["id"]==task["id"]),None)
        verification={
            "status":"VERIFIED" if verified_task and verified_task["status"]=="COMPLETED" else "PENDING",
            "task_status":verified_task["status"] if verified_task else "UNKNOWN",
            "evidence":"تم فحص حالة المهمة بعد التنفيذ الداخلي.",
            "run_id":run_id
        }
        self.events.publish("VERIFIED",verification)

        self._state("LEARN",status="READY",goal=goal,run_id=run_id)
        lesson="تم تنفيذ خطوة داخلية آمنة والتحقق من نتيجتها." if execution.get("status")=="COMPLETED" else "تم تسجيل أن الخطوة تحتاج صلاحية قبل التنفيذ."
        self.store.save_memory("cognitive.last_verified_run",f"{run_id} | {lesson}")
        self.events.publish("LEARNING_RECORDED",{"lesson":lesson,"run_id":run_id})

        return {
            "run_id":run_id,
            "goal":goal,
            "stages":self.STAGES,
            "stage_count":len(self.STAGES),
            "memory_count":len(memories),
            "options":options,
            "decision":decision,
            "execution":execution,
            "verification":verification,
            "learning":{"status":"RECORDED","lesson":lesson},
            "tool_result":tool_result,
            "world":self.world.snapshot(),
            "tasks":self.tasks.snapshot()
        }
