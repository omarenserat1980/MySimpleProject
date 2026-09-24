from .decision_engine import DecisionEngine
from .event_bus import EventBus
from .permissions import PermissionGate
from .task_engine import TaskEngine
from .world_model import WorldModel
from uuid import uuid4

class CognitiveLoop:
    """Traceable V12 cognitive pipeline. Exposes high-level state, never private chain-of-thought."""
    STAGES=["PERCEIVE","UNDERSTAND","MEMORY","ANALYZE","PLAN","DECIDE","EXECUTE","VERIFY","LEARN"]

    def __init__(self,store):
        self.store=store
        self.events=EventBus(store)
        self.decisions=DecisionEngine()
        self.permissions=PermissionGate()
        self.tasks=TaskEngine()
        self.world=WorldModel()

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

        if action in {"observe","plan"}:
            self.tasks.update(task["id"],"COMPLETED")
            execution={"status":"COMPLETED","action":action,"task_id":task["id"],"result":"تم تنفيذ خطوة داخلية آمنة: إنشاء المهمة وإكمالها والتحقق من حالتها.","run_id":run_id}
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
            "world":self.world.snapshot(),
            "tasks":self.tasks.snapshot()
        }
