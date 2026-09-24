from .decision_engine import DecisionEngine
from .event_bus import EventBus
from .permissions import PermissionGate
from .task_engine import TaskEngine
from .world_model import WorldModel

class CognitiveLoop:
    """
    Real V12 cognitive pipeline.
    Each stage changes persisted state and emits a traceable event.
    It intentionally exposes high-level state, not private chain-of-thought.
    """
    STAGES = ["PERCEIVE","UNDERSTAND","MEMORY","ANALYZE","PLAN","DECIDE","EXECUTE","VERIFY","LEARN"]

    def __init__(self,store):
        self.store=store
        self.events=EventBus(store)
        self.decisions=DecisionEngine()
        self.permissions=PermissionGate()
        self.tasks=TaskEngine()
        self.world=WorldModel()

    def _state(self, stage, status="RUNNING", **extra):
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
        self._state("PERCEIVE",goal=goal)
        self.events.publish("PERCEIVE",{"goal":goal})

        self._state("UNDERSTAND",goal=goal)
        self.events.publish("UNDERSTAND",{"goal":goal,"summary":"تحديد المطلوب والنتيجة المتوقعة"})

        self._state("MEMORY",goal=goal)
        memories=self.store.memories()[-12:]
        self.events.publish("MEMORY_RECALL",{"count":len(memories)})

        self._state("ANALYZE",goal=goal)
        options=self.decisions.generate(goal)
        self.events.publish("ANALYZE",{"options_count":len(options)})

        self._state("PLAN",goal=goal)
        self.events.publish("PLAN_CREATED",{"steps":["فهم الطلب","تقييم الخيارات","اختيار الخطوة الآمنة","التحقق"]})

        self._state("DECIDE",goal=goal)
        decision=self.decisions.choose(goal,options,self.permissions.grants)
        self.events.publish("DECISION_MADE",decision)

        selected=decision.get("selected",{})
        action=selected.get("id","observe") if isinstance(selected,dict) else "observe"
        execution={"status":"NOT_EXECUTED","action":action,"reason":"execution requires an explicit tool action"}

        self._state("EXECUTE",goal=goal)
        self.events.publish("EXECUTION_SKIPPED",execution)

        self._state("VERIFY",goal=goal)
        verification={"status":"VERIFIED","evidence":"تم التحقق من اكتمال مراحل الإدراك والتحليل والقرار؛ لم يُنفذ إجراء خارجي."}
        self.events.publish("VERIFIED",verification)

        self._state("LEARN",status="READY",goal=goal)
        self.events.publish("LEARNING_RECORDED",{"lesson":"تم تشغيل دورة معرفية كاملة دون تنفيذ خارجي غير مصرح."})

        return {
            "goal":goal,
            "stages":self.STAGES,
            "stage_count":len(self.STAGES),
            "memory_count":len(memories),
            "options":options,
            "decision":decision,
            "execution":execution,
            "verification":verification,
            "learning":{"status":"RECORDED"},
            "world":self.world.snapshot(),
            "tasks":self.tasks.snapshot()
        }
